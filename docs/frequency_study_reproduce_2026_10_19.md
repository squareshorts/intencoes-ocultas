# Reproducing manuscript figures and results

The code snapshot implements the historical game simulator, with source at `src/intencoes/`; strategies and calibration coefficients are frozen. Python 3.11+ with NumPy, pandas, Matplotlib, scipy, pytest and package dependencies listed in `requirements.txt` is required. Run these commands from the archive root:

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python -m pytest -q tests
PYTHONPATH=src python experiments/22_analyse_frequency.py --boots 1500
PYTHONPATH=src python experiments/24_build_supp_tables.py
```

The full game data are already bundled under `results/frequency_dependence` and `results/bluff_invasion`; you do not need to re-simulate them to inspect results. Exact script options for full rerun are in the study protocol files under `results/frequency_dependence/` and in the script `--help` output; running all games may take considerable time. The 1,500-resample final analysis of `evolutionary_summary.csv` is frozen; re-running with independent bootstrap seeds will shift the confidence interval endpoints slightly.

To build the manuscript, change into `manuscript/`, run `pdflatex main.tex`, `biber main`, then `pdflatex main.tex` twice. Run `pdflatex supplement.tex` twice for supplement. Scientific figures are bundled in `manuscript/figures/`. Any public archived DOI and author declaration have not yet been assigned.

The previous rare-mutant protocol includes one set of noncoupled simulations intentionally retained as an audit of an RNG-stream flaw; only records tagged `paired_coupled` support the main claims. The original phase-locked frequency pilot is excluded from the archive.
