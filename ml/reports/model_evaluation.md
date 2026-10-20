# Price model evaluation

Model version `20261020-58e40f68-linear_regression`, trained 2026-10-20T13:52:52+00:00, seed 42.

> Trained on 288 synthetic rows (a documented formula) plus 15 real asking prices copied from public listings. The synthetic rows dominate, so good metrics mostly show that the pipeline recovers the generator's pricing rules, not that it knows the real Hubballi–Dharwad market. Asking prices are not sale prices. Not a valuation.

**Target:** asking_price_inr (observed asking price, modelled as log; not a transaction price).  
**Data:** 303 clean rows from 328 raw (`data/raw/synthetic_properties_v1.csv + data/raw/real_listings_1acre_v1.csv`).  
**Split:** GroupShuffleSplit on near-duplicate group, 70/15/15: train 211, validation 46, test 46. Most rows are synthetic and have no real time axis, so there is no time-based split.  
**Data mix:** 288 synthetic + 15 real rows (1acre_public_listing).  
**Selection:** lowest validation MAE (INR) among trained models; test set used once, after selection.

## Validation set (used to choose the model)
| Model | MAE | RMSE | R² | MAPE | Median APE |
|---|---|---|---|---|---|
| Baseline: overall median price | ₹37.27 lakh | ₹66.82 lakh | -0.079 | 81.7% | 46.4% |
| Baseline: locality + type median ₹/sq ft × area | ₹18.09 lakh | ₹40.30 lakh | 0.608 | 23.0% | 16.2% |
| Linear Regression | ₹13.21 lakh | ₹30.26 lakh | 0.779 | 16.6% | 13.4% |
| Random Forest | ₹19.67 lakh | ₹47.49 lakh | 0.455 | 29.4% | 21.5% |
| Gradient Boosting | ₹16.58 lakh | ₹40.64 lakh | 0.601 | 23.5% | 16.6% |

Selected: **Linear Regression**.

Grid search (5-fold group CV on the training split, scored by MAE):

- Random Forest: 8 combinations, best max_depth=None, max_features=1.0, min_samples_leaf=1 (CV MAE ₹23.75 lakh)
- Gradient Boosting: 8 combinations, best learning_rate=0.05, max_depth=2, n_estimators=400 (CV MAE ₹17.36 lakh)

Why a linear model can win here: the synthetic generator builds prices by *multiplying* a locality rate by type, conversion, layout and road factors and a power of area. Taking logs turns that into a sum, which is exactly what Linear Regression on log(price) fits. Tree models have to approximate the same structure in steps from only 211 training rows. Real prices need not follow this shape, so the ranking of models could change on genuine data.

## Test set (evaluated once, after selection)
| Model | n | MAE | RMSE | R² | MAPE | Median APE |
|---|---|---|---|---|---|---|
| Baseline: overall median price | 46 | ₹34.77 lakh | ₹47.76 lakh | -0.114 | 80.7% | 48.9% |
| Baseline: locality + type median ₹/sq ft × area | 46 | ₹20.03 lakh | ₹30.06 lakh | 0.559 | 31.6% | 24.5% |
| Linear Regression | 46 | ₹10.81 lakh | ₹15.99 lakh | 0.875 | 19.4% | 13.2% |

R² is computed on rupee values, so a few large farmland prices dominate it; MAPE and median APE are easier to read across ₹5 lakh plots and ₹1 crore farms.

## Indicative range
empirical 10th–90th percentile of validation log-residuals gives a nominal 80.0% range of ×0.79 to ×1.37 around the estimate. Measured coverage on the 46 test rows: **76.1%**. With so few rows this coverage figure is itself uncertain.

