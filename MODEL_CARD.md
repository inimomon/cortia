# Cortia Model Card

## Scope
Cortia is currently positioned as an offline post-award anomaly detection system for procurement records. The active modeling target is not confirmed fraud; it is unusual post-award behavior that deserves review.

## Data
- Source: OCDS procurement export processed into [JakartaOCDSFinalData.csv](C:\Users\VICTUS\coding\collab\1\cortia\JakartaOCDSFinalData.csv)
- Coverage: 2014-12-24 to 2023-10-18
- Unit of analysis: award-level procurement record
- Main numeric signals: tender value, award value, days to award, budget utilization, value gap, timing-derived features
- Main categorical signal: `mainprocurementcategory`

## Excluded Fields
- `buyer_name`: excluded from the model because buyer identity is heavily imbalanced and would add weak signal
- `tender_status`: excluded from the model because it is effectively constant in the cleaned dataset

## Leakage Control
- Split strategy: time-based 85/15 split on `award_date`
- Rule: train period must end on or before test period starts
- Preprocessing is fit on training data before being applied to the test set

## Model
- Core detector: `IsolationForest`
- Output:
  - `anomaly_score`
  - `prediction_label` (`normal` or `anomaly`)
  - `severity_band` (`low`, `medium`, `high`)

## Explainability
- Global explanation: permutation importance on a surrogate regressor trained to approximate anomaly scores
- Local explanation: top-3 drivers derived from deviation against the normal training baseline for numeric features and rarity against the normal training baseline for categorical features
- Human-readable output: every prediction includes top-3 drivers and a natural-language explanation paragraph

## Evaluation
- No confirmed fraud labels are currently available
- Retrospective evaluation uses transparent proxy rules:
  - over-budget award
  - same-day award
  - extreme award value for category
  - unusually long award duration for category
  - extreme budget utilization ratio for category
- Reported metrics include proxy precision, recall, F1, top-N precision, and proxy capture

## Persisted Artifacts
Training exports reusable artifacts into `artifacts/post_award_anomaly/`:
- `isolation_forest.joblib`
- `preprocessor.joblib`
- `model_config.json`
- `explanation_baselines.json`
- `reference_thresholds.json`
- prediction and evaluation CSV outputs
- demo input and expected-output files

## Limitations
- Proxy labels are not the same as confirmed corruption or fraud labels
- The dataset is highly concentrated in one buyer environment
- This version is post-award only; it should not be presented as a pre-award early-warning model
