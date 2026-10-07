"""Shared paths and constants for the Fama-French (1993) three-factor replication.

All scripts import from here so that the raw-data locations, processed-data
locations, and output locations are defined in exactly one place.  Raw data is
read in place from the two numbered package folders (never copied or committed).
"""
from pathlib import Path

# Project root = parent of the code/ directory.
ROOT = Path(__file__).resolve().parent.parent

# --- Raw data (documented input location; restricted, NOT committed) ---
RAW = ROOT / "data" / "raw"

MONTHLY_STOCK_CSV = RAW / "monthly_stock.csv"          # CRSP monthly (2000-2025)
FF_FACTORS_CSV = RAW / "F-F factors and RF.csv"        # Ken French benchmark
COMPUSTAT_CSV = RAW / "Compustat.csv"                  # annual accounting
CCM_CSV = RAW / "CCM.csv"                              # CRSP-Compustat link table

# --- Processed intermediates (regenerable from raw; firm-level -> not committed) ---
PROCESSED = ROOT / "data" / "processed"
MONTHLY_CLEAN = PROCESSED / "monthly_stock_clean.parquet"
FF3_BENCHMARK = PROCESSED / "ff3_benchmark.parquet"
COMPUSTAT_CLEAN = PROCESSED / "compustat_clean.parquet"
CCM_CLEAN = PROCESSED / "ccm_clean.parquet"

# --- Outputs (tables, figures, final factor series -> committed) ---
OUTPUT = ROOT / "outputs"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"

# --- Universe / sample constants -------------------------------------------------
# CRSP common-share US equity universe used for factor construction.
# SecurityType == "EQTY"  : ordinary equity (drops ~644k fund rows)
# ShareType    == "NS"    : ordinary common shares (drops ADRs, units, etc.)
# USIncFlg     == "Y"     : US-incorporated firms
# IssuerType   == "CORP"  : operating corporations (drops REITs / non-operating)
# PrimaryExch in {N,A,Q}  : NYSE / NYSE American (AMEX) / NASDAQ
SECURITY_TYPES = {"EQTY"}
SHARE_TYPES = {"NS"}
US_FLAG = "Y"
ISSUER_TYPES = {"CORP"}
EXCHANGES = {"N", "A", "Q"}
# NYSE exchange code, used only to define size / BM breakpoints (FF convention).
NYSE_EXCH = "N"

# Sample window for the factor series.
START_YEAR, END_YEAR = 2000, 2025

# Valid CRSP-Compustat link types (current / unresearched), primary or
# conditional-primary links.  This follows the standard FF replication rule.
CCM_LINKTYPES = {"LU", "LC"}
CCM_LINKPRIMS = {"P", "C"}


def ensure_dirs() -> None:
    """Create output directories if they do not yet exist."""
    for d in (PROCESSED, TABLES, FIGURES):
        d.mkdir(parents=True, exist_ok=True)
