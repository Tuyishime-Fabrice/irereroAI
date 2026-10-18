# Model card: peer benchmark model

## Overview

| | |
| --- | --- |
| **Task** | Regression: expected attendance rate of children aged 3 to 5 in a sector |
| **Target** | Census 2022 attendance rate (Table 2.5), observed, one row per sector |
| **Unit** | Sector (416), grouped in 30 districts and 5 provinces |
| **Features (up to 6)** | Urban share; women aged 15+ with secondary education; households with improved water; households with electricity; poverty rate (EICV7); log children aged 3 to 5 per km² |
| **Candidates** | Province-mean baseline, district-mean baseline (leave one sector out), weighted linear regression, LightGBM |
| **Selection** | Leave-one-district-out cross-validation; the simplest candidate within 1 point of the best MAE |
| **Uncertainty** | 80% split-conformal interval from out-of-fold residuals |
| **Explanations** | Top 3 drivers per sector: linear contributions or SHAP values. These are associations, not causes. |
| **Code** | `irerero/diagnose/peer.py`, `irerero/diagnose/moran.py` |

## Intended use

- Screening aid for district planners and national analysts. It shows where attendance is
  lower than in sectors like it (DEMAND bottleneck), and feeds the *peer gap* component of the
  priority index.
- Every output is a model estimate with an interval. People decide what goes into a plan.

## Not for

- Causal claims ("raising electricity will raise attendance").
- Decisions about individual children, centres or staff.
- Ranking caregivers or teachers.
- Years or places far from the training data.

## Evaluation as measured

The numbers below come from the **demo build, where every input is simulated**. They show the
method works end to end, not real-world accuracy. Re-run `make data` with the real files; the
Data and methods screen then shows the real figures.

| Model | MAE (points) | Weighted MAE | R² |
| --- | --- | --- | --- |
| Province mean | 8.41 | 8.53 | 0.396 |
| District mean | 8.52 | 8.93 | 0.349 |
| **Weighted linear regression (chosen)** | **3.85** | **3.84** | **0.884** |
| LightGBM | 4.11 | 4.26 | 0.869 |

- 80% interval half-width: ±5.9 points. Empirical coverage: 80.3% overall, 85% rural and 61%
  urban. Urban sectors are under-covered, so their intervals should be read as too narrow.
- MAE by area: rural 3.4, urban 6.1 points. By province: Kigali 5.3, East 3.1, North 4.2,
  South 3.2, West 4.4.
- Moran's I of residuals: 0.30 (p = 0.001). Errors cluster in space: neighbouring sectors share
  something the features miss. In the simulated data this is the district effect built into
  the generator.
- The simulated attendance was generated from a logistic model of these same features. A
  linear model fitting it well is expected, and says nothing about real data.

## Fallback

If a baseline is kept, the peer gap drops out of the priority index and each sector is
compared with the average of the other sectors in its district. The README and the Data and
methods screen say so.

## Ethical considerations

- Inputs are published aggregates only; no child-level data.
- Features describe places, not people. A low expectation is not a judgement on a community.
- Outputs carry their status (model estimate, or simulated), are shown with intervals, and never
  trigger an action without a person's decision, recorded in the audit log.
