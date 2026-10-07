"""04_factor_construction.py — build MKT-RF, SMB, HML.

For each month, compute value-weighted returns of the six size x BM portfolios
(weights = market equity at the START of the month, i.e. lagged ME), then:

    MKT-RF = vwretd - RF            (CRSP value-weighted market minus risk-free)
    SMB    = mean(S/L,S/M,S/H) - mean(B/L,B/M,B/H)
    HML    = mean(S/H,B/H) - mean(S/L,B/L)

Outputs:
    data/processed/portfolio_returns.parquet  6 value-weighted portfolio series
    outputs/FF3_constructed.csv               date, MKT_RF, SMB, HML (decimals)

Run:  python code/04_factor_construction.py
"""
from __future__ import annotations

import pandas as pd

import config as cfg

PORTFOLIOS = ["S/L", "S/M", "S/H", "B/L", "B/M", "B/H"]


def value_weighted_portfolio_returns(
    monthly: pd.DataFrame, assignment: pd.DataFrame
) -> pd.DataFrame:
    """Return a YYYYMM x portfolio matrix of value-weighted monthly returns."""
    m = monthly[["PERMNO", "YYYYMM", "ME_mm", "MthRet"]].copy()

    # Value weight = market equity at the START of the month (lagged ME).
    # Compute the lag on the full monthly history BEFORE merging with the
    # assignment, so the first month of each holding period (July) correctly
    # picks up the June ME rather than a missing value.
    m = m.sort_values(["PERMNO", "YYYYMM"])
    m["w"] = m.groupby("PERMNO")["ME_mm"].shift(1)

    # Which June sort does each month belong to?  A June-t sort is held from
    # July of t through June of t+1, so months Jan-Jun use the previous sort.
    m["year"] = m["YYYYMM"] // 100
    m["month"] = m["YYYYMM"] % 100
    m["sort_year"] = m["year"] - (m["month"] < 7).astype(int)

    merged = m.merge(assignment, on=["PERMNO", "sort_year"], how="inner")
    merged = merged[merged["MthRet"].notna() & (merged["w"] > 0)]
    merged["w_r"] = merged["MthRet"] * merged["w"]

    g = merged.groupby(["YYYYMM", "portfolio"]).agg(
        w_r=("w_r", "sum"), w=("w", "sum")
    )
    ret = (g["w_r"] / g["w"]).unstack("portfolio")
    ret = ret.reindex(columns=PORTFOLIOS)

    return ret


def market_and_rf(monthly: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    """Monthly CRSP value-weighted market return and the risk-free rate."""
    vw = monthly[["YYYYMM", "vwretd"]].drop_duplicates().sort_values("YYYYMM")
    rf = benchmark[["YYYYMM", "RF"]].sort_values("YYYYMM")
    out = vw.merge(rf, on="YYYYMM", how="inner")
    return out


def build_factors(
    port_ret: pd.DataFrame, mkt_rf_df: pd.DataFrame
) -> pd.DataFrame:
    """Combine portfolio returns into the three factors."""
    f = pd.DataFrame(index=port_ret.index)
    f["SMB"] = (
        port_ret[["S/L", "S/M", "S/H"]].mean(axis=1)
        - port_ret[["B/L", "B/M", "B/H"]].mean(axis=1)
    )
    f["HML"] = (
        port_ret[["S/H", "B/H"]].mean(axis=1)
        - port_ret[["S/L", "B/L"]].mean(axis=1)
    )

    f = f.reset_index().rename(columns={"YYYYMM": "date"})
    f = f.merge(mkt_rf_df, left_on="date", right_on="YYYYMM", how="inner")
    f["MKT_RF"] = f["vwretd"] - f["RF"]

    f = f[["date", "MKT_RF", "SMB", "HML"]].sort_values("date")
    return f


def main() -> None:
    cfg.ensure_dirs()
    print("[1/4] loading monthly returns and portfolio assignment ...")
    monthly = pd.read_parquet(cfg.MONTHLY_CLEAN)
    assignment = pd.read_parquet(cfg.PROCESSED / "portfolio_assignment.parquet")

    print("[2/4] computing value-weighted portfolio returns ...")
    port_ret = value_weighted_portfolio_returns(monthly, assignment)
    print(f"    portfolio return series: {port_ret.index.min()} -> {port_ret.index.max()}")
    print(f"    months with all 6 portfolios: {port_ret.dropna(how='any').shape[0]}")

    print("[3/4] loading benchmark RF / market return ...")
    benchmark = pd.read_parquet(cfg.FF3_BENCHMARK)
    mkt_rf_df = market_and_rf(monthly, benchmark)

    print("[4/4] building factors ...")
    factors = build_factors(port_ret, mkt_rf_df)
    print(f"    factor series: {factors['date'].min()} -> {factors['date'].max()} ({len(factors)} months)")

    port_ret.reset_index().to_parquet(cfg.PROCESSED / "portfolio_returns.parquet", index=False)
    factors.to_csv(cfg.OUTPUT / "FF3_constructed.csv", index=False)
    print("    wrote portfolio_returns.parquet and outputs/FF3_constructed.csv")


if __name__ == "__main__":
    main()
