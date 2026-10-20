"""Train, evaluate and save the price model (BLUEPRINT Part E, steps 6–10).

Everything reported comes from the run itself; nothing is typed in by hand.
The saved artifact is exactly the model that was evaluated on the test set
(fitted on the training split only), so the published metrics describe the
deployed model.
"""
from __future__ import annotations

import json
import math
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.baselines import LocalityTypeMedianPPSF
from app.ml.data_prep import CleaningResult
from app.ml.features import BINARY, CATEGORICAL, FEATURE_DESCRIPTIONS, FEATURES, NUMERIC, build_features

MODEL_FILE = "price_model.joblib"
METADATA_FILE = "metadata.json"
INTERVAL_LOW_Q, INTERVAL_HIGH_Q = 0.10, 0.90

MODEL_LABELS = {
    "baseline_median": "Baseline: overall median price",
    "baseline_locality_type_ppsf": "Baseline: locality + type median ₹/sq ft × area",
    "linear_regression": "Linear Regression",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}

GRIDS = {
    "random_forest": {"regressor__model__max_depth": [None, 12],
                      "regressor__model__min_samples_leaf": [1, 3],
                      "regressor__model__max_features": [1.0, 0.5]},
    "gradient_boosting": {"regressor__model__n_estimators": [200, 400],
                          "regressor__model__learning_rate": [0.05, 0.1],
                          "regressor__model__max_depth": [2, 3]},
}


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=5, sparse_output=False),
         CATEGORICAL),
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC),
        ("bin", "passthrough", BINARY),
    ])


def log_target(model) -> TransformedTargetRegressor:
    """Fit on log(price), predict in rupees."""
    return TransformedTargetRegressor(regressor=model, func=np.log, inverse_func=np.exp, check_inverse=False)


def candidate_models(seed: int) -> dict[str, Any]:
    pipe = lambda est: log_target(Pipeline([("prep", preprocessor()), ("model", est)]))  # noqa: E731
    return {
        "baseline_median": log_target(DummyRegressor(strategy="median")),
        "baseline_locality_type_ppsf": LocalityTypeMedianPPSF(),
        "linear_regression": pipe(LinearRegression()),
        "random_forest": pipe(RandomForestRegressor(n_estimators=300, random_state=seed, n_jobs=1)),
        "gradient_boosting": pipe(GradientBoostingRegressor(subsample=0.8, random_state=seed)),
    }


def metrics(y_true, y_pred) -> dict[str, float]:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    ape = np.abs(y_pred - y_true) / y_true
    return {
        "n": int(len(y_true)),
        "mae_inr": float(mean_absolute_error(y_true, y_pred)),
        "rmse_inr": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
        "mape": float(ape.mean()),
        "median_ape": float(np.median(ape)),
    }


@dataclass
class Split:
    train: np.ndarray
    val: np.ndarray
    test: np.ndarray


def group_split(groups: pd.Series, seed: int, val: float = 0.15, test: float = 0.15) -> Split:
    """70/15/15 split in which all near-duplicates of one property land in the same part."""
    idx = np.arange(len(groups))
    outer = GroupShuffleSplit(n_splits=1, test_size=test, random_state=seed)
    rest, te = next(outer.split(idx, groups=groups))
    inner = GroupShuffleSplit(n_splits=1, test_size=val / (1 - test), random_state=seed)
    tr, va = next(inner.split(rest, groups=groups.iloc[rest]))
    return Split(train=rest[tr], val=rest[va], test=te)


def _group_breakdown(df: pd.DataFrame, y, pred, by: str) -> list[dict]:
    out = []
    for key, g in df.assign(_y=np.asarray(y), _p=np.asarray(pred)).groupby(by):
        m = metrics(g["_y"], g["_p"])
        out.append({by: key, "n": m["n"], "mae_inr": m["mae_inr"], "mape": m["mape"],
                    "median_ape": m["median_ape"]})
    return sorted(out, key=lambda r: -r["n"])


def _caveat(n_synthetic: int, n_real: int) -> str:
    if n_synthetic and n_real:
        return (f"Trained on {n_synthetic} synthetic rows (a documented formula) plus {n_real} real asking prices "
                "copied from public listings. The synthetic rows dominate, so good metrics mostly show that the "
                "pipeline recovers the generator's pricing rules, not that it knows the real Hubballi–Dharwad "
                "market. Asking prices are not sale prices. Not a valuation.")
    if n_synthetic:
        return ("Trained on synthetic data generated by a documented formula. Good metrics show that "
                "the pipeline recovers the generator's pricing rules, not that it knows the real "
                "Hubballi–Dharwad market. Not a valuation.")
    return "Indicative estimate from listing asking prices. Not a valuation."


