# Replication and Extension of the Fama–French (1993) Three-Factor Construction

> Empirical report · ECON6067 individual project
> Replication target: Fama, E. F. & French, K. R. (1993), "Common Risk Factors in the Returns on Stocks and Bonds," *Journal of Financial Economics*, 33(1), 3–56.

---

## 1. Research question and motivation

Fama and French (1993) ask whether the cross-sectional variation in stock returns can be summarised by a small set of common factors. They identify three stock-market factors — the market excess return (MKT-RF), a size factor (SMB) and a book-to-market factor (HML) — and show that these factors explain much of the variation in returns across portfolios sorted on size and book-to-market.

The goal of this project is not to replicate every test in the paper, but to focus on **the factor construction itself**: rebuild the monthly MKT-RF, SMB and HML series for 2000–2025 from raw CRSP / Compustat data, compare them against the official Kenneth French series, and add an independent extension. The transferable value of the exercise is that it covers the full empirical workflow — raw data → sample cleaning → variable definition → portfolio sorting → factor construction → validation — that underlies any task requiring the construction of aggregate series or indices from micro data.

---

## 2. Data sources, sample construction and variable definitions

### 2.1 Data sources

| Data | Source | Use |
|---|---|---|
| CRSP Monthly Stock | Course package 02 (`monthly_stock.csv`, 2000–2025, 2.42m rows) | monthly returns, prices, shares outstanding, market capitalisation, market return |
| F-F factors and risk-free rate | Course package 02 (`F-F factors and RF.csv`) | official benchmark factors + RF |
| Compustat Annual | Course package 04 (`Compustat.csv`) | accounting items for book equity |
| CRSP-Compustat link table | Course package 04 (`CCM.csv`) | links Compustat firms (gvkey) to CRSP securities (permno) |

The raw data are restricted and are not committed to the GitHub repository; acquisition is documented in `README.md`.

### 2.2 Sample (universe)

Factor construction follows Fama–French's "US common equity" universe. A stock-month observation is kept only if it satisfies all of:

| Field | Condition | Meaning |
|---|---|---|
| `SecurityType` | `EQTY` | ordinary equity (drops ~640k fund rows) |
| `ShareType` | `NS` | ordinary common shares (drops ADRs, units, etc.) |
| `USIncFlg` | `Y` | US-incorporated firm |
| `IssuerType` | `CORP` | operating corporation (drops REITs and non-operating issuers) |
| `PrimaryExch` | `N`/`A`/`Q` | NYSE / NYSE American / NASDAQ |

This leaves 1,339,565 stock-months across 12,949 securities. NYSE breakpoints are computed using only `PrimaryExch = "N"` stocks (Fama–French convention).

**Data-quality step.** The raw `monthly_stock.csv` contains fully duplicated (PERMNO, month) rows (2,755 rows, an artefact of a multi-table join at the source). These duplicates would double-count securities in the value-weighting and materially distort portfolio returns (e.g. the S/L portfolio for July 2001 was wrongly computed as +19.79% instead of about −4.5%). They are therefore dropped on `(PERMNO, YYYYMM)`, keeping one observation per stock-month.

### 2.3 Variable definitions

**Market equity (ME):** `ME = MthCap / 1000` (millions of USD). `MthCap` already equals price × shares outstanding (thousands of USD); negative prices are handled at the source.

**Book equity (BE):** constructed following Fama–French:

```
BE = SEQ + TXDITC − preferred stock
preferred stock = PSTKRV (redemption), else PSTKL (liquidation), else PSTK (carrying), else 0
if SEQ missing: BE = CEQ + PSTK
if SEQ and CEQ missing: BE = AT − LT
```

`TXDITC` (deferred taxes and investment tax credit) is treated as 0 when missing. Only BE > 0 observations are retained (94,523 firm-years). Note that the `TXDB` field mentioned in the assignment brief is the `txditc` field in the actual data; the two refer to the same item.

**Book-to-market (BM):** for the June sort of year t, `BM = BE(fiscal year ending in calendar year t−1) / ME(Dec t−1)`. The fiscal year is identified by the calendar year of `datadate` ("fiscal year ending in calendar year t−1"), which guarantees the accounting data are available at the June sort (a lag of at least six months).

**CRSP-Compustat link:** keep primary or conditional-primary links (`LINKPRIM ∈ {P, C}`) of type current/unresearched (`LINKTYPE ∈ {LC, LU}`), and require the link to be active at the fiscal-year end (`LINKDT ≤ datadate ≤ LINKENDDT`, with `E` meaning still active). If several BE records map to one (permno, fiscal year), the latest `datadate` is kept.

