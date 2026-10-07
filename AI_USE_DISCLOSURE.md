# AI-Use Disclosure

This project was completed with the assistance of Claude Code (Anthropic Opus 5). This document records where and how AI was used, how its output was checked, and the important AI errors or suggestions that were corrected or rejected. I reviewed and take responsibility for every analytical conclusion, data choice, and the final report.

## 1. Where and how AI was used

| Stage | AI use |
|---|---|
| Data exploration | Reading the data dictionaries and raw CSVs, identifying field meanings, units, missingness and duplicates |
| Code writing | Drafting the six scripts under `code/` (cleaning, variable construction, sorting, factor construction, validation, extension) |
| Debugging | Locating the sources of replication divergence (duplicate rows, lagged-weight ordering) |
| Test implementation | Implementing the GRS test, tracking regressions, descriptive statistics and plots |
| Report drafting | Drafting the structure and text of `report.pdf` from the outputs |

## 2. How AI output was checked

- **Numerical verification item by item:** the constructed factors were compared with the official Kenneth French series factor-by-factor and month-by-month (correlations, tracking regressions, descriptive statistics); any anomaly (e.g. a 30-percentage-point deviation in a single month) was traced back to specific stocks and code logic.
- **Cross-checking against the data dictionary:** AI inferences about field meanings were verified against `DATA_DICTIONARY.md` and by sampling the actual data.
- **Script-by-script execution:** each script was run independently, and the scale, range and reasonableness of intermediate outputs (row counts, breakpoints, portfolio sizes) were checked.
- **Units and conventions:** CRSP returns (decimals) and F-F factors (percent) were distinguished and unified before comparison; NYSE breakpoints, fiscal-year lag and holding-period conventions were checked against Fama–French methodology.

## 3. Important AI errors or suggestions that were corrected or rejected

1. **Wrong ordering of the lagged market-equity weight (corrected).** The initial draft computed the start-of-month market-equity lag *after* merging with the portfolio-assignment table, so the first month of each holding period (every July) received a missing weight. This made the July 2001 HML equal −25.8% versus the official +4.95%. After diagnosis, the lag was computed on the full history *before* the merge, lifting the HML monthly correlation from 0.82 to 0.95.

2. **Unhandled duplicate rows in the raw data (corrected).** The initial draft did not detect fully duplicated (PERMNO, month) rows in `monthly_stock.csv` (2,755 rows), causing double-counting in the value-weighting and inflating the S/L portfolio return (e.g. +19.79% for July 2001). After confirming they were an artefact of the source join, deduplication on `(PERMNO, YYYYMM)` was added.

3. **Wrong column name in the CCM merge (corrected).** The initial draft referred to the CRSP identifier as `PERMNO` after merging, but the CCM table names it `LPERMNO`, causing a KeyError. This was fixed by renaming to `PERMNO`.

4. **Mismatch between the brief and the real fields (flagged and corrected by AI).** The brief's book-equity formula used `TXDB`/`PSTKRV`, while the actual data name the deferred-tax item `txditc` and the preferred-stock redemption value `pstkrv`. AI identified the inconsistency and used the correct fields.

5. **Redundant code introduced by AI (removed).** An early draft of the extension contained an unused placeholder function (`grs_stat` returning fixed values). On review it was found to have no real use and could mislead, so it was removed.

6. **A tendency toward an over-optimistic result (rejected).** AI could have framed the momentum extension as "adding momentum significantly improves the model"; the data in fact show a limited, period-dependent improvement. I insisted on reporting the weaker result faithfully, because an honest finding is more valuable than a pre-set positive conclusion.

## 4. Conclusion

AI carried out most of the mechanical work — code generation, debugging and drafting — substantially improving efficiency; but all key judgments — the sample universe, variable definitions, breakpoint rules, the tracing of anomalous results to their cause, and the faithful reporting of the "limited value of momentum" conclusion — were led and confirmed by me. Every step of AI output was verified against the benchmark and the raw data.
