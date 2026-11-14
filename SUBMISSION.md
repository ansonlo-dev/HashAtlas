# CDS3004 Data Mining group project: submission guide

Team **HashAtlas** (CRN 234, five members; names, IDs and roles in [`configs/team.json`](configs/team.json)).
GitHub repository: **https://github.com/ORGANISATION/REPOSITORY** (replace with the team's public repository URL).
Live dashboard: <https://cds3004.ansonlo.dev/>.

## 1. What the instructor asked for (special tutorial, 2 Oct 2026)

| Requirement | Where it is |
|---|---|
| Teams of 3-5 (CRN 234) | Five members, `configs/team.json` |
| Workflow: real problem → data → techniques → evaluation → visualisation and interpretation → communication | Report sections 2-16; slides 1-18 (incl. the intro video); dashboard |
| "Impress me": interesting question + usable data + appropriate analysis | 975,494 real Bitcoin blocks; three questions matched to classification, clustering and association rules |
| Hosted on GitHub; every member commits; full history kept | This repository; make it **public** before submission |
| Presentation file (PPTX or PDF) | `presentation/HashAtlas.pptx`, `presentation/HashAtlas.pdf` |
| One ZIP by the captain with: README + GitHub URL, code folder, report **PDF** with member contributions, agent trajectories | `README.md`; repository snapshot; `reports/technical_report.pdf` (section 17); `agent_trajectories/` |
| Agents used as assistants; human plan review and output verification; ≥ 10 rounds per member | Report section 15; `artifacts/verification.json`; trajectories |
| Deadlines: slides before the week 12-13 presentations; materials 23:59, 6 Dec 2026 | – |

## 2. Rubric map

### Project (22%)

| Criterion | Evidence |
|---|---|
| Problem definition: problem, constraints, alternatives | Report §2 (users, Q1-Q3 with success criteria, six constraints, five alternatives); slides 3-4 |
| Solution design: related, innovative, clearly explained | Report §3 (three observation units, pipeline, four design innovations); slides 2, 5, 7 |
| Data collection & preprocessing: collect, load large data, feature types, missing/noisy data | Report §4: ~975k blocks from four sources, parallel typed loading, data dictionary with conceptual scales, quality table (missing fields, out-of-order timestamps kept, empty blocks, gap filling), label audit on 424k blocks |
| Feature selection | Report §6: variance filter, mutual information vs noise probes, Spearman redundancy, group ablation (wrapper); control feature removed as designed |
| Feature transformation | Report §5: bit decomposition of nominal bit fields, log1p, ratios, day-relative policy features, cyclic encoding, standardisation in pipelines, weekly aggregation, break-even economics |
| Data visualisation | 18 report figures + paper-toned versions in the slides; interactive ECharts dashboard (8 pages) |
| Data-mining method usage | Decision tree, KNN, linear/RBF SVM; K-means, single/complete/average/Ward, DBSCAN; Apriori (from scratch) + contrast mining |
| Model learning procedure | Grids, month-grouped CV, nested CV, complexity curve, worked Gini split, frozen model choice; report §7 |
| Performance evaluation | Out-of-time validation and sealed test, baselines, macro-F1, balanced accuracy, top-3 and family accuracy, per-class table, ROC/PR, day-block bootstrap, drift; report §8 |
| Result interpretation and limitations | Report §8-13 (pool-level ceiling explained by template sharing, KNN/SVM vs tree geometry, DBSCAN limits, backtest weakness) |
| Decision making on new examples | Report §11: unknown-block attribution, blocks mined after the freeze, miner advisor; `hashatlas predict`; dashboard Advisor, Fingerprint Lab |

### Presentation (8%)

Time and pace: 20-minute slot = 1:30 intro video + ~16:30 speaking (five presenters, 3:14–3:23 each) + ~2:00 buffer (word-count timing per slide) (`presentation/timing_check.csv`); content organisation: one
question per section, Q1-Q3 answered on the closing slide; tools: one consistent "Ledger" theme (paper, ink, Bitcoin orange) shared by slides, video and dashboard, native charts, live demo
with screenshot fallback; delivery, engagement, attire, speech: see `presentation/qa_and_presenter_preparation.md`.

## 3. Actions only the team can do before submission

- [ ] Put real names (and optionally student IDs) in `configs/team.json`; rebuild: `uv run hashatlas webdata report` and
      `cd presentation/build && ./make.sh`.
- [ ] Check every contribution statement matches what each member actually did.
- [ ] Create the GitHub repository, push the **full history**, make it public, and put its URL in `configs/team.json`,
      `README.md` and this file.
- [ ] Every member commits their own work from their own GitHub account.
- [ ] Every member exports their agent trajectory (≥ 10 rounds) and lists it in `agent_trajectories/README.md`.
- [ ] Two timed rehearsals including the live demo; dress professionally on the day.
- [ ] Captain builds the ZIP (README, code folder, report PDF, trajectories) and submits on Moodle by 23:59, 6 Dec 2026.
