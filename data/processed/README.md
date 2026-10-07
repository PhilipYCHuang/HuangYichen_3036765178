# data/processed/

Intermediate files produced by the pipeline are written here by `code/01..04`
(e.g. `monthly_stock_clean.parquet`, `bm_me_panel.parquet`,
`portfolio_assignment.parquet`, `portfolio_returns.parquet`).

These files are derivatives of restricted raw data, so they are regenerated
locally and are **not** committed to GitHub. Running `python code/run_all.py`
recreates them automatically.
