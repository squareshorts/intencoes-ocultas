# Intenções Ocultas - rare-bluffer invasion reproducibility package

Frozen source: private repository `squareshorts/intencoes-ocultas`, review branch
`review/action-specific-calibration`, starting at commit `7a9d834`.
Scientific report: `BLUFF_INVASION_REPORT_20261019.md`.

Use Python 3.11+ and install `numpy pandas scipy matplotlib pytest`.

Linux/macOS:

    PYTHONPATH=src python experiments/19_bluff_invasion.py --players 4 --games 2500 --boot 2000 --batch 250 --coupled
    PYTHONPATH=src python experiments/19_bluff_invasion.py --players 3 --games 1500 --boot 2000 --batch 250 --coupled
    PYTHONPATH=src python experiments/19_bluff_invasion.py --players 5 --games 1500 --boot 2000 --batch 250 --coupled
    PYTHONPATH=src python experiments/20_summarise_bluff_invasion.py --boots 5000
    PYTHONPATH=src pytest -q tests

PowerShell (from project root, after pip install):

    $env:PYTHONPATH = 'src'
    python experiments/19_bluff_invasion.py --players 4 --games 2500 --boot 2000 --batch 250 --coupled
    python experiments/20_summarise_bluff_invasion.py --boots 5000
    python -m pytest -q tests

The experiment supports checkpoint/resume of each size/threshold/forecast
trial. To re-run from scratch, rename or remove that trial's `paired_coupled_*.csv` first.
Do not edit the historical results/exp2*, results/exp3*, or results/exp4*.

The experiment-only CoupledBluffAgent is not a production agent and does not
change the historical evolutionary runs. For the diagnostic RNG drift comparison,
run the same command without `--coupled`; those are noncausal audit results.

The primary 4-player family uses 9 exact paired tests with Holm correction.
3- and 5-player experiments are exploratory cross-size checks.

`manifest_sha256.txt` contains the SHA256 hashes of every included file except
itself. All outcomes are simulated, and three rule assumptions remain unconfirmed.