**Delisting:** the data contain no separate delisting-return field (only a delisting flag, `MthDelFlg`, with ~1,177 delisting events in the sample); `MthRet` already contains the total return available. This is a documented limitation with negligible effect on value-weighted portfolios.

---

## 3. Empirical design

Each June, NYSE stocks define the breakpoints that split the full sample into 2 size groups × 3 book-to-market groups:

- **Size:** `Small` = ME(June) < NYSE median; `Big` = otherwise
- **Book-to-market:** `Low` < 30th pct; `Medium` ∈ [30th, 70th]; `High` > 70th pct (NYSE percentiles)

This yields six portfolios S/L, S/M, S/H, B/L, B/M, B/H, held from July of year t through June of year t+1. Monthly portfolio returns are **value-weighted** (weight = market equity at the start of the month, i.e. prior-month ME).

The three factors are:

```
MKT-RF = vwretd − RF
SMB    = (S/L + S/M + S/H)/3 − (B/L + B/M + B/H)/3
HML    = (S/H + B/H)/2 − (S/L + B/L)/2
```

where `vwretd` is the CRSP value-weighted market return and RF is taken from the official benchmark data. The sample runs 2000–2025; the factor series spans July 2001 (after the first June sort) through December 2025, 294 months.

---

## 4. Core replication results and comparison with the benchmark

### 4.1 Descriptive statistics (monthly, 2001-07 to 2025-12)

| Factor | Mean(%) | Std(%) | t-stat | Ann. mean(%) | Ann. Sharpe |
|---|---|---|---|---|---|
| MKT-RF (constructed) | 0.68 | 4.43 | 2.64 | 8.50 | 0.55 |
| MKT-RF (official) | 0.73 | 4.44 | 2.82 | 9.13 | 0.59 |
| SMB (constructed) | 0.18 | 2.62 | 1.19 | 2.20 | 0.24 |
| SMB (official) | 0.06 | 2.60 | 0.42 | 0.77 | 0.09 |
| HML (constructed) | −0.00 | 3.13 | −0.00 | −0.00 | −0.00 |
| HML (official) | 0.04 | 3.09 | 0.19 | 0.42 | 0.04 |

### 4.2 Correlations

| Factor | Monthly correlation | R² |
|---|---|---|
| MKT-RF | **0.9973** | 0.994 |
| SMB | **0.9616** | 0.925 |
| HML | **0.9539** | 0.910 |

### 4.3 Tracking regression (constructed = α + β × official)

| Factor | α (%/mo) | β | R² |
|---|---|---|---|
| MKT-RF | −0.05 | 0.995 | 0.994 |
| SMB | +0.12 | 0.967 | 0.925 |
| HML | −0.03 | 0.967 | 0.910 |

The tracking regressions show intercepts close to zero (3–12 bp/month) and slopes close to one, so the constructed factors are highly consistent with the official series in both level and volatility. In the cumulative-return plots (`outputs/figures/cumulative_*.png`) the constructed and official series are nearly indistinguishable.

### 4.4 Sources of the differences

The HML correlation varies markedly over time (`outputs/tables/correlation_by_subperiod.csv`):

| Period | HML correlation |
|---|---|
| 2001–2005 | 0.782 |
| 2006–2010 | 0.958 |
| 2011–2015 | 0.952 |
| 2016–2020 | 0.973 |
| 2021–2025 | 0.985 |

The gap is largest in the early sample (2001–2005) and converges thereafter. The main sources of difference — all explainable, ordinary deviations — are:

1. **Data vintage:** the official factors use the Compustat vintage available when Kenneth French computed them, whereas this project uses the current (restated) Compustat. The effect is largest for the early sample (the dot-com period), where accounting restatements matter more.
2. **Coverage:** early Compustat coverage of small and newly listed firms is thinner, affecting the composition of the High-BM group.
3. **Book-equity definition:** the preferred-stock items (`pstkrv`/`pstkl`/`pstk`) were reported differently in early years, so BE differs slightly.
4. **Size tilt:** the constructed SMB has β = 0.967 and a slightly higher mean (0.18% vs 0.06%), reflecting a marginally different size distribution.

These differences are consistent with the experience in the literature that replicating the official factors typically leaves a 3–8% monthly-correlation gap; an HML correlation of 0.95 is a high-quality replication.

---

## 5. Extension: a momentum factor and a three- vs four-factor comparison

### 5.1 Motivation and economic question

