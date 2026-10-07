# data/raw/

Place the original input data files here (they are restricted and **not** committed to GitHub).

Download the two course packages and copy the four CSVs below into this folder:

| File | Package | Source |
|---|---|---|
| `monthly_stock.csv` | 02 | CRSP Monthly Stock (2000–2025) |
| `F-F factors and RF.csv` | 02 | Kenneth French 3 factors + risk-free rate |
| `Compustat.csv` | 04 | Compustat Fundamentals Annual |
| `CCM.csv` | 04 | CRSP-Compustat link table |

Keep the CSV filenames unchanged. `code/config.py` reads these four paths directly.
