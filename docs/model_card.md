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

Measured on the real files (the bundle of 30 October 2026) with `make data`; the Data and
methods screen shows the same figures. 416 sectors in 30 districts. Five features were
available: women's education is not published by sector, so it is left out.

| Model | MAE (points) | Weighted MAE | R² |
| --- | --- | --- | --- |
| Province mean | 13.05 | 12.09 | -0.133 |
| **District mean (kept)** | **9.21** | **8.61** | **0.401** |
| Weighted linear regression | 12.79 | 11.97 | -0.036 |
| LightGBM | 11.57 | 11.16 | 0.066 |

- Neither model beats the district mean in leave-one-district-out validation, so the district
  mean is kept and the fallback below applies. The features explain little of the differences
  between sectors once the district is known.
- 80% interval half-width: ±14.9 points. Empirical coverage: 80.3% overall, 81.2% rural and
  75.0% urban. Urban intervals are slightly too narrow.
- MAE by area: rural 9.27, urban 8.85 points. By province: Kigali 8.46, East 8.23, North 8.72,
  South 10.83, West 9.20.
- Moran's I of residuals: 0.142 (p = 0.001). Errors cluster in space: neighbouring sectors share
  something the features miss.

## Fallback

If a baseline is kept, each sector is compared with the average of the other sectors in its
district: that average is its expected value, and the peer gap in the priority index measures
the distance to it. This is the case on the real data. The Data and methods screen says so.

## Ethical considerations

- Inputs are published aggregates only; no child-level data.
- Features describe places, not people. A low expectation is not a judgement on a community.
- Outputs carry their status (model estimate, or simulated where an input is a stand-in), are
  shown with intervals, and never trigger an action without a person's decision, recorded in the audit log.
