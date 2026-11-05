"""Stage 14 - generate and execute a short walkthrough notebook (notebooks/hashatlas_walkthrough.ipynb).

The notebook reads the committed artifacts and processed data, re-derives a few headline numbers in plain
pandas, and shows key figures, so a reader can follow the analysis without running the whole pipeline.
"""
from __future__ import annotations

import nbformat
from nbclient import NotebookClient

from .config import ROOT

CELLS = [
    ("md", "# HashAtlas walkthrough\nCan a small Bitcoin miner still win? This notebook loads the pipeline outputs "
           "(run `uv run hashatlas run-all` first) and re-derives headline numbers independently."),
    ("code", "import json, pandas as pd, numpy as np\nfrom pathlib import Path\nA = Path('../artifacts')\n"
             "q = json.load(open(A/'quality_report.json'))\nprint('blocks:', q['rows_loaded'], '| heights', q['height_range'])\n"
             "print('label audit agreement:', round(q['label_audit']['agreement'], 4), 'on', q['label_audit']['blocks_compared'], 'blocks')"),
    ("md", "## 1. Who mines? Unattributed share and solo blocks by year"),
    ("code", "b = pd.read_parquet('../data/interim/blocks.parquet', columns=['time','miner','is_solo'])\n"
             "y = b.groupby(b['time'].dt.year).agg(blocks=('miner','size'), unknown=('miner', lambda s: (s=='Unknown').mean()), solo=('is_solo','sum'))\ny.round(3)"),
    ("md", "## 2. Fingerprint classifier: recompute macro-F1 from the saved test predictions"),
    ("code", "p = pd.read_parquet('../data/processed/test_predictions.parquet')\n"
             "from sklearn.metrics import f1_score, confusion_matrix\nprint('macro-F1', round(f1_score(p['y'], p['pred'], average='macro'), 4))\n"
             "tm = json.load(open(A/'test_metrics.json'))\nprint('published', round(tm['families'][tm['operational_family']]['macro_f1'], 4))\n"
             "pd.crosstab(p['y'], p['pred'], normalize='index').round(2)"),
    ("md", "## 3. Eras rediscovered by K-means (weekly rows)"),
    ("code", "w = pd.read_parquet('../data/processed/weeks.parquet')\npd.crosstab(w['kmeans'], w['era'])"),
    ("md", "## 4. Association rules (top 10 by lift)"),
    ("code", "r = json.load(open(A/'rules.json'))\npd.DataFrame(r['rules'])[['antecedent','consequent','support','confidence','lift','confirm_confidence']].head(10)"),
    ("md", "## 5. Miner advisor: Hong Kong vs Asia (Antminer S21, business tariff)"),
    ("code", "d = json.load(open(A/'decisions.json'))\na = pd.DataFrame(d['advisor'])\n"
             "a[(a.device=='Antminer S21') & (a.tariff=='business') & a.asia][['country','price_usd_kwh','pool_income_usd_day','electricity_usd_day','profit_usd_day','recommendation']].sort_values('price_usd_kwh')"),
    ("md", "## 6. Future Lab: halving timing and backtest"),
    ("code", "f = json.load(open(A/'future.json'))\nprint(f['halving'])\npd.DataFrame(f['backtest']['rows'])[['origin','horizon_days','inside_80pct_band','median_error_pct','persistence_error_pct']]"),
    ("md", "## 7. Independent verification"),
    ("code", "v = json.load(open(A/'verification.json'))\nprint(v['passed'], '/', v['total'])\npd.DataFrame(v['checks'])[['check','passed']]"),
]


def run() -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(s) if k == "md" else nbformat.v4.new_code_cell(s) for k, s in CELLS]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    out = ROOT / "notebooks" / "hashatlas_walkthrough.ipynb"
    out.parent.mkdir(exist_ok=True)
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(out.parent)}}).execute()
    nbformat.write(nb, out)
    print("notebook executed:", out.relative_to(ROOT))
