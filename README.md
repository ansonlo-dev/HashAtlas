# HashAtlas: Can a Small Bitcoin Miner Still Win?

**CDS3004 Data Mining group project** (Lingnan University, 2026/27 Term 1, CRN 234). Team HashAtlas, five members;
names, roles and contributions are in [`configs/team.json`](configs/team.json) and section 17 of the report.

| Submission item | Where |
|---|---|
| GitHub repository (public, full commit history) | **https://github.com/ORGANISATION/REPOSITORY** (replace before submission) |
| Project report (PDF, with each member's contributions) | [`reports/technical_report.pdf`](reports/technical_report.pdf) |
| Presentation (~16 min, five presenters) and script | [`presentation/HashAtlas.pptx`](presentation/HashAtlas.pptx), [`.pdf`](presentation/HashAtlas.pdf), [`slide_by_slide_script.md`](presentation/slide_by_slide_script.md) |
| Agent-use trajectories (one per member) | [`agent_trajectories/README.md`](agent_trajectories/README.md) |
| Live interactive dashboard | <https://cds3004.ansonlo.dev/> |
| Submission checklist and rubric map | [`SUBMISSION.md`](SUBMISSION.md) |

We mined the complete Bitcoin block history (every block since 3 January 2009, labelled with its miner) to answer
three questions:

1. **Classification**: can a block's *behavioural fingerprint* (version-bit rolling, nonce bits, timestamps, how it
   is filled) reveal who mined it, a pool or a solo miner, without reading the miner's name? (decision tree, KNN,
   linear and RBF SVM, month-grouped and nested cross-validation, sealed out-of-time test)
2. **Clustering and association rules**: do the data rediscover the CPU → GPU → ASIC eras by themselves, and which
   pools build blocks alike? (K-means, four hierarchical linkages, DBSCAN; Apriori implemented from scratch)
3. **Decisions**: should a miner in Hong Kong or elsewhere in Asia mine in a pool, mine solo as a lottery, or switch
   off, today and after the 2028 halving? (miner advisor across 27 economies, scenario Future Lab with a backtest)

<!-- KEY RESULTS START -->
## Key results

|  | Result |
| :--- | :--- |
| Data | 975,494 blocks (heights 0-975,493), 0 missing / 0 duplicate heights; label precision 99.95% vs mempool.space |
| Fingerprint classifier (sealed test 2025-04 → 2026-10) | Decision tree: macro-F1 0.244 (95% CI 0.238-0.249), accuracy 42%, top-3 69%, template-family accuracy 46%; baselines ≤ 0.081 |
| Blocks mined after the freeze | 36.1% correct on 1,446 unseen blocks |
| Eras (unsupervised) | K-means K=3 ARI 0.71; Ward ARI 0.89 vs documented hardware eras |
| Association rules | 837 frequent itemsets from 120,538 blocks; 103 rules; brute-force check passed |
| Hong Kong miner advice | S21 loss 7.26 USD/day at 0.175 USD/kWh (break-even 0.089); 1.2 TH/s home miner: 1 in 16,362 per year |
| Future Lab | 2028 halving ~2028-04-07; backtest 80% band coverage 75% |
| Verification | 17/17 independent checks passed |
<!-- KEY RESULTS END -->

## Requirements

