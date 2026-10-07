"""02_variable_construction.py — build BE, link to CRSP, compute BM.

Pipeline:
  1. Book equity (BE) from Compustat annual, following Fama-French's definition.
  2. Link BE to CRSP PERMNOs via the CRSP-Compustat link table, honouring the
     link start/end dates so the correct information is attached at each point.
  3. Merge BE with December / June market equity and build the book-to-market
     ratio (BM = BE / ME_Dec) used at each June sort.

Outputs (data/processed/):
    be_linked.parquet   PERMNO x fiscal-end-year book equity (linked, BE > 0)
    bm_me_panel.parquet PERMNO x sort_year panel: ME_June, ME_Dec, BE, BM, is_nyse

Run:  python code/02_variable_construction.py
"""
from __future__ import annotations

import pandas as pd

import config as cfg


# --------------------------------------------------------------------------- #
# 1. Book equity
# --------------------------------------------------------------------------- #
def build_book_equity(comp: pd.DataFrame) -> pd.DataFrame:
    """Return Compustat rows with a Fama-French book equity (BE) column.

    FF definition:
      BE = SEQ + TXDITC - preferred_stock,
      preferred_stock = PSTKRV (redemption), else PSTKL (liquidation),
                        else PSTK (carrying), else 0.
      If SEQ is missing:  BE = CEQ + PSTK   (PSTK = 0 if missing).
      If SEQ and CEQ missing: BE = AT - LT.
    Missing TXDITC / preferred-stock items are treated as 0.  Only BE > 0 kept.
    """
    c = comp.copy()

    preferred = (
        c["pstkrv"].fillna(c["pstkl"]).fillna(c["pstk"]).fillna(0.0)
    )
    txditc = c["txditc"].fillna(0.0)
    pstk0 = c["pstk"].fillna(0.0)

    seq = c["seq"]
    ceq = c["ceq"]
    at = c["at"]
    lt = c["lt"]

    be = seq + txditc - preferred
    # Fallback 1: common equity + preferred carrying value.
    be = be.where(seq.notna(), ceq + pstk0)
    # Fallback 2: total assets - total liabilities.
    be = be.where(seq.notna() | ceq.notna(), at - lt)

    c["BE"] = be
    c = c[c["BE"] > 0].copy()
    return c


# --------------------------------------------------------------------------- #
# 2. Link BE to CRSP PERMNO
# --------------------------------------------------------------------------- #
def link_be_to_crsp(comp_be: pd.DataFrame, ccm: pd.DataFrame) -> pd.DataFrame:
    """Attach each BE observation to the CRSP PERMNO whose link is active at
    the fiscal-year end date (LINKDT <= datadate <= LINKENDDT, NaT = open)."""
    merged = comp_be.merge(ccm, on="gvkey", how="inner")

    active = (merged["LINKDT"] <= merged["datadate"]) & (
        merged["LINKENDDT"].isna() | (merged["datadate"] <= merged["LINKENDDT"])
    )
    linked = merged[active].copy()

    # Calendar year in which the fiscal year ends -> the year that BE is
    # available for (used at the June sort of the following year).
    linked["fye_year"] = linked["datadate"].dt.year
    # The CCM link maps gvkey to LPERMNO (the CRSP permanent identifier).
    linked = linked.rename(columns={"LPERMNO": "PERMNO"})

    # One BE per PERMNO per fiscal-end year: keep the latest report date.
    linked = linked.sort_values(["PERMNO", "fye_year", "datadate"])
    linked = linked.drop_duplicates(["PERMNO", "fye_year"], keep="last")

    out = linked[["PERMNO", "fye_year", "BE"]].sort_values(["PERMNO", "fye_year"])
    return out


# --------------------------------------------------------------------------- #
# 3. Merge with market equity and build BM
# --------------------------------------------------------------------------- #
def build_bm_panel(
    monthly: pd.DataFrame, be_linked: pd.DataFrame
) -> pd.DataFrame:
    """Build a PERMNO x sort_year panel with the June-sort inputs.

    For the June sort of year t:
        BE      = book equity of fiscal year ending in calendar year t-1
        ME_Dec  = market equity at December of year t-1 (BM denominator)
        ME_June = market equity at June of year t          (size sorting)
        BM      = BE / ME_Dec
        is_nyse = primary exchange is NYSE in June t (used for breakpoints)
    """
    m = monthly[["PERMNO", "YYYYMM", "ME_mm", "PrimaryExch"]].copy()
    m["year"] = m["YYYYMM"] // 100

    me_dec = m[m["YYYYMM"] % 100 == 12][["PERMNO", "year", "ME_mm"]].rename(
        columns={"ME_mm": "ME_Dec", "year": "dec_year"}
    )
    me_jun = m[m["YYYYMM"] % 100 == 6][
        ["PERMNO", "year", "ME_mm", "PrimaryExch"]
    ].rename(columns={"ME_mm": "ME_June", "year": "jun_year"})

    frames = []
    for t in range(cfg.START_YEAR, cfg.END_YEAR + 1):
        be = be_linked[be_linked["fye_year"] == t - 1][
            ["PERMNO", "BE"]
        ]
        md = me_dec[me_dec["dec_year"] == t - 1][["PERMNO", "ME_Dec"]]
        mj = me_jun[me_jun["jun_year"] == t][["PERMNO", "ME_June", "PrimaryExch"]]

        df = be.merge(md, on="PERMNO", how="inner").merge(
            mj, on="PERMNO", how="inner"
        )
        # Positive market equity is required for a well-defined BM / size sort.
        df = df[(df["ME_Dec"] > 0) & (df["ME_June"] > 0)].copy()

        df["sort_year"] = t
        df["BM"] = df["BE"] / df["ME_Dec"]
        df["is_nyse"] = df["PrimaryExch"] == cfg.NYSE_EXCH

        frames.append(
            df[["PERMNO", "sort_year", "BE", "ME_Dec", "ME_June", "BM", "is_nyse"]]
        )

    panel = pd.concat(frames, ignore_index=True)
    return panel.sort_values(["sort_year", "PERMNO"])


# --------------------------------------------------------------------------- #
def main() -> None:
    cfg.ensure_dirs()
    print("[1/3] building book equity ...")
    comp = pd.read_parquet(cfg.COMPUSTAT_CLEAN)
    comp_be = build_book_equity(comp)
    print(f"    Compustat rows with BE > 0: {len(comp_be):,}")

    print("[2/3] linking BE to CRSP PERMNO ...")
    ccm = pd.read_parquet(cfg.CCM_CLEAN)
    be_linked = link_be_to_crsp(comp_be, ccm)
    print(f"    linked PERMNO x fye_year rows: {len(be_linked):,}")
    print(f"    unique PERMNO: {be_linked['PERMNO'].nunique():,}")

    print("[3/3] merging with market equity and building BM panel ...")
    monthly = pd.read_parquet(cfg.MONTHLY_CLEAN)
    panel = build_bm_panel(monthly, be_linked)
    print(f"    panel rows: {len(panel):,}  |  unique PERMNO: {panel['PERMNO'].nunique():,}")
    print(f"    stocks per sort year (median): {panel.groupby('sort_year').size().median():.0f}")
    print(f"    NYSE share of panel: {panel['is_nyse'].mean():.3f}")

    print("\nwriting parquet intermediates ...")
    be_linked.to_parquet(cfg.PROCESSED / "be_linked.parquet", index=False)
    panel.to_parquet(cfg.PROCESSED / "bm_me_panel.parquet", index=False)
    print("done.")


if __name__ == "__main__":
    main()