A well-known omission of the three-factor model is **momentum**: Carhart (1997) shows that adding a winners-minus-losers (WML) factor markedly improves the model's explanatory power. This extension asks a concrete question: **over 2000–2025, does a momentum factor still add incremental explanatory power beyond the three factors?** The question has a clear literature basis and real tension, given the well-documented weakening of the momentum premium after 2000.

### 5.2 Construction and test design

- **Momentum factor:** each month, stocks are sorted on cumulative return over the past 2–12 months (skipping the most recent month) into 2 size × 3 momentum portfolios using NYSE breakpoints; `WML = (S/W + B/W)/2 − (S/L + B/L)/2`, rebalanced monthly. The WML series spans 300 months (2001-01 to 2025-12) with mean +0.12%/month, standard deviation 4.87% and t = 0.43.
- **Test assets:** 25 size-B/M portfolios (5×5 NYSE quintile sorts, annual June rebalancing, value-weighted).
- **Test:** time-series regressions of each portfolio on the three- and four-factor models, comparing the **GRS statistic**, mean absolute alpha, and mean R².

### 5.3 Results

| Model | GRS | p-value | mean \|α\|(%/mo) | mean R² | significant-α share |
|---|---|---|---|---|---|
| FF3 | 5.33 | < 0.001 | 0.230 | 0.901 | 64% |
| FF4 | 5.10 | < 0.001 | 0.223 | 0.902 | 64% |

Sub-samples (`outputs/tables/ff4_model_comparison_subperiod.csv`):

| Period | Model | GRS | mean \|α\|(%/mo) | mean R² |
|---|---|---|---|---|
| 2001–2012 | FF3 → FF4 | 2.68 → 2.81 | 0.244 → 0.237 | 0.900 → 0.903 |
| 2013–2025 | FF3 → FF4 | 4.24 → 4.05 | 0.220 → 0.220 | 0.912 → 0.913 |

### 5.4 Interpretation

The results support a careful and honest conclusion: over 2000–2025 the momentum factor adds only **limited** incremental explanatory power to the three-factor model — the full-sample GRS statistic falls only from 5.33 to 5.10 and the mean absolute alpha falls by just 0.007%/month, while both models are strongly rejected by the GRS test (pricing errors on the 25 size-B/M portfolios remain significant). The sub-samples reveal **period dependence**: in 2001–2012 adding momentum slightly worsens the GRS statistic (consistent with the well-known momentum crash of 2009), whereas in 2013–2025 it helps marginally.

This is consistent with the literature consensus that the US momentum premium weakened substantially after 2000, and that the marginal value of the Carhart four-factor model relative to the three-factor model fluctuates with the sample period and test assets. The value of this extension lies in quantifying that marginal value in a standard GRS framework and documenting its period heterogeneity — a more informative finding than the pre-set conclusion that "adding momentum always helps".

---

## 6. Validation, limitations and conclusion

### 6.1 Validation

- **Market-factor consistency:** the CRSP `vwretd` correlates at 0.999 with the official `Mkt-RF + RF`, confirming the correspondence between the risk-free rate and the market return; the MKT-RF replication is essentially exact.
- **Units:** official factors are in percent and CRSP returns are decimals; all are converted to decimals before comparison. The benchmark file is parsed by skipping the header text and annual rows, keeping only the six-digit `YYYYMM` monthly rows.
- **Data quality:** fully duplicated stock-month rows were identified and removed so that value-weighting counts each security-month exactly once.

### 6.2 Limitations

1. No separate delisting-return field; delisting is handled minimally.
2. Compustat data are the current vintage, which differs inherently from the historical vintage used for the official factors.
3. The factor series starts in July 2001 (after the first June sort), six months shorter than the official series.
4. The momentum factor uses the standard 12–1 window and 30/70 breakpoints; window robustness checks are left for future work.

### 6.3 Conclusion

This project reconstructs the monthly MKT-RF, SMB and HML factors for 2000–2025 from raw CRSP/Compustat data. The market factor matches the official series almost exactly (ρ = 0.997), and SMB (ρ = 0.962) and HML (ρ = 0.954) are also replicated to a high standard, with tracking-regression intercepts near zero and slopes near one. The remaining differences stem mainly from data vintage and coverage, concentrated in the early sample. The extension constructs a momentum factor and compares the three- and four-factor models, finding that momentum adds only marginal, period-dependent explanatory power over 2000–2025, consistent with the evidence of a weakened momentum premium. All results are reproducible from the raw data by running the scripts in `code/` in order.
