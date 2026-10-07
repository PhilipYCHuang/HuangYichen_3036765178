"""01_data_prep.py — load raw data, apply universe filters, save clean intermediates.

Reads the four raw CSVs in place, applies the documented universe / link filters,
standardises units and dates, and writes compact parquet files to data/processed/.

Outputs (all under data/processed/):
    monthly_stock_clean.parquet   CRSP monthly, filtered to US common equity
    ff3_benchmark.parquet         Ken French Mkt-RF/SMB/HML/RF, 2000-2025, decimals
    compustat_clean.parquet       Compustat annual, USD industrial consolidated
    ccm_clean.parquet             CRSP-Compustat link table, primary/current links

Run:  python code/01_data_prep.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

import config as cfg


# --------------------------------------------------------------------------- #
# monthly_stock.csv
# --------------------------------------------------------------------------- #
_MONTHLY_COLS = [
    "PERMNO", "PERMCO", "YYYYMM", "MthCalDt",
    "MthRet", "MthRetx", "MthPrc", "ShrOut", "MthCap", "MthDelFlg",
    "PrimaryExch", "SecurityType", "ShareType", "USIncFlg", "IssuerType",
    "vwretd", "sprtrn",
]
_MONTHLY_DTYPE = {
    "PERMNO": "int64", "PERMCO": "int64", "YYYYMM": "int64",
    "MthRet": "float64", "MthRetx": "float64", "MthPrc": "float64",
    "ShrOut": "float64", "MthCap": "float64",
    "vwretd": "float64", "sprtrn": "float64",
    "MthCalDt": "str", "MthDelFlg": "str",
    "PrimaryExch": "str", "SecurityType": "str", "ShareType": "str",
    "USIncFlg": "str", "IssuerType": "str",
}


def load_monthly_stock() -> pd.DataFrame:
    """Load and filter the CRSP monthly file to the US common-equity universe."""
    print("[1/4] loading monthly_stock.csv ...")
    df = pd.read_csv(
        cfg.MONTHLY_STOCK_CSV,
        usecols=_MONTHLY_COLS,
        dtype=_MONTHLY_DTYPE,
        low_memory=False,
    )
    n0 = len(df)

    # Universe filters (see config.py for the rationale of each).
    df = df[
        df["SecurityType"].isin(cfg.SECURITY_TYPES)
        & df["ShareType"].isin(cfg.SHARE_TYPES)
        & (df["USIncFlg"] == cfg.US_FLAG)
        & df["IssuerType"].isin(cfg.ISSUER_TYPES)
        & df["PrimaryExch"].isin(cfg.EXCHANGES)
    ].copy()

    # The raw course file contains identical duplicate (PERMNO, month) rows
    # (an artifact of the source join across CRSP tables).  Drop them so each
    # stock-month is counted exactly once in the value-weighting.
    n_before = len(df)
    df = df.drop_duplicates(subset=["PERMNO", "YYYYMM"], keep="first")
    if n_before != len(df):
        print(f"    dropped {n_before - len(df):,} duplicate stock-month rows")

    # Dates and market equity.
    df["MthCalDt"] = pd.to_datetime(df["MthCalDt"], format="%Y-%m-%d")
    # MthCap is already price x shares, in thousands of USD.  ME in millions.
    df["ME_mm"] = df["MthCap"] / 1_000.0

    df = df[
        ["PERMNO", "PERMCO", "YYYYMM", "MthCalDt", "MthRet", "MthRetx",
         "MthPrc", "ShrOut", "MthCap", "ME_mm", "MthDelFlg",
         "PrimaryExch", "vwretd", "sprtrn"]
    ].sort_values(["PERMNO", "YYYYMM"])

    print(f"    rows: {n0:,} -> {len(df):,}  (dropped {n0 - len(df):,})")
    print(f"    unique PERMNO: {df['PERMNO'].nunique():,}")
    print(f"    window: {df['YYYYMM'].min()} -> {df['YYYYMM'].max()}")
    return df


# --------------------------------------------------------------------------- #
# F-F factors and RF.csv  (Ken French benchmark)
# --------------------------------------------------------------------------- #
def load_ff_benchmark() -> pd.DataFrame:
    """Parse the Ken French 3-factor file's monthly section (2000-2025)."""
    print("[2/4] parsing F-F factors and RF.csv ...")
    lines = cfg.FF_FACTORS_CSV.read_text(encoding="utf-8").splitlines()

    # The header row carries the 'Mkt-RF' label; rows after it are CSV data.
    hdr_idx = next(i for i, ln in enumerate(lines) if "Mkt-RF" in ln)

    rows: list[tuple[int, float, float, float, float]] = []
    for ln in lines[hdr_idx + 1:]:
        parts = [p.strip() for p in ln.split(",")]
        if not parts or not re.fullmatch(r"\d{6}", parts[0]):
            continue  # skip annual (YYYY) rows, blanks and the copyright line
        rows.append((int(parts[0]), *[float(p) for p in parts[1:5]]))

    df = pd.DataFrame(rows, columns=["YYYYMM", "MktRF", "SMB", "HML", "RF"])
    df = df[
        (df["YYYYMM"] >= cfg.START_YEAR * 100 + 1)
        & (df["YYYYMM"] <= cfg.END_YEAR * 100 + 12)
    ].copy()
    df.sort_values("YYYYMM", inplace=True)

    # Ken French reports returns in percent; convert to decimals to match CRSP.
    for c in ["MktRF", "SMB", "HML", "RF"]:
        df[c] = df[c] / 100.0

    print(f"    monthly rows 2000-2025: {len(df):,}")
    print(f"    window: {df['YYYYMM'].min()} -> {df['YYYYMM'].max()}")
    return df


