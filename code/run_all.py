"""run_all.py — run the full pipeline end-to-end with a single command.

With the raw data in place (see README), this reproduces every table and figure
without any manual editing of data or code:

    python code/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "01_data_prep.py",
    "02_variable_construction.py",
    "03_portfolio_sorting.py",
    "04_factor_construction.py",
    "05_validation.py",
    "06_extension.py",
]


def main() -> None:
    code_dir = Path(__file__).resolve().parent
    for name in SCRIPTS:
        print(f"\n{'=' * 70}\nRunning {name}\n{'=' * 70}")
        result = subprocess.run([sys.executable, str(code_dir / name)], cwd=code_dir)
        if result.returncode != 0:
            print(f"\n[FAILED] {name} exited with code {result.returncode}")
            sys.exit(result.returncode)
    print("\nAll steps completed successfully. Outputs are in outputs/ and data/processed/.")


if __name__ == "__main__":
    main()
