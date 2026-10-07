"""06_extension.py — momentum factor and a three- vs four-factor comparison.

Extension question: does adding a momentum factor (Carhart 1997) improve the
explanatory power of the three-factor model?

Steps:
  1. Construct a monthly momentum factor WML (winners-minus-losers) using a
     12-1 momentum signal (cumulative return from t-12 to t-2, skipping the most
     recent month), sorted into 2 size x 3 momentum portfolios with NYSE
     breakpoints, rebalanced monthly.
  2. Construct 25 size x book-to-market test portfolios (5x5 NYSE quintile
     sorts, annual June rebalancing).
  3. Regress each test portfolio on the 3-factor model and on the 4-factor
     model; compare the GRS statistic, average absolute alpha, and mean R2.

Outputs:
    outputs/tables/momentum_factor.csv      monthly WML series
    outputs/tables/ff4_model_comparison.csv GRS / alpha / R2 comparison
    outputs/figures/extension_alpha_bar.png per-portfolio |alpha|, FF3 vs FF4

Run:  python code/06_extension.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as sps

import config as cfg


# --------------------------------------------------------------------------- #
# 1. Momentum factor
# --------------------------------------------------------------------------- #
def compute_momentum(monthly: pd.DataFrame) -> pd.DataFrame:
    """Add a 12-1 momentum column: cum return over [t-12, t-2], as a decimal."""
    m = monthly[["PERMNO", "YYYYMM", "ME_mm", "MthRet", "PrimaryExch"]].copy()
    m = m.sort_values(["PERMNO", "YYYYMM"])
    m["gross"] = 1.0 + m["MthRet"]
    # 11-month trailing product ending at the current month...
    m["mom11"] = m.groupby("PERMNO")["gross"].transform(
        lambda s: s.rolling(11, min_periods=11).apply(np.prod, raw=True)
    )
    # ...shifted by two months so mom(t) = product over [t-12, t-2].
    m["mom"] = m.groupby("PERMNO")["mom11"].shift(2) - 1.0
    m["ME_lag"] = m.groupby("PERMNO")["ME_mm"].shift(1)
    return m


def momentum_factor(monthly: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Return (monthly WML series, 6 momentum-portfolio return matrix)."""
    m = compute_momentum(monthly)

    nyse = m[m["PrimaryExch"] == cfg.NYSE_EXCH]
    bps = nyse.groupby("YYYYMM").agg(
        size_med=("ME_lag", "median"),
        mom_p30=("mom", lambda s: s.quantile(0.30)),
        mom_p70=("mom", lambda s: s.quantile(0.70)),
    )
    m = m.merge(bps, on="YYYYMM", how="left")

    m["size_b"] = np.where(m["ME_lag"] < m["size_med"], "S", "B")
    m["mom_b"] = np.select(
        [m["mom"] < m["mom_p30"], m["mom"] <= m["mom_p70"]],
        ["L", "M"], default="W",
    )
    m["port"] = m["size_b"] + "/" + m["mom_b"]

    v = m[m["MthRet"].notna() & (m["ME_lag"] > 0) & m["mom"].notna()].copy()
    v["w_r"] = v["MthRet"] * v["ME_lag"]
    g = v.groupby(["YYYYMM", "port"]).agg(w_r=("w_r", "sum"), w=("ME_lag", "sum"))
    ret = (g["w_r"] / g["w"]).unstack("port")
    ret = ret.reindex(columns=["S/L", "S/M", "S/W", "B/L", "B/M", "B/W"])

    wml = ret[["S/W", "B/W"]].mean(axis=1) - ret[["S/L", "B/L"]].mean(axis=1)
    wml.name = "WML"
    return wml, ret