def train(cleaning: CleaningResult, out_dir: Path, *, seed: int = 42, tune: bool = True,
          dataset_file: str = "", report_dir: Path | None = None) -> dict:
    """Run the whole training procedure and write the artifact + metadata. Returns the metadata."""
    df = cleaning.clean.reset_index(drop=True)
    X = build_features(df.to_dict("records"))
    y = df["asking_price_inr"].to_numpy(float)
    groups = df["dup_group_id"]
    sp = group_split(groups, seed)
    Xtr, Xva, Xte = X.iloc[sp.train], X.iloc[sp.val], X.iloc[sp.test]
    ytr, yva, yte = y[sp.train], y[sp.val], y[sp.test]

    fitted, val_metrics, tuning = {}, {}, {}
    cv = GroupKFold(n_splits=5, shuffle=True, random_state=seed)
    for name, model in candidate_models(seed).items():
        if tune and name in GRIDS:
            gs = GridSearchCV(model, GRIDS[name], scoring="neg_mean_absolute_error", cv=cv, n_jobs=-1)
            gs.fit(Xtr, ytr, groups=groups.iloc[sp.train])
            model = gs.best_estimator_
            tuning[name] = {"best_params": {k.split("__")[-1]: v for k, v in gs.best_params_.items()},
                            "cv_mae_inr": float(-gs.best_score_), "grid_size": len(gs.cv_results_["params"])}
        else:
            model.fit(Xtr, ytr)
        fitted[name] = model
        val_metrics[name] = metrics(yva, model.predict(Xva))

    trained = [n for n in fitted if not n.startswith("baseline")]
    best = min(trained, key=lambda n: val_metrics[n]["mae_inr"])
    model = fitted[best]

    # Interval from validation log-residuals, then coverage measured once on test.
    val_resid = np.log(yva) - np.log(model.predict(Xva))
    q_lo, q_hi = (float(np.quantile(val_resid, q)) for q in (INTERVAL_LOW_Q, INTERVAL_HIGH_Q))
    pred_te = model.predict(Xte)
    lo, hi = pred_te * math.exp(q_lo), pred_te * math.exp(q_hi)
    coverage = float(np.mean((yte >= lo) & (yte <= hi)))

    test_metrics = {name: metrics(yte, fitted[name].predict(Xte))
                    for name in ("baseline_median", "baseline_locality_type_ppsf", best)}

    perm = permutation_importance(model, Xte, yte, scoring="neg_mean_absolute_error", n_repeats=20,
                                  random_state=seed)
    importance = sorted(({"feature": f, "mae_increase_inr": float(m), "std_inr": float(s)}
                         for f, m, s in zip(FEATURES, perm.importances_mean, perm.importances_std)),
                        key=lambda r: -r["mae_increase_inr"])

    # Generalisation to localities the model has never seen.
    holdout = locality_holdout(X, y, df["locality"], {"baseline_locality_type_ppsf": LocalityTypeMedianPPSF(),
                                                      best: clone(model)}, seed)

    test_df = df.iloc[sp.test]
    by_type = _group_breakdown(test_df, yte, pred_te, "property_type")
    by_locality = _group_breakdown(test_df, yte, pred_te, "locality")

    area_ranges = {t: {"min_sqft": float(g["normalized_area_sqft"].min()),
                       "max_sqft": float(g["normalized_area_sqft"].max()), "n": int(len(g))}
                   for t, g in df.iloc[sp.train].groupby("property_type")}
    synthetic_mask = df["is_synthetic"].astype(str).str.lower().eq("true") if "is_synthetic" in df \
        else pd.Series(False, index=df.index)
    n_synthetic, n_real = int(synthetic_mask.sum()), int((~synthetic_mask).sum())
    # True whenever any training row is synthetic: the model's behaviour then still reflects the generator.
    trained_on_synthetic = n_synthetic > 0
    now = datetime.now(timezone.utc)
    version = f"{now:%Y%m%d}-{cleaning.dataset_sha256[:8]}-{best}"

    metadata = {
        "model_name": best,
        "model_label": MODEL_LABELS[best],
        "model_version": version,
        "trained_at": now.isoformat(timespec="seconds"),
        "target": "asking_price_inr (observed asking price, modelled as log; not a transaction price)",
        "trained_on_synthetic": trained_on_synthetic,
        "data_mix": {"synthetic_rows": n_synthetic, "real_rows": n_real,
                     "real_sources": sorted(df.loc[~synthetic_mask, "data_source"].unique().tolist())
                     if "data_source" in df and n_real else []},
        "seed": seed,
        "tuned": tune,
        "dataset": {"file": dataset_file, "sha256": cleaning.dataset_sha256, "raw_rows": cleaning.raw_rows,
                    "clean_rows": int(len(df)), "excluded_rows": int(cleaning.raw_rows - len(df))},
        "split": {"method": "GroupShuffleSplit on near-duplicate group, 70/15/15",
                  "train": int(len(sp.train)), "validation": int(len(sp.val)), "test": int(len(sp.test))},
        "selection": "lowest validation MAE (INR) among trained models; test set used once, after selection",
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "tuning": tuning,
        "interval": {"method": "empirical 10th–90th percentile of validation log-residuals",
                     "nominal": 0.80, "log_residual_low": q_lo, "log_residual_high": q_hi,
                     "measured_test_coverage": coverage, "test_n": int(len(sp.test))},
        "error_by_property_type": by_type,
        "error_by_locality": by_locality,
        "locality_holdout": holdout,
        "permutation_importance": importance,
        "feature_schema": {
            "features": FEATURES, "categorical": CATEGORICAL, "numeric": NUMERIC, "binary": BINARY,
            "descriptions": FEATURE_DESCRIPTIONS,
            "training_localities": sorted(df.iloc[sp.train]["locality"].unique().tolist()),
            "training_property_types": area_ranges,
        },
        "library_versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                             "numpy": np.__version__, "pandas": pd.__version__},
        "caveat": _caveat(n_synthetic, n_real),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / MODEL_FILE, compress=3)
    (out_dir / METADATA_FILE).write_text(json.dumps(metadata, indent=2, default=_json_default), encoding="utf-8")
    if report_dir is not None:
        _plots(report_dir / "plots", yte, pred_te, importance)
    return metadata


