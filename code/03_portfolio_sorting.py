"""03_portfolio_sorting.py — June 2x3 size x book-to-market sorts.

Each June t, sort stocks into 2 size groups (Small/Big) and 3 book-to-market
groups (Low/Medium/High) using NYSE breakpoints, producing 6 portfolios
(S/L, S/M, S/H, B/L, B/M, B/H).

Breakpoints (Fama-French convention):
    size  : NYSE median of June-t market equity
    BM    : NYSE 30th and 70th percentiles of BM (= BE(t-1) / ME_Dec(t-1))

Outputs:
    data/processed/portfolio_assignment.parquet   PERMNO x sort_year -> portfolio
    outputs/tables/breakpoints.csv                  NYSE breakpoints by sort year

Run:  python code/03_portfolio_sorting.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg


def assign_portfolios(panel: pd.DataFrame) -> pd.DataFrame:
    """Add size/BM buckets to the sorting panel using NYSE breakpoints."""
    nyse = panel[panel["is_nyse"]]

    bps = (
        nyse.groupby("sort_year")
        .agg(
            size_median=("ME_June", "median"),
            bm_p30=("BM", lambda s: s.quantile(0.30)),
            bm_p70=("BM", lambda s: s.quantile(0.70)),
        )
        .reset_index()
    )

    panel = panel.merge(bps, on="sort_year", how="left")

    panel["size_bucket"] = np.where(panel["ME_June"] < panel["size_median"], "S", "B")
    panel["bm_bucket"] = np.select(
        [panel["BM"] < panel["bm_p30"], panel["BM"] <= panel["bm_p70"]],
        ["L", "M"],
        default="H",
    )
    panel["portfolio"] = panel["size_bucket"] + "/" + panel["bm_bucket"]

    return panel, bps


def main() -> None:
    cfg.ensure_dirs()
    print("[1/2] loading BM/ME panel ...")
    panel = pd.read_parquet(cfg.PROCESSED / "bm_me_panel.parquet")
    print(f"    panel rows: {len(panel):,}")

    print("[2/2] assigning 2x3 portfolios ...")
    panel, bps = assign_portfolios(panel)

    assignment = panel[
        ["PERMNO", "sort_year", "size_bucket", "bm_bucket", "portfolio"]
    ]
    counts = assignment.groupby(["sort_year", "portfolio"]).size().unstack()
    print("    mean stocks per portfolio:")
    print((counts.mean().round(0)).to_string())

    assignment.to_parquet(cfg.PROCESSED / "portfolio_assignment.parquet", index=False)
    bps.round(4).to_csv(cfg.TABLES / "breakpoints.csv", index=False)
    print("    wrote portfolio_assignment.parquet and outputs/tables/breakpoints.csv")


if __name__ == "__main__":
    main()