# --------------------------------------------------------------------------- #
# 2. 25 size x BM test portfolios (5x5, annual NYSE quintiles)
# --------------------------------------------------------------------------- #
def assign_quintiles(panel: pd.DataFrame) -> pd.DataFrame:
    """Assign 1..5 size and BM quintile buckets using NYSE 20/40/60/80 pct."""
    frames = []
    for _, grp in panel.groupby("sort_year"):
        nyse = grp[grp["is_nyse"]]
        s_breaks = [nyse["ME_June"].quantile(q) for q in (0.2, 0.4, 0.6, 0.8)]
        b_breaks = [nyse["BM"].quantile(q) for q in (0.2, 0.4, 0.6, 0.8)]
        g = grp.copy()
        g["sz"] = pd.cut(g["ME_June"], [-np.inf, *s_breaks, np.inf], labels=[1, 2, 3, 4, 5])
        g["bmq"] = pd.cut(g["BM"], [-np.inf, *b_breaks, np.inf], labels=[1, 2, 3, 4, 5])
        g["port"] = g["sz"].astype(str) + "x" + g["bmq"].astype(str)
        frames.append(g)
    return pd.concat(frames, ignore_index=True)


def value_weighted_returns(
    monthly: pd.DataFrame, assignment: pd.DataFrame
) -> pd.DataFrame:
    """Value-weighted monthly returns for an annual June-rebalanced assignment."""
    m = monthly[["PERMNO", "YYYYMM", "ME_mm", "MthRet"]].copy()
    m = m.sort_values(["PERMNO", "YYYYMM"])
    m["w"] = m.groupby("PERMNO")["ME_mm"].shift(1)          # lagged ME
    m["sort_year"] = (m["YYYYMM"] // 100) - ((m["YYYYMM"] % 100) < 7).astype(int)

    merged = m.merge(assignment[["PERMNO", "sort_year", "port"]],
                     on=["PERMNO", "sort_year"], how="inner")
    merged = merged[merged["MthRet"].notna() & (merged["w"] > 0)]
    merged["w_r"] = merged["MthRet"] * merged["w"]
    g = merged.groupby(["YYYYMM", "port"]).agg(w_r=("w_r", "sum"), w=("w", "sum"))
    return (g["w_r"] / g["w"]).unstack("port")


# --------------------------------------------------------------------------- #
# 3. Factor-model regressions and GRS test
# --------------------------------------------------------------------------- #
def model_comparison(test_ret: pd.DataFrame, factors3: pd.DataFrame,
                     factors4: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for label, factors in [("FF3", factors3), ("FF4", factors4)]:
        common = test_ret.index.intersection(factors.index)
        Y = test_ret.loc[common].values
        F = factors.loc[common]
        T, N = Y.shape
        K = F.shape[1]
        X = np.column_stack([np.ones(T)] + [F[c].values for c in F.columns])
        betas = np.linalg.lstsq(X, Y, rcond=None)[0]
        alpha = betas[0, :]
        resid = Y - X @ betas
        resid_cov = resid.T @ resid / (T - K - 1)

        # GRS
        a = alpha.reshape(-1, 1)
        mu = F.mean().values.reshape(-1, 1)
        Omega = np.cov(F.values, rowvar=False, ddof=1)
        Sinv = np.linalg.inv(resid_cov)
        Oinv = np.linalg.inv(Omega)
        shp2 = (mu.T @ Oinv @ mu).item()
        grs = ((T - N - K) / N) * (a.T @ Sinv @ a).item() / (1 + shp2)
        pval = 1 - sps.f.cdf(grs, N, T - N - K)

        r2 = 1 - (resid ** 2).sum(axis=0) / ((Y - Y.mean(axis=0)) ** 2).sum(axis=0)

        # proper t-statistics for each alpha
        X_inv = np.linalg.inv(X.T @ X)
        se_alpha = np.sqrt(resid_cov.diagonal() * X_inv[0, 0])
        t_alpha = alpha / se_alpha

        rows[label] = {
            "n_assets": N, "T": T, "K": K,
            "grs": grs, "grs_pval": pval,
            "avg_abs_alpha": float(np.abs(alpha).mean()),
            "avg_abs_alpha_pct_mo": float(np.abs(alpha).mean() * 100),
            "mean_r2": float(r2.mean()),
            "share_sig_alpha_5pct": float((np.abs(t_alpha) > 1.96).mean()),
        }
    return pd.DataFrame(rows).T


# --------------------------------------------------------------------------- #
def main() -> None:
    cfg.ensure_dirs()
    monthly = pd.read_parquet(cfg.MONTHLY_CLEAN)

    print("[1/4] constructing momentum factor ...")
    wml, mom_port = momentum_factor(monthly)
    print(f"    WML series: {wml.index.min()} -> {wml.index.max()} ({len(wml)} months)")
    print(f"    WML mean={wml.mean()*100:+.2f}%/mo  std={wml.std()*100:.2f}%  t={wml.mean()/wml.std()*np.sqrt(len(wml)):+.2f}")
    wml.to_frame().reset_index().rename(columns={"YYYYMM": "date"}).to_csv(
        cfg.TABLES / "momentum_factor.csv", index=False)

    print("[2/4] constructing 25 size x BM test portfolios ...")
    panel = pd.read_parquet(cfg.PROCESSED / "bm_me_panel.parquet")
    panel5 = assign_quintiles(panel)
    assignment = panel5[["PERMNO", "sort_year", "port"]]
    test_ret = value_weighted_returns(monthly, assignment)
    print(f"    25-portfolio returns: {test_ret.index.min()} -> {test_ret.index.max()}")
    test_ret = test_ret.dropna(how="any")
    print(f"    non-missing rows: {len(test_ret)}")

    print("[3/4] aligning factors ...")
    ff3 = pd.read_csv(cfg.OUTPUT / "FF3_constructed.csv").set_index("date")[["MKT_RF", "SMB", "HML"]]
    ff4 = ff3.join(wml.rename("WML"), how="inner")

    print("[4/4] model comparison (GRS test) ...")
    comp = model_comparison(test_ret, ff3, ff4)
    print(comp.round(4).to_string())
    comp.to_csv(cfg.TABLES / "ff4_model_comparison.csv")

    # sub-period comparison: momentum's marginal value may differ by period
    print("\nsub-period comparison:")
    sub_rows = []
    for lo, hi in [(2001, 2012), (2013, 2025)]:
        tr = test_ret[(test_ret.index // 100 >= lo) & (test_ret.index // 100 <= hi)]
        f3 = ff3[(ff3.index // 100 >= lo) & (ff3.index // 100 <= hi)]
        f4 = ff4[(ff4.index // 100 >= lo) & (ff4.index // 100 <= hi)]
        c = model_comparison(tr, f3, f4)
        c["period"] = f"{lo}-{hi}"
        c = c.reset_index().rename(columns={"index": "model"})
        sub_rows.append(c)
    sub = pd.concat(sub_rows, ignore_index=True)
    print(sub.round(4).to_string(index=False))
    sub.to_csv(cfg.TABLES / "ff4_model_comparison_subperiod.csv", index=False)

    # per-portfolio |alpha| bar chart
    fig, ax = plt.subplots(figsize=(9, 5))
    common = test_ret.index.intersection(ff3.index)
    for label, fac in [("FF3", ff3), ("FF4", ff4)]:
        c = test_ret.index.intersection(fac.index)
        Y = test_ret.loc[c].values
        F = fac.loc[c]
        X = np.column_stack([np.ones(len(c))] + [F[col].values for col in F.columns])
        al = np.linalg.lstsq(X, Y, rcond=None)[0][0, :]
        ax.plot(range(1, 26), np.abs(al) * 100, marker="o", ms=4, lw=1.2, label=label)
    ax.set_xlabel("Size-BM portfolio (sorted by size quintile, then BM quintile)")
    ax.set_ylabel("|alpha| (% per month)")
    ax.set_title("Absolute pricing error, FF3 vs FF4 (25 size-BM portfolios)")
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(cfg.FIGURES / "extension_alpha_bar.png", dpi=150)
    plt.close(fig)

    print("\ndone. wrote momentum_factor.csv, ff4_model_comparison.csv, extension_alpha_bar.png")


if __name__ == "__main__":
    main()