def locality_holdout(X: pd.DataFrame, y: np.ndarray, localities: pd.Series, models: dict, seed: int) -> dict:
    """GroupKFold by locality: every fold's test localities are absent from its training data."""
    cv = GroupKFold(n_splits=5, shuffle=True, random_state=seed)
    preds = {name: np.zeros(len(y)) for name in models}
    for tr, te in cv.split(X, y, groups=localities):
        for name, m in models.items():
            preds[name][te] = clone(m).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
    return {"method": "GroupKFold (5 folds) by locality over all clean rows",
            "results": {name: metrics(y, p) for name, p in preds.items()}}


def _plots(plot_dir: Path, y, pred, importance) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # plots are optional; the report says so
        return
    plot_dir.mkdir(parents=True, exist_ok=True)
    lakh = 1e5
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.scatter(y / lakh, pred / lakh, s=18, alpha=0.7)
    lim = [min(y.min(), pred.min()) / lakh * 0.8, max(y.max(), pred.max()) / lakh * 1.2]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set(xscale="log", yscale="log", xlim=lim, ylim=lim, xlabel="Actual asking price (₹ lakh)",
           ylabel="Predicted (₹ lakh)", title="Test set: predicted vs actual (synthetic data)")
    fig.tight_layout()
    fig.savefig(plot_dir / "predicted_vs_actual.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(pred / lakh, np.log(y) - np.log(pred), s=18, alpha=0.7)
    ax.axhline(0, color="k", lw=1)
    ax.set(xscale="log", xlabel="Predicted (₹ lakh)", ylabel="log(actual) − log(predicted)",
           title="Test set residuals")
    fig.tight_layout()
    fig.savefig(plot_dir / "residuals.png", dpi=120)
    plt.close(fig)

    top = importance[:10][::-1]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh([r["feature"] for r in top], [r["mae_increase_inr"] / lakh for r in top],
            xerr=[r["std_inr"] / lakh for r in top])
    ax.set(xlabel="Increase in test MAE when shuffled (₹ lakh)", title="Permutation importance")
    fig.tight_layout()
    fig.savefig(plot_dir / "permutation_importance.png", dpi=120)
    plt.close(fig)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, float) and math.isnan(o):
        return None
    raise TypeError(type(o))
