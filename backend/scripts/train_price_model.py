"""Clean the listing data, train and evaluate the price models, and save the selected one.

    python scripts/train_price_model.py               # full run with grid search (about a minute)
    python scripts/train_price_model.py --no-tune     # quick run with default hyperparameters

Outputs (paths relative to the repository root):
    data/processed/clean_properties_v1.csv   cleaned rows used for training
    data/training/price_training_v1.csv      model-ready features + target + group
    ml/artifacts/price_model/                price_model.joblib + metadata.json
    ml/reports/data_quality.md, model_evaluation.md, plots/*.png

The model is also recorded in the model_metadata table if the database has been migrated.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import REPO_DIR  # noqa: E402
from app.ml import reporting  # noqa: E402
from app.ml.data_prep import clean, detection_check, load_raw  # noqa: E402
from app.ml.features import build_features  # noqa: E402
from app.ml.training import METADATA_FILE, train  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=REPO_DIR / "data" / "raw" / "synthetic_properties_v1.csv")
    ap.add_argument("--out", type=Path, default=REPO_DIR / "ml" / "artifacts" / "price_model")
    ap.add_argument("--reports", type=Path, default=REPO_DIR / "ml" / "reports")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-tune", action="store_true", help="skip the grid search")
    ap.add_argument("--no-register", action="store_true", help="do not write the model_metadata row")
    args = ap.parse_args()

    try:
        source = args.data.resolve().relative_to(REPO_DIR).as_posix()
    except ValueError:
        source = args.data.name
    print(f"Cleaning {source} ...")
    c = clean(args.data)
    detection = detection_check(load_raw(args.data), c.flagged)
    reporting.write(args.reports / "data_quality.md", reporting.data_quality_md(c, detection, source))

    processed = REPO_DIR / "data" / "processed" / "clean_properties_v1.csv"
    processed.parent.mkdir(parents=True, exist_ok=True)
    c.clean.to_csv(processed, index=False)
    snapshot = build_features(c.clean.to_dict("records"))
    snapshot["asking_price_inr"] = c.clean["asking_price_inr"].to_numpy()
    snapshot["dup_group_id"] = c.clean["dup_group_id"].to_numpy()
    snapshot.insert(0, "source_record_id", c.clean["source_record_id"].to_numpy())
    training_csv = REPO_DIR / "data" / "training" / "price_training_v1.csv"
    training_csv.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(training_csv, index=False)
    print(f"  {c.raw_rows} raw rows -> {len(c.clean)} clean rows")

    print("Training (this runs a small grid search unless --no-tune) ...")
    m = train(c, args.out, seed=args.seed, tune=not args.no_tune, dataset_file=source, report_dir=args.reports)
    plots = (args.reports / "plots" / "predicted_vs_actual.png").exists()
    reporting.write(args.reports / "model_evaluation.md", reporting.evaluation_md(m, plots))

    best = m["test_metrics"][m["model_name"]]
    print(f"Selected {m['model_label']} ({m['model_version']})")
    print(f"  test MAE {reporting.inr(best['mae_inr'])}, MAPE {reporting.pct(best['mape'])}, "
          f"R2 {best['r2']:.3f}, 80% range coverage {reporting.pct(m['interval']['measured_test_coverage'])}")
    print(f"  saved to {args.out}")

    if not args.no_register:
        try:
            from app.db.session import SessionLocal
            from app.ml.registry import register_model
            with SessionLocal() as db:
                register_model(db, m, (args.out / METADATA_FILE).resolve().relative_to(REPO_DIR).as_posix()
                               if args.out.resolve().is_relative_to(REPO_DIR) else str(args.out))
            print("  recorded in model_metadata")
        except Exception as e:  # database not migrated yet: the artifact still works
            print(f"  not recorded in the database ({type(e).__name__}); run alembic upgrade head first")


if __name__ == "__main__":
    main()