- Linux or macOS; Python 3.12 managed by [uv](https://docs.astral.sh/uv/) (dependencies locked in `uv.lock`).
- For the PDF report: `pandoc` 3.x and TeX Live with `latexmk`, LuaLaTeX and the Libertinus fonts.
- For the dashboard: [Bun](https://bun.sh) (`web/`), and Node + a local Chrome for the browser check.
- For the slides: Node with `pptxgenjs` (`presentation/build`), LibreOffice for the PDF export.
- Internet access to `gz.blockchair.com`, `mempool.space`, `api.blockchain.info` and `globalpetrolprices.com`.

## Reproduce

```bash
uv sync                          # create the environment from uv.lock
uv run pytest -q                 # unit tests
uv run hashatlas acquire         # download (resumable; SHA-256 provenance in artifacts/source_manifest.json)
uv run hashatlas run-all         # clean → features → train → evaluate → explain → clusters → rules → decide
                                 # → future → figures → webdata → verify → report → notebook
cd web && bun install && bun test src && bun run validate-data && bun run build   # dashboard
node scripts/e2e.mjs             # bounded browser check, screenshots in reports/screenshots/
cd ../presentation/build && bun install && ./make.sh                              # slides + PDF
```

| Stage | What it does | Main outputs |
|---|---|---|
| `acquire` | Blockchair daily dumps (2009-2018), mempool.space per-pool block lists (2019+) and gap fill, pool definitions, solo-service lists, network charts, electricity prices | `data/raw/`, `artifacts/source_manifest.json` |
| `clean` | Typed loading of ~975k blocks, source merge, labels (mempool.space attribution / coinbase tags / address guess), label audit, quality report, data dictionary | `data/interim/blocks.parquet`, `artifacts/quality_report.json`, `artifacts/data_dictionary.csv` |
| `features` | Fingerprint features (bit decomposition, ratios, day-relative policy), weekly/day economics, hardware frontier, break-even prices | `data/processed/` |
| `train` | Feature selection (variance, MI vs noise probes, Spearman, group ablation), tree/KNN/SVM search with month-grouped CV, nested CV, template families, frozen model choice | `artifacts/feature_selection.json`, `model_search.json`, `model_selection.json`, `models/` |
| `evaluate` | Sealed-test metrics, confusion, ROC/PR, day-block bootstrap, drift, newcomer pools | `artifacts/test_metrics.json` |
| `explain` | Tree export, hand-checked Gini split, complexity curve, permutation importance, KNN neighbours, SVM coefficients | `artifacts/explanations.json` |
| `clusters` | Era discovery (K-means, 4 linkages, DBSCAN), pool families, anomalous blocks | `artifacts/clusters.json` |
| `rules` | From-scratch Apriori with brute-force check, rules, later-window confirmation, pool signatures, solo contrast | `artifacts/rules.json` |
| `decide` | Unknown-block attribution and concentration, post-freeze blocks, miner advisor | `artifacts/decisions.json` |
| `future` | Hash-rate scenario paths, halving timing, device break-even, backtest of two resampling windows | `artifacts/future.json` |
| `figures`, `webdata`, `verify`, `report`, `notebook` | Report/slide figures (white and paper-toned), dashboard data, independent checks, report PDF, executed notebook | `reports/`, `web/public/data/`, `artifacts/verification.json`, `notebooks/` |

**New examples:** `uv run hashatlas predict --heights 975400 975401` fingerprints blocks (prediction first, the
revealed label separately); `uv run hashatlas predict --ths 200 --watts 3500 --country "Hong Kong"` gives miner advice.

`data/` is regenerated and not committed; `artifacts/`, `models/`, `reports/` and `web/public/data/` are committed so
the evidence can be reviewed without rerunning.

## Repository layout

```
configs/            config.yaml (all settings), team.json (members and contributions)
src/hashatlas/      acquire, clean, features, train, evaluate, explain, clusters, rules, decide, future,
                    figures, webdata, verify, report, notebook, predict, cli
tests/              unit tests (bit decomposition, leakage, Apriori vs brute force, economics, bootstrap)
artifacts/          evidence files (JSON/CSV)        models/   fitted pipelines (joblib)
reports/            technical_report.{md,tex,pdf}, figures/, screenshots/, latex/
notebooks/          executed walkthrough notebook     web/      React + TypeScript + ECharts dashboard
presentation/       HashAtlas.pptx/.pdf, script, timing, build/  agent_trajectories/  per-member agent logs
```

## Data sources and terms

Blockchair daily dumps (free tier; cite Blockchair), mempool.space REST API and the open-source
[`mempool/mining-pools`](https://github.com/mempool/mining-pools) definitions, blockchain.com charts API,
GlobalPetrolPrices electricity price table (dated snapshot). Blocks are public, pseudonymous records; no personal data
is used. Outputs are historical analysis and scenarios, **not financial advice**.

## Version control

Every member commits their own work; the full history is kept (no fresh "clean" repository). The dashboard is
deployed with Cloudflare Workers (`web/wrangler.jsonc`) at <https://cds3004.ansonlo.dev/>.