# --------------------------------------------------------------------------- #
# Compustat.csv
# --------------------------------------------------------------------------- #
_COMPUSTAT_COLS = [
    "gvkey", "datadate", "fyear", "costat", "curcd", "datafmt", "indfmt", "consol",
    "at", "ceq", "lt", "pstk", "pstkl", "pstkrv", "seq", "txditc",
]


def load_compustat() -> pd.DataFrame:
    """Load Compustat annual and keep the USD industrial consolidated sample."""
    print("[3/4] loading Compustat.csv ...")
    df = pd.read_csv(cfg.COMPUSTAT_CSV, usecols=_COMPUSTAT_COLS)
    n0 = len(df)

    df = df[
        (df["curcd"] == "USD")
        & (df["indfmt"] == "INDL")
        & (df["datafmt"] == "STD")
        & (df["consol"] == "C")
        & (df["costat"] == "A")
    ].copy()

    df["datadate"] = pd.to_datetime(df["datadate"], format="%Y-%m-%d")
    df = df.sort_values(["gvkey", "datadate"])

    print(f"    rows: {n0:,} -> {len(df):,}")
    print(f"    fyear: {df['fyear'].min()} -> {df['fyear'].max()}")
    print(f"    unique gvkey: {df['gvkey'].nunique():,}")
    return df


# --------------------------------------------------------------------------- #
# CCM.csv
# --------------------------------------------------------------------------- #
def load_ccm() -> pd.DataFrame:
    """Load the CRSP-Compustat link table and keep valid primary/current links."""
    print("[4/4] loading CCM.csv ...")
    df = pd.read_csv(cfg.CCM_CSV)
    n0 = len(df)

    df = df[
        df["LINKPRIM"].isin(cfg.CCM_LINKPRIMS)
        & df["LINKTYPE"].isin(cfg.CCM_LINKTYPES)
    ].copy()

    df["LINKDT"] = pd.to_datetime(df["LINKDT"], format="%Y-%m-%d")
    # 'E' means the link is still active; store as NaT and treat as open-ended.
    df["LINKENDDT"] = df["LINKENDDT"].replace("E", pd.NaT)
    df["LINKENDDT"] = pd.to_datetime(df["LINKENDDT"], format="%Y-%m-%d")

    df = df[["gvkey", "LPERMNO", "LINKTYPE", "LINKPRIM", "LINKDT", "LINKENDDT"]]

    print(f"    rows: {n0:,} -> {len(df):,}")
    print(f"    unique gvkey: {df['gvkey'].nunique():,} | unique LPERMNO: {df['LPERMNO'].nunique():,}")
    return df


# --------------------------------------------------------------------------- #
def main() -> None:
    cfg.ensure_dirs()

    monthly = load_monthly_stock()
    ff3 = load_ff_benchmark()
    comp = load_compustat()
    ccm = load_ccm()

    print("\nwriting parquet intermediates ...")
    monthly.to_parquet(cfg.MONTHLY_CLEAN, index=False)
    ff3.to_parquet(cfg.FF3_BENCHMARK, index=False)
    comp.to_parquet(cfg.COMPUSTAT_CLEAN, index=False)
    ccm.to_parquet(cfg.CCM_CLEAN, index=False)
    print("done. files written to data/processed/")


if __name__ == "__main__":
    main()