## Error by property type (test set)
| Type | n | MAE | MAPE | Median APE |
|---|---|---|---|---|
| residential_plot | 21 | ₹9.10 lakh | 21.5% | 13.5% |
| agricultural_land | 12 | ₹10.26 lakh | 20.7% | 18.3% |
| independent_house | 5 | ₹8.43 lakh | 13.6% | 5.7% |
| commercial_building | 4 | ₹21.53 lakh | 18.6% | 18.7% |
| commercial_plot | 4 | ₹13.72 lakh | 12.2% | 10.8% |

## Error by locality (test set)
Most localities have only a handful of test rows, so these numbers are noisy.

| Locality | n | MAE | MAPE |
|---|---|---|---|
| Gokul Road | 7 | ₹14.85 lakh | 16.1% |
| Byahatti | 4 | ₹4.79 lakh | 11.8% |
| Old Hubballi | 4 | ₹11.01 lakh | 18.9% |
| Bhairidevarkoppa | 3 | ₹4.58 lakh | 19.1% |
| Garag | 3 | ₹3.27 lakh | 16.0% |
| Hubballi (village not named) | 3 | ₹28.28 lakh | 52.9% |
| Malmaddi | 3 | ₹12.98 lakh | 13.9% |
| Rayapur | 3 | ₹16.59 lakh | 29.3% |
| Unkal | 3 | ₹10.12 lakh | 28.6% |
| Amminabhavi | 2 | ₹7.49 lakh | 20.1% |
| Lakamanahalli | 2 | ₹3.79 lakh | 5.8% |
| Navanagar | 2 | ₹8.01 lakh | 9.9% |
| Saptapur | 2 | ₹10.57 lakh | 8.1% |
| Sattur | 2 | ₹5.23 lakh | 14.8% |
| Kelgeri | 1 | ₹8.58 lakh | 13.3% |
| Mugad | 1 | ₹17.38 lakh | 40.1% |
| Vidyanagar | 1 | ₹6.52 lakh | 4.7% |

## Unseen localities
GroupKFold (5 folds) by locality over all clean rows. The model never sees the test localities during training.

| Model | MAE | MAPE | Median APE |
|---|---|---|---|
| Baseline: locality + type median ₹/sq ft × area | ₹27.60 lakh | 48.2% | 28.3% |
| Linear Regression | ₹46.02 lakh | 105.3% | 53.4% |

Errors are much larger for localities absent from training. The model has no information about an unseen locality beyond its city and distance to the centre, so the API adds a warning when a locality was not in the training data. In this run the simple baseline, which falls back to the median ₹/sq ft of the property type, was more accurate than the trained model on unseen localities.

## Permutation importance (test set)
How much the test MAE rises when one feature's values are shuffled. Global, not per property.

| Feature | MAE increase | Std |
|---|---|---|
| log_area_sqft | ₹5.14 crore | ₹89.48 lakh |
| conversion_status | ₹50.03 lakh | ₹8.90 lakh |
| property_type | ₹40.14 lakh | ₹7.58 lakh |
| locality | ₹20.39 lakh | ₹2.26 lakh |
| road_access_ord | ₹5.13 lakh | ₹1.20 lakh |
| city | ₹2.96 lakh | ₹1.01 lakh |
| land_classification | ₹2.44 lakh | ₹0.73 lakh |
| layout_approval_status | ₹1.77 lakh | ₹0.72 lakh |
| distance_to_centre_km | ₹0.09 lakh | ₹0.51 lakh |
| road_access_unknown | ₹0.04 lakh | ₹0.16 lakh |
| road_frontage_missing | ₹0.03 lakh | ₹0.02 lakh |
| is_corner_plot | ₹-0.00 lakh | ₹0.01 lakh |
| amenity_count | ₹-0.12 lakh | ₹0.16 lakh |
| road_frontage_ft | ₹-0.45 lakh | ₹0.52 lakh |

## Plots

![Predicted vs actual](plots/predicted_vs_actual.png)

![Residuals](plots/residuals.png)

![Permutation importance](plots/permutation_importance.png)

## Library versions
python 3.13.16, scikit-learn 1.7.2, numpy 2.3.5, pandas 2.3.3
