"""05_validation.py — compare constructed factors to the Ken French benchmark.

Produces:
    outputs/tables/descriptive_stats.csv       summary stats (both series)
    outputs/tables/correlation.csv             monthly correlations
    outputs/tables/tracking_regression.csv     regress constructed on benchmark
    outputs/tables/correlation_by_subperiod.csv
    outputs/figures/cumulative_{MKT_RF,SMB,HML}.png   cumulative-return plots

Run:  python code/05_validation.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as cfg

FACTORS = ["MKT_RF", "SMB", "HML"]


def load_merged() -> pd.DataFrame:
    mine = pd.read_csv(cfg.OUTPUT / "FF3_constructed.csv")
    bench = pd.read_parquet(cfg.FF3_BENCHMARK).rename(
        columns={"YYYYMM": "date", "MktRF": "MKT_RF_b", "SMB": "SMB_b", "HML": "HML_b"}
    )
    return mine.merge(bench, on="date", how="inner")


def summary_stats(df: pd.DataFrame, col: str) -> pd.Series:
    x = df[col].dropna()
    n = len(x)
    mean = x.mean()
    std = x.std(ddof=1)
    t = mean / (std / np.sqrt(n)) if std > 0 else np.nan
    ann_mean = (1 + mean) ** 12 - 1
    ann_std = std * np.sqrt(12)
    sharpe = ann_mean / ann_std if ann_std > 0 else np.nan
    return pd.Series(
        {
            "n": n,
            "mean": mean,
            "std": std,
            "t_stat": t,
            "min": x.min(),
            "max": x.max(),
            "skew": x.skew(),
            "kurt": x.kurt(),
            "ann_mean": ann_mean,
            "ann_std": ann_std,
            "ann_sharpe": sharpe,
        }
    )


def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for f in FACTORS:
        rows[f] = summary_stats(df, f)
        rows[f"{f}_bench"] = summary_stats(df, f"{f}_b")
    return pd.DataFrame(rows).T


def correlation_table(df: pd.DataFrame) -> pd.DataFrame:
    out = {}
    for f in FACTORS:
        c = df[[f, f"{f}_b"]].corr().iloc[0, 1]
        out[f] = {"correlation": c, "R2": c**2}
    return pd.DataFrame(out).T


def tracking_regression(df: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for f in FACTORS:
        y = df[f].values
        X = np.column_stack([np.ones(len(y)), df[f"{f}_b"].values])
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        yhat = X @ b
        r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
        rows[f] = {"alpha_monthly": b[0], "beta": b[1], "R2": r2, "n": len(y)}
    return pd.DataFrame(rows).T


def correlation_by_subperiod(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["yr"] = df["date"] // 100
    periods = [(2001, 2005), (2006, 2010), (2011, 2015), (2016, 2020), (2021, 2025)]
    rows = []
    for lo, hi in periods:
        s = df[(df["yr"] >= lo) & (df["yr"] <= hi)]
        row = {"period": f"{lo}-{hi}"}
        for f in FACTORS:
            row[f] = s[f].corr(s[f"{f}_b"])
        rows.append(row)
    return pd.DataFrame(rows)


def cumulative_plot(df: pd.DataFrame, f: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    x = pd.to_datetime(df["date"].astype(str), format="%Y%m")
    mine = (1 + df[f]).cumprod() - 1
    bench = (1 + df[f"{f}_b"]).cumprod() - 1
    ax.plot(x, mine * 100, lw=1.4, label="Constructed")
    ax.plot(x, bench * 100, lw=1.4, ls="--", label="Ken French benchmark")
    ax.set_title(f"Cumulative {f} (2000-2025)", fontsize=12)
    ax.set_ylabel("Cumulative return (%)")
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(cfg.FIGURES / f"cumulative_{f}.png", dpi=150)
    plt.close(fig)


def write_markdown_table(df: pd.DataFrame, path) -> None:
    df.to_csv(path.with_suffix(".csv"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(df.round(4).to_markdown())


def main() -> None:
    cfg.ensure_dirs()
    print("[1/4] merging constructed factors with benchmark ...")
    df = load_merged()
    print(f"    overlap: {len(df):,} months  ({df['date'].min()} - {df['date'].max()})")

    print("[2/4] descriptive statistics ...")
    desc = descriptive_stats(df)
    print(desc[["mean", "std", "t_stat", "ann_mean", "ann_sharpe"]].round(4).to_string())
    desc.to_csv(cfg.TABLES / "descriptive_stats.csv")

    print("[3/4] correlations and tracking regressions ...")
    corr = correlation_table(df)
    reg = tracking_regression(df)
    sub = correlation_by_subperiod(df)
    print("\ncorrelations:")
    print(corr.round(4).to_string())
    print("\ntracking regression (constructed = alpha + beta * benchmark):")
    print(reg.round(4).to_string())
    corr.to_csv(cfg.TABLES / "correlation.csv")
    reg.to_csv(cfg.TABLES / "tracking_regression.csv")
    sub.to_csv(cfg.TABLES / "correlation_by_subperiod.csv", index=False)

    print("[4/4] cumulative return plots ...")
    for f in FACTORS:
        cumulative_plot(df, f)
    print("    wrote figures to outputs/figures/")
    print("\ndone.")


if __name__ == "__main__":
    main()
