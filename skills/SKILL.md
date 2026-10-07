---
name: ff3-replication
description: Regenerate the main tables and figures of the Fama-French (1993) three-factor replication and momentum extension from the raw data.
---

# Fama–French (1993) three-factor replication — generate outputs

Use this skill to regenerate the project's main tables and figures from raw
data with no manual editing.

## Prerequisites

- Python 3 with `pandas`, `numpy`, `matplotlib`, `scipy`, `statsmodels`,
  `pyarrow` installed (`pip install pandas numpy matplotlib scipy statsmodels pyarrow`).
- The four raw CSVs placed in `data/raw/` (see `data/raw/README.md`).

## Steps

1. From the project root, run the whole pipeline:

   ```bash
   python code/run_all.py
   ```

   This executes, in order: `01_data_prep.py` → `02_variable_construction.py`
   → `03_portfolio_sorting.py` → `04_factor_construction.py` →
   `05_validation.py` → `06_extension.py`. Each script reads the previous
   step's output from `data/processed/` and writes to `outputs/`.

2. Confirm the main outputs exist:

   - `outputs/FF3_constructed.csv` — the reconstructed monthly MKT-RF / SMB / HML.
   - `outputs/tables/descriptive_stats.csv`, `correlation.csv`,
     `tracking_regression.csv`, `ff4_model_comparison.csv`.
   - `outputs/figures/cumulative_{MKT_RF,SMB,HML}.png`, `extension_alpha_bar.png`.

## What the main tables/figures are

| Output | What it shows |
| --- | --- |
| `outputs/tables/descriptive_stats.csv` | mean / std / t / Sharpe for the constructed vs official factors |
| `outputs/tables/correlation.csv` | monthly correlation of each constructed factor with the benchmark |
| `outputs/tables/tracking_regression.csv` | regression of constructed on benchmark (alpha / beta / R²) |
| `outputs/tables/ff4_model_comparison.csv` | GRS test, mean \|alpha\|, R² for the 3- vs 4-factor model |
| `outputs/figures/cumulative_*.png` | cumulative-return curves, constructed vs benchmark |
| `outputs/figures/extension_alpha_bar.png` | per-portfolio pricing error, FF3 vs FF4 |

## Verification

The reconstructed factors should correlate with the Ken French benchmark at
≈ 0.997 (MKT-RF), ≈ 0.96 (SMB) and ≈ 0.95 (HML). If a value is far below this,
check `data/raw/` for the correct files and re-run `run_all.py`.
