"""Stage 13 - the technical report: reports/technical_report.md (every number read from artifacts/), then the
LaTeX/PDF build (reports/latex/build.sh: pandoc -> LuaLaTeX)."""
from __future__ import annotations

import subprocess
from datetime import date

import pandas as pd

from .config import ARTIFACTS, REPORTS, ROOT, cfg, read_json

FAM = {"tree": "Decision tree", "knn": "KNN", "svm_linear": "Linear SVM", "svm_rbf": "RBF SVM",
       "decision_stump": "Decision stump (depth 1)", "stratified_random": "Stratified random", "majority": "Majority class"}


def f(x, d=3):
    return "n/a" if x is None else f"{x:,.{d}f}"


def p(x, d=1):
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def n(x):
    return f"{int(x):,}"


def table(header, rows, align=None):
    align = align or ["l"] + ["r"] * (len(header) - 1)
    sep = ["---:" if a == "r" else ":---" for a in align]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fig(name, caption):
    return f"![{caption}](figures/{name}.png)"


def odds(pr):
    return "n/a" if not pr else (f"1 in {1 / pr:,.0f}" if pr < 0.2 else p(pr))


def build_markdown() -> str:
    c = cfg()
    q = read_json(ARTIFACTS / "quality_report.json")
    src = read_json(ARTIFACTS / "source_manifest.json")
    fs = read_json(ARTIFACTS / "feature_selection.json")
    split = read_json(ARTIFACTS / "split_manifest.json")
    sel = read_json(ARTIFACTS / "model_selection.json")
    ms = read_json(ARTIFACTS / "model_search.json")
    tm = read_json(ARTIFACTS / "test_metrics.json")
    ex = read_json(ARTIFACTS / "explanations.json")
    cl = read_json(ARTIFACTS / "clusters.json")
    ru = read_json(ARTIFACTS / "rules.json")
    dec = read_json(ARTIFACTS / "decisions.json")
    fu = read_json(ARTIFACTS / "future.json")
    ver = read_json(ARTIFACTS / "verification.json")
    feat = read_json(ARTIFACTS / "features_summary.json")
    team = read_json(ROOT / "configs" / "team.json")
    runlog = read_json(ARTIFACTS / "run_log.json") if (ARTIFACTS / "run_log.json").exists() else {}

    op = tm["operational_family"]
    T = tm["families"]
    S = ms["families"]
    nested = ms["nested_cv_tree"]
    la = q["label_audit"]
    ua = dec["unknown_attribution"]
    nb = dec["new_blocks"]
    st = dec["network_state"]
    adv = pd.DataFrame(dec["advisor"])
    s21 = adv[(adv["device"] == "Antminer S21") & (adv["tariff"] == "business")].sort_values("price_usd_kwh")
    s21_be = float(s21["breakeven_usd_kwh"].iloc[0])
    viable = s21[s21["price_usd_kwh"] <= s21_be]["country"].tolist()
    hk = adv[(adv["country"] == "Hong Kong") & (adv["tariff"] == "business")].set_index("device")
    bitaxe = adv[adv["device"].str.startswith("Bitaxe")].iloc[0]
    bt = fu["backtest"]["summary"]
    btc = fu["backtest_comparison"]
    tf = sel["template_families"]
    multi_fams = [g for g in tf["groups"] if len(g) > 1]
    pf = cl["pool_families"]
    pf_multi = [g for g in pf["families"] if len(g) > 1]
    rules_sorted = sorted(ru["rules"], key=lambda r: -r["lift"])
    top_rule = rules_sorted[0] if rules_sorted else None
    sigs = [s for s in ru["pool_signatures"] if s["top"]]
    fam_names = {k: v for k, v in tf["map"].items()}
    eras_prof = cl["profiles"]
    imp = ex["permutation_importance"][:8]
    rs = ex["root_split_worked"]
    hard_era_ari = cl["ari_vs_hardware_eras"]["kmeans"]
    ward = cl["hierarchical"]["ward"]
    solo_years = q["labels"]["solo_blocks"]
    test_solo = tm["solo_operating_point"]
    devs = pd.DataFrame(fu["devices"])
    wk = pd.read_parquet(ROOT / "data" / "processed" / "weeks.parquet")
    wcol = wk.columns[0]
    ward_bounds = [str(d.date()) for d in wk.loc[wk["hier_ward"] != wk["hier_ward"].shift(), wcol].iloc[1:]]
    members = team["members"]
    today = date.today().strftime("%d %B %Y")
    best_by_val = max(["tree", "knn", "svm_linear", "svm_rbf"], key=lambda k: S[k]["validation"]["macro_f1"])
    best_by_test = max(["tree", "knn", "svm_linear", "svm_rbf"], key=lambda k: T[k]["macro_f1"])
    newcomers = tm["newcomer_pools"][:8]
    fam_of = {m: tuple(g) for g in pf["families"] for m in g}
    agree = [r for r in tm["newcomer_pools"] if r["top_prediction"] in fam_of.get(r["miner"], ())]
    same = [r for r in tm["newcomer_pools"]
            if any(r["miner"] in g and r["top_prediction"] in g for g in pf["families"])]
    readas = [r for r in tm["newcomer_pools"] if r["top_share"] >= 0.45][:4]
    agree_text = ("pools that are rare or absent in training are mostly read as an existing pool with a similar "
                  "fingerprint (" + "; ".join(f"{r['miner']} → {r['top_prediction']} {p(r['top_share'], 0)}" for r in readas) + ")"
                  + (", and " + ", ".join(f"{r['miner']} is read as {r['top_prediction']}, which the dendrogram places in the same family"
                                          for r in same[:2]) if same else "") + ".")
    stump = T["decision_stump"]["macro_f1"]
    weak = [FAM[k] for k in ("knn", "svm_linear", "svm_rbf") if T[k]["macro_f1"] <= stump]
    beat_text = ("KNN and both SVMs also beat the majority and random baselines in accuracy and top-3 accuracy, but "
                 f"{', '.join(weak)} do not beat the one-split tree in macro-F1." if weak else
                 "KNN and both SVMs also beat all three baselines, by smaller margins.")
    per_class = tm["per_class"]

    md = []
    md.append(f'''---
title: "HashAtlas: Can a Small Bitcoin Miner Still Win?"
subtitle: "Mining 975,494 Bitcoin blocks for miner fingerprints, mining eras, pool families and miner decisions across Asia"
team: "Team {team['team_name']} · {', '.join(m['name'] for m in members)} · CRN {team['crn']}"
date: "{team['course']} · {today}"
---

# 1. Introduction

In January 2009 anyone with a laptop could mine Bitcoin. Seventeen years later the network computes about
{f(st['hashrate_ths_30d'] / 1e6, 0)} exahashes per second, block production is dominated by industrial pools, and yet every few
weeks a news story reports that a hobbyist with a single small device has "won the lottery" and mined a whole block
on their own. **Can a small miner still win?** And if you live in Hong Kong or elsewhere in Asia, what should you
actually do with a mining device: join a pool, mine solo as a lottery ticket, or switch it off?

This project answers these questions with data mining on the complete Bitcoin block history: **{n(q['rows_loaded'])}
blocks** from the genesis block (3 January 2009) to height {n(q['height_range'][1])} ({c['sources']['last_day']}),
labelled with the entity that mined each one. We combine three complementary techniques, each matched to a question:

* **Classification** (decision tree, KNN, SVM): can the *behavioural fingerprint* a miner leaves in a block (version-bit
  rolling, nonce bits, timestamps, how the block is filled) reveal who mined it, without reading the miner's name?
* **Clustering** (K-means, four hierarchical linkages, DBSCAN): do the data rediscover the CPU → GPU → ASIC history of
  mining on their own, and which pools build their blocks in the same way?
* **Association rules** (Apriori, implemented from scratch): which block properties co-occur with which miners?

The models are then **applied to new examples**: blocks with no pool tag, blocks mined after our data freeze, and
miner set-ups in {sum(e["available"] for e in dec["electricity"])} economies. A limited **Future Lab** explores what the 2028 halving means for small miners, with a
backtest that shows how far such projections can be trusted. An interactive dashboard presents every result:
<{team['live_site']}>.

The rest of the report follows the course's six-step data-mining workflow: problem (section 2), design (3), data (4),
transformation and selection (5-6), mining and evaluation (7-10), decisions and interpretation (11-13), and
communication, ethics and agent use (14-16). Each member's contributions are listed in section 17.

# 2. Problem definition

## 2.1 Users and decisions

* **A would-be home or small-business miner in Hong Kong or Asia** deciding whether a device is worth running, and how
  (pool or solo).
* **Analysts, journalists and regulators** asking how decentralised block production really is: a pool's *name* on a
  block does not say who built the block template.
* **Pool operators and researchers** who want to know which on-chain behaviours identify a miner (a privacy question).

## 2.2 Questions and success criteria

| ID | Question | Technique | Success criterion (set before testing) |
|---|---|---|---|
| Q1 | From a block's fingerprint alone, which mining entity produced it? Can solo blocks be spotted? | Classification | Clearly beat majority / random / one-split baselines on an out-of-time test; report per-class results and the Solo class honestly |
| Q2a | Do the data rediscover the hardware eras without being told? | Clustering | Adjusted Rand index (ARI) against the documented eras clearly above 0; contiguous eras |
| Q2b | Which pools build blocks alike? | Clustering + rules | Families that are stable across linkages and consistent with the classifier's confusions |
| Q3 | What should a miner in Hong Kong / Asia do, now and after the 2028 halving? | Decisions on new examples | Advice that follows from the data, with explicit odds and break-even prices; future scenarios with a published backtest error |

## 2.3 Constraints

1. **Labels are self-declared.** A block's miner is known only from the text a miner writes in the coinbase or from a
   known payout address. Labels can be missing ("Unknown"), copied or shared, and the label text itself must never
   be used as a model input (it would be leakage).
2. **No look-ahead.** Pools appear, merge and disappear over time, so evaluation must be out-of-time: train on the
   past, validate on the next period, test once on the most recent period.
3. **Extreme class imbalance.** Solo-mining services won only {n(solo_years)} blocks in history, about
   {split['test']['solo']} in the whole test period.
4. **Data access and scale.** Nearly a million blocks from free public sources with rate limits; the pipeline must
   resume, verify and record provenance. (The free Blockchair quota ran out mid-download; section 4 explains the switch.)
5. **Compute.** One workstation: SVM and nested cross-validation need bounded, documented samples.
6. **Ethics.** Public but pseudonymous data; no personal data; outputs must not be presented as investment advice.

## 2.4 Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Predict the BTC price | Not a data-mining question about mining; prices are driven by external events; widely shown to be unreliable |
| Identify pools by their coinbase tag | That is the *label*; a lookup table, not data mining, and fails exactly when a tag is absent or shared |
| Transaction-level analysis (address clustering) | Billions of rows; out of scope for one term and raises re-identification concerns |
| Deep learning on raw block bytes | Not interpretable, not taught in this course, and would hide *why* blocks are similar |
| Other crypto topics (Solana rug pulls, stablecoin de-pegs) | Considered at topic selection; Bitcoin mining offered the most complete, verifiable data across all three techniques |

# 3. Solution design

The design uses **three observation units**, one per question, so that each technique works on data whose meaning
fits it:

| Unit | Rows | Used for | Time meaning |
|---|---:|---|---|
| Block (2019-01 → 2026-11) | {n(feat['modern_blocks'])} | Fingerprint classification, association rules, anomalies | Each block is observed when mined |
| Week (2009 → 2026-10) | {n(cl['weeks'])} | Era discovery (K-means, hierarchical, DBSCAN) | Weekly aggregate of all blocks |
| Pool profile (2024 → 2026-10) | {len(pf['pools'])} | Pool families (hierarchical) | Mean fingerprint of each pool |
| Device × economy | {len(adv)} | Miner advisor | Network state at the data freeze |

**Pipeline** (`uv run hashatlas run-all`, {len(runlog) or 15} stages): acquire → clean and label → features →
selection and training (frozen model choice) → sealed test → explanations → clustering → rules → decisions → Future
Lab → figures → web data → independent verification → report → notebook. Every stage writes its evidence to
`artifacts/` and is reproducible from `configs/config.yaml` (random seed {c['project']['random_seed']}).

**What is new in this design.** (i) Fingerprints are learnt from *behaviour only*: the label source is excluded and the
version and nonce fields are decomposed into bits because they are nominal bit fields, not quantities. (ii)
Day-relative features remove market conditions so that only a miner's *policy* remains. (iii) Classification and
clustering are joined: "template families" found by hierarchical clustering on training data explain the classifier's
confusions and give a second, family-level evaluation. (iv) Decisions are made on genuinely new blocks mined *after*
the analysis freeze, and the Future Lab backtests its own method.

# 4. Data collection and preprocessing

## 4.1 Sources and acquisition

| Source | Content | Size |
|---|---|---:|
| Blockchair daily block dumps | Every block 2009-2018 (one gzip TSV per day) | {n(q['rows_from_dumps'])} rows |
| mempool.space API: per-pool block lists + gap fill | Every block from 1 Jan 2019 (height {n(c['sources']['mempool_start_height'])}) to {c['sources']['last_day']}, with mempool.space's pool attribution and fee-rate percentiles | {n(q['rows_from_mempool'])} rows; {n(src['mempool_blocks']['calls'])} API calls |
| mempool.space mining-pool definitions (open source) | {src['pool_definitions']['n_definitions']} pools, coinbase tags and payout addresses | 1 JSON |
| mempool.space solo-service block lists | {n(src['solo']['solo_blocks'])} blocks of {len(src['solo']['by_service'])} solo services | 1 JSON |
| blockchain.com charts | Daily hash rate, price, miner revenue, fees since 2009 | {n(src['charts']['hash-rate']['points'])} days |
| GlobalPetrolPrices (dated snapshot) | Household and business electricity prices, USD/kWh | {src['electricity']['countries']} countries |

**Loading a large dataset.** The ~4,000 daily dump files are read in parallel with explicit dtypes and only the needed
columns, concatenated (about one million rows), de-duplicated by height and stored as Parquet. Every raw file has a
SHA-256 hash in `artifacts/source_manifest.json`; downloads resume and retry with back-off. Mid-way through, the free
Blockchair dump quota was exhausted (HTTP 402), so from 2019 onwards every block was fetched from mempool.space per
pool (100 blocks per call), and any isolated height missing from either source was filled individually. The final
table has **no missing and no duplicate heights** ({n(q['height_range'][0])} to {n(q['height_range'][1])}).

## 4.2 Attribute types

Conceptual measurement scale is recorded separately from storage type (Lecture 2). Key decisions:

* `version` and `nonce` are stored as integers but are **nominal bit fields**: bit 13 being set says something about
  the miner's software; "version = 0x2FFFE000 is larger than 0x20000000" says nothing. They are decomposed into bits.
* `height` is ordinal (a position), `time` is interval, counts and sizes are ratio-scaled, `miner` is nominal.
* The full data dictionary with scale, discrete/continuous status and role is in `artifacts/data_dictionary.csv`
  (and the dashboard's Methods page).

## 4.3 Data quality: problems found and how they were handled

| Issue | Finding | Handling |
|---|---|---|
| Missing values | Total input/output value and coin-days destroyed are not provided by mempool.space ({n(q['missing_values'].get('cdd_total', 0))} rows) | Not used (not needed); fee rate recomputed where missing |
| Out-of-order timestamps | {n(q['timestamp_earlier_than_previous_block'])} blocks ({p(q['timestamp_earlier_than_previous_share'], 2)}) have an earlier timestamp than their predecessor | **Kept**: consensus allows it; it reflects miner clocks and is a candidate fingerprint, not an error |
| Empty blocks | {n(q['empty_blocks'])} coinbase-only blocks | Kept; genuine miner behaviour (an empty-block flag is a feature) |
| Under-claimed rewards | {n(q.get('under_claimed_reward_blocks', 0))} blocks claimed less than subsidy + fees (mostly 2011-2013 pool software); none claimed more | Kept; the subsidy is taken from the schedule, revenue from what was actually claimed |
| Difficulty consistency | Difficulty bits change only at retarget heights ({q['difficulty_changes_off_retarget']} violations) | Verified |
| Unattributed blocks | "Unknown" miner: {p(q['unknown_miner_share_by_year'].get('2010', 0), 0)} of blocks in 2010, {p(q['unknown_miner_share_by_year'].get('2024', 0), 2)} in 2024 | A genuine state, not a missing value: excluded from training, used as the application set (section 11) |
| Heavy tails / noise | Fees, transaction counts and sizes span orders of magnitude | log1p transforms; extremes are real (e.g. inscription-heavy blocks), so none deleted |

{fig('f04_label_quality', 'Unattributed share of blocks by year, and the source of every label.')}

## 4.4 Label quality audit

Labels for 2019+ come from mempool.space's attribution (coinbase tags *and* payout addresses, curated). Labels for
2009-2018 come from our own transparent labeller: the first matching coinbase tag from the same open definition
file, then Blockchair's address-based guess. To measure how good our labeller is, we **re-applied it to all
{n(la['blocks_compared'])} mempool.space-labelled blocks** and compared:

* when our labeller finds a tag, it agrees with mempool.space **{p(la['precision_when_tag_found'], 2)}** of the time;
* it finds a tag for {p(la['coverage_tag_found'], 1)} of blocks; the rest are mainly pools identified only by payout
  address (largest: {la['top_disagreements'][0]['mempool']}, {n(la['top_disagreements'][0]['n'])} blocks), which our
  labeller marks Unknown rather than guessing;
* overall agreement {p(la['agreement'], 1)}. Early-era labels are therefore precise but somewhat incomplete, which
  only affects descriptive statistics (section 9), not the 2019+ models.

{fig('f02_who_mines', 'Share of blocks per quarter: unattributed early miners gave way to pools by 2013-2014.')}

# 5. Feature transformation

All transformations are fitted on training data only where they have parameters (scaling, bins).

| Transformation | Applied to | Why |
|---|---|---|
| Bit decomposition | version bits 13-28 (BIP320 general-purpose bits used by ASICBoost rolling), count of rolled bits, BIP9 top bits, signal bits; nonce bits 0-31 | Nominal bit fields: each bit is a binary attribute; distances on the raw integer would be meaningless |
| log1p | transaction count, fees, fee rate, minimum fee rate, mean transaction size | Heavy right tails |
| Ratios and shares | fullness = weight / 4,000,000; witness share; fee share of reward; log(outputs) − log(inputs) | Comparable across eras and block sizes |
| **Day-relative policy** | fee rate, minimum/median fee, fee percentiles, transaction count, fullness, each minus the median of all blocks that day | Removes market conditions (busy vs quiet days) so that only the miner's template policy remains |
| Cyclic encoding | hour of day (sin, cos) | Included as a **deliberately irrelevant control**: blocks are found at random times, so selection should remove it |
| Standardisation | all features, inside the KNN and SVM pipelines (fitted per training fold) | Distance-based methods need comparable scales |
| Weekly aggregation | {len(cl['features'])} era features (log hash rate, 30-day growth, empty share, transactions per block, fullness, fee share, unattributed share, HHI concentration, log BTC earned per TH/s) | Removes daily noise for era clustering |
| Frontier hardware and break-even price | best available J/TH by date (CPU → S21 XP); break-even USD/kWh = hash price ÷ energy per TH-day | Turns network data into the economics a miner faces |

**Excluded by design (leakage control):** coinbase text, payout address, Blockchair's miner guess (all label sources),
block height and calendar time (they only encode which pools were large *when*), and network difficulty (identical
for every miner in the same period). An automated check confirms none of them reached the model (section 15).

# 6. Feature selection

Feature selection used **training data only** (2019-2023, month-stratified sample of {n(split['train_sample']['rows'])}
blocks) and four complementary methods, from filter to wrapper:

{table(['Step', 'Method', 'Removed', 'Remaining'], [
        ['0', 'Candidate fingerprint features', '–', fs['candidates']],
        ['1', 'Variance filter (min-max scaled variance < 1e-4)', len(fs['removed_low_variance']), fs['candidates'] - len(fs['removed_low_variance'])],
        ['2', f"Mutual information vs. 10 random noise probes (cutoff {f(fs['mi_noise_cutoff'], 5)})", len(fs['removed_mi_below_noise']),
         fs['candidates'] - len(fs['removed_low_variance']) - len(fs['removed_mi_below_noise'])],
        ['3', 'Redundancy: |Spearman ρ| > 0.90, keep higher MI', len(fs['removed_redundant']),
         fs['candidates'] - len(fs['removed_low_variance']) - len(fs['removed_mi_below_noise']) - len(fs['removed_redundant'])],
        ['4', 'Wrapper: drop-one-group ablation (tree, month-grouped CV)', ', '.join(fs['removed_groups_no_gain']) or 'none', fs['n_selected']],
    ], ['r', 'l', 'l', 'r'])}

Findings worth noting:

* **Timing carries no miner signal.** Both timestamp features (offset from the median of the previous 11 blocks and
  interval since the previous block) scored below the noise probes and were removed, consistent with block discovery
  being a random (Poisson) process for every miner.
* **The control feature was caught**: the hour-of-day encodings were removed (one by mutual information, the other by
  the ablation), as designed.
* Most nonce bits are noise; a few low-order bits survive (some mining hardware searches the nonce space in a
  structured way).
* Redundant pair removed: {', '.join(f"{r['a']} vs {r['b']} (ρ = {r['rho']})" for r in fs['removed_redundant']) or 'none'}.

{table(['Feature group', 'Features kept', 'CV macro-F1 without the group', 'Change'],
        [[g, a['features_in_group'], f(a['macro_f1_without'], 4), f"{a['change']:+.4f}"] for g, a in fs['group_ablation']['groups'].items()],
        ['l', 'r', 'r', 'r'])}

Version bits and body composition carry most of the signal. The final model uses **{fs['n_selected']} features**.

{fig('f05_feature_selection', 'Left: mutual information of the top 30 candidates (violet = kept) against the noise-probe cutoff. Right: change in CV macro-F1 when a feature group is removed.')}

# 7. Model learning procedure

## 7.1 Target and data splits

The target is the mining entity of a block: the {len(sel['classes']) - 2} pools that mined at least 2% of training-period
blocks, an **Other pools** class, and a **Solo** class (the six solo-mining services). Unknown blocks are never used
for fitting.

{table(['Split', 'Period', 'Labelled blocks', 'Solo', 'Role'], [
        ['Train', f"{split['train']['first'][:10]} → {split['train']['last'][:10]}", n(split['train']['labelled']), split['train']['solo'],
         'feature selection, hyper-parameters (CV), nested CV'],
        ['Validation', f"{split['validation']['first'][:10]} → {split['validation']['last'][:10]}", n(split['validation']['labelled']), split['validation']['solo'],
         'model-family choice, Solo threshold (out of time)'],
        ['Test (sealed)', f"{split['test']['first'][:10]} → {split['test']['last'][:10]}", n(split['test']['labelled']), split['test']['solo'],
         'scored once, after the choice was frozen'],
        ['New', f"{split['new']['first'][:10]} → {split['new']['last'][:10]}", n(split['new']['labelled']), split['new']['solo'],
         'mined after the data freeze: decision demo'],
    ], ['l', 'l', 'r', 'r', 'l'])}

**Cross-validation adapted to time.** Shuffled k-fold would put blocks from the same day in both training and
validation folds and overstate accuracy. Folds are therefore **grouped by calendar month** (5-fold GroupKFold). The
training sample keeps every Solo block and a month-stratified proportional sample of the rest (representative
sampling, Lecture 3).

## 7.2 Algorithms and hyper-parameters

{table(['Model', 'Grid searched', 'Chosen', 'CV macro-F1 (± SE)', 'Train macro-F1'], [
        ['Decision tree', 'criterion {gini, entropy} × max_depth {3…16, none} × min_samples_leaf {5, 20, 50} × class_weight {none, balanced}',
         ', '.join(f"{k}={v}" for k, v in S['tree']['best_params'].items()), f"{f(S['tree']['cv_macro_f1_mean'])} ± {f(S['tree']['cv_macro_f1_se'])}", f(S['tree']['cv_train_macro_f1'])],
        ['KNN', 'k {5, 15, 41} × weights {uniform, distance} × metric {Manhattan, Euclidean}; standardised',
         ', '.join(f"{k.split('__')[1]}={v}" for k, v in S['knn']['best_params'].items()), f"{f(S['knn']['cv_macro_f1_mean'])} ± {f(S['knn']['cv_macro_f1_se'])}", f(S['knn']['cv_train_macro_f1'])],
        ['Linear SVM', f"C {{0.01, 0.1, 1, 10}}; balanced classes; {n(S['svm_linear']['train_rows'])}-row sample",
         ', '.join(f"{k.split('__')[1]}={v}" for k, v in S['svm_linear']['best_params'].items()), f"{f(S['svm_linear']['cv_macro_f1_mean'])} ± {f(S['svm_linear']['cv_macro_f1_se'])}", f(S['svm_linear']['cv_train_macro_f1'])],
        ['RBF SVM', f"C {{1, 10}} × γ {{scale, 0.03}}; balanced; {n(S['svm_rbf']['train_rows'])}-row sample",
         ', '.join(f"{k.split('__')[1]}={v}" for k, v in S['svm_rbf']['best_params'].items()), f"{f(S['svm_rbf']['cv_macro_f1_mean'])} ± {f(S['svm_rbf']['cv_macro_f1_se'])}", f(S['svm_rbf']['cv_train_macro_f1'])],
    ], ['l', 'l', 'l', 'r', 'r'])}

The SVMs are trained on a bounded sample because kernel SVM cost grows roughly quadratically with rows; all models
are scored on identical validation and test blocks. **Nested cross-validation** (outer 5 × inner 3, month-grouped)
estimates the *whole* tree-tuning procedure without optimistic bias: macro-F1 **{f(nested['mean'])} ± {f(nested['sd'])}**
(SD over outer folds), close to the inner CV score, so the grid search did not overfit its own folds.

{fig('f06_tree_complexity', 'Tree complexity: training macro-F1 keeps rising with depth while held-out CV levels off, the classic overfitting signature.')}

## 7.3 How the tree splits (worked example)

The root of the training tree tests **`{rs['feature']}` ≤ {f(rs['threshold'], 3)}**. Recomputed by hand on
{n(rs['n'])} training blocks: parent Gini {f(rs['gini']['parent'], 4)}; left child ({n(rs['n_left'])} blocks) Gini
{f(rs['gini']['left'], 4)}; right child ({n(rs['n_right'])} blocks) Gini {f(rs['gini']['right'], 4)}; weighted child
impurity (n~L~G~L~ + n~R~G~R~)/n = {f(rs['gini']['weighted_children'], 4)}; **Gini reduction {f(rs['gini']['reduction'], 4)}**
(entropy information gain {f(rs['entropy']['information_gain'], 4)}). Gini and entropy reached CV scores of
{f(ex['complexity']['best_cv_by_criterion'].get('gini'))} and {f(ex['complexity']['best_cv_by_criterion'].get('entropy'))};
the chosen criterion was {S['tree']['best_params']['criterion']}. The fitted tree is exported in full to the dashboard,
where any test block can be traced root-to-leaf.

{fig('f11_tree_top', 'Top two levels of the fitted decision tree (class proportions per node); the full tree is in the dashboard.')}

## 7.4 Model choice (frozen before testing)

Rule declared in advance: highest **validation** macro-F1; the decision tree is preferred if within 0.01 (it is
explainable). Validation macro-F1: tree {f(S['tree']['validation']['macro_f1'])}, KNN {f(S['knn']['validation']['macro_f1'])},
linear SVM {f(S['svm_linear']['validation']['macro_f1'])}, RBF SVM {f(S['svm_rbf']['validation']['macro_f1'])}. The
operational model is the **{FAM[sel['chosen_family']].lower()}**, frozen on {sel['frozen_at']}; the chosen configuration
was refitted on train + validation before the sealed test. The template families used for family-level scoring were
also fixed on training data: {'; '.join(' + '.join(g) for g in multi_fams) or 'no multi-class family'}.

# 8. Performance evaluation

## 8.1 Results on the sealed test period

{table(['Model', 'Macro-F1', 'Balanced acc.', 'Accuracy', 'Top-3 acc.', 'Family acc.', 'Solo AP', 'Solo ROC-AUC'], [
        [FAM[k] + (' **(operational)**' if k == op else ''), f(T[k]['macro_f1']), p(T[k]['balanced_accuracy']), p(T[k]['accuracy']),
         p(T[k].get('top3_accuracy')) if T[k].get('top3_accuracy') else '–', p(T[k].get('family_accuracy')),
         f(T[k].get('solo_average_precision')) if T[k].get('solo_average_precision') is not None else '–',
         f(T[k].get('solo_roc_auc')) if T[k].get('solo_roc_auc') is not None else '–']
        for k in ['tree', 'knn', 'svm_linear', 'svm_rbf', 'decision_stump', 'stratified_random', 'majority']
    ], ['l'] + ['r'] * 7)}

Test period {tm['test_period'][0]} → {tm['test_period'][1]}, {n(tm['test_blocks'])} labelled blocks, {len(sel['classes'])}
classes. A 95% bootstrap interval that resamples whole **days** (blocks on the same day share conditions) gives
macro-F1 **{f(tm['bootstrap']['macro_f1_95ci'][0])} – {f(tm['bootstrap']['macro_f1_95ci'][1])}** for the operational model.
Macro-F1 is averaged over the classes present in the test period; predicting a pool that no longer exists still
counts as an error.

{fig('f07_model_comparison', 'Macro-F1 of every model on CV, validation and the sealed test (same features, same blocks); error bar = day-block bootstrap 95% interval.')}

**Reading the numbers.** The decision tree is clearly the best model: its macro-F1 is
{f(T[op]['macro_f1'] / max(T['stratified_random']['macro_f1'], 1e-9), 1)}× the stratified-random baseline and
{f(T[op]['macro_f1'] / max(T['decision_stump']['macro_f1'], 1e-9), 1)}× a one-split tree. {beat_text}
Exact-pool accuracy is modest ({p(T[op]['accuracy'], 0)} across {len(sel['classes'])} classes, against {p(T['majority']['accuracy'], 0)} for always
predicting the largest pool), but the **true pool is among the tree's top three candidates {p(T[op].get('top3_accuracy'), 0)}** of
the time. In other words, behaviour narrows a block down to a few look-alike pools; it cannot reliably separate pools
that build blocks the same way. Merging the template families fixed on training data raises accuracy only to
{p(T[op]['family_accuracy'], 0)}, because those families were defined from average profiles, while the confusions below are
spread across many large pools.

**Why the tree and not KNN or SVM?** The signal sits in a few *discrete* bit patterns (signal bits set, how many
version bits are rolled) and in thresholds on block composition. Axis-aligned tree splits isolate exactly these
patterns. Distance- and kernel-based models weigh all {fs['n_selected']} standardised features together, so a handful of
informative bits is drowned by many weakly informative ones (the curse of dimensionality discussed in Lecture 7). We
tested remedies on validation data — only the top-k mutual-information features, and mutual-information-weighted
distances — and neither lifted KNN or the RBF SVM above about 0.11 macro-F1. The model comparison therefore teaches
something about the data: its geometry favours rule-like models.

{fig('f08_confusion', 'Test-period confusion matrix, row-normalised (diagonal = recall).')}

{table(['Class', 'Precision', 'Recall', 'F1', 'Blocks'], [[k, f(v['precision'], 2), f(v['recall'], 2), f(v['f1-score'], 2), n(v['support'])] for k, v in per_class.items()], ['l', 'r', 'r', 'r', 'r'])}

The validation-to-test difference and the monthly scores (dashboard, Block Radar) show **drift**: pools change firmware
and policies, and new pools appear. The pools that did not exist (or were small) during training are mapped by the
frozen model as follows, a direct test of "whose template does a newcomer use?":

{table(['Newcomer pool', 'Blocks (val+test)', 'Most often predicted as', 'Share'], [[r['miner'], n(r['blocks']), r['top_prediction'], p(r['top_share'], 0)] for r in newcomers], ['l', 'r', 'l', 'r'])}

## 8.2 The Solo class

Solo blocks are a needle in a haystack (base rate {p(T['tree']['solo_base_rate'], 3)} of test blocks). One-vs-rest
**average precision** is the honest metric here (ROC-AUC looks good for any rare class). The threshold frozen on
validation ({sel['solo_threshold']['rule']}) flagged {test_solo['flagged']} test blocks, of which {test_solo['true_positives']}
were solo (precision {p(test_solo['precision'], 0)}, recall {p(test_solo['recall'], 0)} of {test_solo['solo_in_test']}). With so few
solo blocks per year these figures carry wide uncertainty; the finding is that **modern solo blocks are mostly built
with the same open-source templates as pool blocks** (section 10.3), so they are hard to fingerprint.

{fig('f09_solo_roc_pr', 'Solo vs rest on the test period: ROC (left) and precision-recall (right). SVM scores are decision values, not probabilities.')}

## 8.3 What the models rely on

Permutation importance on the test period (drop in macro-F1 when one feature is shuffled):
{', '.join(f"`{r['feature']}` ({f(r['mean'], 4)})" for r in imp)}. Version-rolling bits and how full a block is relative
to that day dominate; fee features matter less because, since 2023, most pools fill blocks with the same fee-maximising
template (section 10).
''')
    if ex.get("knn_example"):
        k = ex["knn_example"]
        md.append(f'''**KNN, opened up.** For the latest solo test block (#{n(k['height'])}), the {k['k']} nearest training blocks
({k['metric']} distance, {k['weights']} weights, standardised features) voted
{', '.join(f"{a}: {b}" for a, b in sorted(k['votes'].items(), key=lambda x: -x[1])[:4])}, so KNN predicted **{k['prediction']}**,
a concrete illustration of why solo blocks are hard: their nearest neighbours are ordinary pool blocks.

{fig('f10_permutation_importance', 'Permutation importance of the operational model on the test period.')}
''')
    md.append(f'''# 9. Clustering

## 9.1 Rediscovering the mining eras

One row per week ({n(cl['weeks'])} weeks, 2009 → 2026), {len(cl['features'])} standardised features describing *how* blocks
were produced. K was chosen by the silhouette maximum for K ≥ 3 (K = 2 trivially splits "early" from "late"); 25
initialisations; a hand-checked first iteration confirms the assignment and update steps (SSE
{f(cl['kmeans_trace']['sse_initial_assignment'], 1)} → {f(cl['kmeans_trace']['sse_after_update'], 1)}, centroids identical to
scikit-learn within {cl['kmeans_trace']['max_abs_diff_vs_sklearn_centroids']:.1e}). Stability across 10 seeds: mean ARI
{f(cl['seed_stability_ari_mean'], 2)}.

{fig('f12_kmeans_dbscan', 'Left: K-means SSE (elbow) and silhouette by K. Right: DBSCAN k-distance curve with the chosen eps.')}

{table(['Cluster', 'Weeks', 'From', 'To', 'Dominant documented era'], [[f"C{r['cluster']}", r['weeks'], r['first_week'], r['last_week'], r['dominant_hardware_era']] for r in eras_prof], ['l', 'r', 'l', 'l', 'l'])}

**Without being told anything about hardware, the clusters line up with the documented eras**: K-means ARI
**{f(hard_era_ari, 2)}**, Ward linkage ARI **{f(ward['ari_vs_hardware_eras'], 2)}**. K-means places the start of the
industrial regime in {next((r['first_week'][:7] for r in eras_prof if r['dominant_hardware_era'] == 'Industrial ASIC'), 'n/a')}, when pools
had taken over and blocks had become full, rather than at the first ASIC in January 2013; Ward linkage's boundaries fall on
{' and '.join(ward_bounds)}, i.e. two weeks after the documented start of the FPGA era (1 June 2011) and two days after
the July 2016 halving that coincided with the industrial-ASIC (Antminer S9) era. Both are useful refinements
of a timeline that textbooks usually date by hardware releases alone.

{table(['Linkage', 'Cophenetic correlation', 'Cluster sizes (cut at K)', 'ARI vs K-means', 'ARI vs eras'],
        [[k, f(v['cophenetic_correlation'], 3), ', '.join(map(str, v['cluster_sizes'])), f(v['ari_vs_kmeans'], 2), f(v['ari_vs_hardware_eras'], 2)] for k, v in cl['hierarchical'].items()],
        ['l', 'r', 'l', 'r', 'r'])}

Single linkage chains almost everything into one cluster (its known weakness); average linkage preserves distances best
(highest cophenetic correlation) but also produces one dominant cluster; **Ward**, which minimises the increase in SSE,
gives compact eras closest to history. **DBSCAN** (MinPts {cl['dbscan_selected']['min_samples']}, eps
{f(cl['dbscan_selected']['eps'], 2)} from the {cl['dbscan_selected']['eps_quantile']} quantile of the k-distance curve) finds
{cl['dbscan_selected']['clusters']} dense regions and labels {p(cl['dbscan_selected']['noise_share'], 1)} of weeks as noise: the
transition weeks where hash rate and block composition were changing fastest. Density-based clustering is the wrong
tool for separating eras that blend into each other, and that is itself a finding.

{fig('f13_eras_timeline', 'Weekly cluster assignments compared with the documented hardware eras (black = DBSCAN noise).')}

## 9.2 Pool families

For the {len(pf['pools'])} pools with at least {c['clustering']['min_pool_blocks']} blocks in {pf['window'][0]} → {pf['window'][1]},
a profile of mean fingerprints (version-rolling habits, signal bits, empty-block rate, day-relative fee and size policy,
timestamp offset) was clustered with average linkage (cophenetic correlation {f(pf['linkages']['average']['cophenetic_correlation'], 3)}).
Cutting below the 35th percentile of merge heights gives these multi-pool families:
{'; '.join('**' + ' + '.join(g) + '**' for g in pf_multi)}.

{fig('f14_pool_dendrogram', 'Average-linkage dendrogram of pool fingerprint profiles (2024-2026); the dashed line is the family cut.')}

The families largely agree with the classifier: {agree_text} This matters for decentralisation: block production
that looks spread over many pool names may come from fewer distinct block-building set-ups. Similar fingerprints can
also come from shared mining firmware or pool software, so the data **suggest**, but do not prove, common control.

## 9.3 Anomalous blocks

DBSCAN on {n(cl['anomalies']['rows'])} recent blocks marks {p(cl['anomalies']['noise_share'], 1)} as noise. Those blocks are
{f(cl['anomalies']['noise_empty_share'] / max(cl['anomalies']['all_empty_share'], 1e-9), 0)}× more often empty than average and
have unusual timestamps, which is genuine but rare miner behaviour, not data errors.

# 10. Association rules

## 10.1 Transactions, items and Apriori

Each modern block ({ru['discovery_window'][0]} → {ru['discovery_window'][1]}, **{n(ru['transactions'])} transactions**)
is a basket of {len(ru['items'])} items: empty, full (≥ 98%) or light; how many version bits are rolled (none, 1-4, 5-8,
9-12, 13-16); signal bits set; timestamp far ahead of the median; fast or slow follow-up; fees and transaction count
below or above the day's median; witness-heavy content; consolidating or fan-out shape; and the miner (pools with at
least 1% of blocks, "small pools", Solo, Unknown). Bin edges were fitted on the discovery window only.

Apriori was implemented from scratch: join frequent (k−1)-itemsets sharing k−2 items, prune every candidate with an
infrequent subset (support is anti-monotone), then count the survivors.

{table(['k', 'Joined candidates', 'Pruned by subset', 'Counted', 'Frequent'], [[t['k'], n(t['candidates']), n(t['pruned_by_subset']), n(t['counted']), n(t['frequent'])] for t in ru['apriori_trace']], ['r'] * 5)}

Minimum support {p(ru['min_support'], 0)} ({n(ru['min_count'])} blocks) gave {n(ru['frequent_itemsets'])} frequent itemsets. An
exhaustive brute-force count of every itemset up to size {ru['brute_force_check']['max_len']} over {ru['brute_force_check']['items_checked']}
items found the same {ru['brute_force_check']['frequent_by_brute_force']} frequent itemsets with identical counts
(**check passed**).

## 10.2 Rules "block properties → miner"

With minimum confidence {p(ru['min_confidence'], 0)} (single pools have base rates of 1-30%, so this already implies
lift > 1), {ru['n_rules']} rules were found, and each was re-measured on the later window {ru['confirm_window'][0]} → {ru['confirm_window'][1]}.
''')
    if top_rule:
        md.append(table(['Rule', 'Support', 'Confidence', 'Lift', 'Later confidence', 'Confirmed'],
                        [[' ∧ '.join(r['antecedent']) + ' → ' + r['consequent'].replace('miner=', ''), p(r['support'], 1), p(r['confidence'], 0),
                          f(r['lift'], 2), p(r['confirm_confidence'], 0), 'yes' if r['confirmed'] else 'no'] for r in rules_sorted[:8]],
                        ['l', 'r', 'r', 'r', 'r', 'l']))
    md.append(f'''

Confidence is a historical conditional frequency and lift compares it with the miner's base rate; neither implies
causation. Most high-confidence rules point to the largest pool simply because of its base rate (low lift); the
informative rules are the high-lift ones.

{fig('f15_rules', 'Rules by support and confidence, coloured by lift.')}

## 10.3 Pool signatures and the solo contrast

Small pools can never pass a global support threshold, so we also mined frequent itemsets **inside** each pool's blocks
and compared their support with all other blocks (contrast mining):

{table(['Pool', 'Signature itemset', 'In pool', 'Elsewhere', 'Ratio'], [[s['pool'], ' ∧ '.join(s['top'][0]['itemset']), p(s['top'][0]['support_inside'], 0), p(s['top'][0]['support_outside'], 1), f(s['top'][0]['ratio'], 1) + '×'] for s in sigs[:9]], ['l', 'l', 'r', 'r', 'r'])}

Pools with a strong signature (signal bits, distinctive version rolling) are exactly the ones the classifier recognises
best. The large pools ({', '.join(s['pool'] for s in ru['pool_signatures'] if not s['top'])}) have **no distinctive itemset at
all**: they build blocks the way everybody else does. For the {ru['solo_contrast']['solo_blocks']} solo blocks since 2019, the most
over-represented itemset ({' ∧ '.join(ru['solo_contrast']['itemsets'][0]['itemset'])}) is only
{f(ru['solo_contrast']['itemsets'][0]['ratio'], 2)}× more common than among pool blocks, confirming that modern solo blocks are
nearly indistinguishable from pool blocks.

# 11. Decision making on new examples

## 11.1 Unattributed blocks and real concentration

In the last 12 months before the freeze, {n(ua['unknown_blocks'])} of {n(ua['blocks'])} blocks ({p(ua['unknown_share'], 2)}) carried
no attribution. The frozen model attributes them as {', '.join(f"{k}: {v}" for k, v in list(ua['predicted_classes'].items())[:4])}.
By pool *name*, **{ua['nakamoto_by_pool_name']} entities** mined more than half of the blocks (the Nakamoto coefficient). As
an **upper-bound scenario**, if every fingerprint family of section 9.2 were a single block builder, the number would
be **{ua['nakamoto_after_family_merge']}** (largest family: {list(ua['top_families'])[0]}). Similarity is not proof of shared
ownership ({ua['caution']}), so the true figure lies between these two bounds; the point is that pool names alone
cannot establish how decentralised block building is.

{fig('f18_concentration', 'Concentration of block production by labelled pool name.')}

## 11.2 Blocks mined after the data freeze

The {n(nb['labelled'])} labelled blocks mined between {nb['period'][0]} and {nb['period'][1]} were never seen by any stage.
The frozen model predicted their miner first; when the labels were revealed, **{p(nb['accuracy'], 1)}** were correct,
below the test-period accuracy ({p(T[op]['accuracy'], 0)}): one more sign of drift, as pools such as SpiderPool keep growing
after the training period. The command `uv run hashatlas predict --heights …` repeats this for any block.

## 11.3 The miner advisor: pool, solo lottery, or switch off?

At the freeze (30-day means to {st['date']}): network hash rate {f(st['hashrate_ths_30d'] / 1e6, 0)} EH/s, BTC price
{f(st['price_usd_30d'], 0)} USD, **hash price {f(st['hashprice_usd_th_day_30d'], 4)} USD per TH/s per day**. For a device with
hash rate h (TH/s) and power W, pool income = hash price × h × (1 − 2% fee), electricity = W/1000 × 24 × price per kWh,
and solo blocks arrive as a Poisson process with rate (h / network) × 144 per day.

{table(['Device', 'HK pool income / day', 'HK electricity / day', 'Profit / day', 'Break-even USD/kWh', 'Solo odds / year'],
        [[d, f(r['pool_income_usd_day'], 2), f(r['electricity_usd_day'], 2), f(r['profit_usd_day'], 2), f(r['breakeven_usd_kwh'], 3), odds(r['solo_p_block_per_year'])] for d, r in hk.iterrows()],
        ['l', 'r', 'r', 'r', 'r', 'r'])}

Hong Kong business electricity costs {f(float(hk['price_usd_kwh'].iloc[0]), 3)} USD/kWh; an Antminer S21 needs
**{f(s21_be, 3)} USD/kWh or less**. Among the {len(s21)} economies with business tariffs in our snapshot, the S21 covers its
electricity in {len(viable)}: {', '.join(viable) if viable else 'none'}.

{fig('f16_advisor', 'Business electricity price by economy against the Antminer S21 break-even price (teal = Asia).')}

**Decision.** In Hong Kong, at retail tariffs, mining for profit does not pay at the freeze-date hash price. A small
home miner (1.2 TH/s) is a lottery ticket: odds of about **{odds(float(bitaxe['solo_p_block_per_year']))} per year**, an
expected wait of {f(float(bitaxe['solo_expected_years_to_block']), 0)} years, and it costs electricity every day it runs. The
advisor recommends pool mining only where electricity is below the device's break-even price, and labels solo mining
honestly as a lottery.

{fig('f03_solo_odds', 'Chance that a 1.2 TH/s miner finds at least one block in a year (left) and blocks actually won by solo services (right).')}

# 12. Future Lab: the 2028 halving (scenarios, not forecasts)

**How much future, and how.** We include the future only where it can be grounded: (1) the protocol schedule is
certain: the subsidy halves at height {n(fu['halving']['height'])}; (2) hash-rate growth is simulated by block-bootstrapping
30-day stretches of historical daily growth ({n(fu['n_paths'])} paths); (3) BTC price and fee share are **user-chosen
scenarios**, never forecasts; (4) the method is **backtested** from four historical dates.

* Projected halving date: **{fu['halving']['date_p50']}** (80% of paths {fu['halving']['date_p10']} → {fu['halving']['date_p90']}).
* Backtest ({bt['cases']} origin/horizon cases): the 80% band contained the realised hash rate in **{p(bt['coverage_80pct_band'], 0)}** of
  cases. Two resampling windows were compared by the declared rule "lower backtest error wins": mean |error| of the
  median path {f(btc['last-3-years']['mae_pct']['median'], 0)}% (last 3 years) vs {f(btc['since-2017']['mae_pct']['median'], 0)}% (since
  2017), so the last-3-years window drives the main scenario. **Honest limitation:** a naive "no growth" projection had
  a lower error ({f(bt['mae_pct']['persistence'], 0)}%) over 2019-2025, so the median path should be read as one point in a wide
  range, not as a prediction.

{fig('f17_future', 'Left: hash-rate scenarios to 2029 with the projected 2028 halving. Right: backtest error of the same method from past origins.')}

{table(['Device', 'Checkpoint', 'Date', 'Break-even USD/kWh (p10-p90)', 'Solo odds / year'],
        [[r['device'], r['checkpoint'], r['date'], f"{f(r['breakeven_usd_kwh_p50'], 3)} ({f(r['breakeven_usd_kwh_p10'], 3)}-{f(r['breakeven_usd_kwh_p90'], 3)})", odds(r['solo_p_year_p50'])] for _, r in devs.iterrows()],
        ['l', 'l', 'l', 'r', 'r'])}

At today's price and a 5% fee share, the halving cuts the break-even electricity price of every device by more than half
(Antminer S21: {f(devs[(devs['device'] == 'Antminer S21')]['breakeven_usd_kwh_p50'].iloc[0], 3)} → {f(devs[(devs['device'] == 'Antminer S21')]['breakeven_usd_kwh_p50'].iloc[1], 3)} USD/kWh).
Break-even scales linearly with price, so even a doubled BTC price would only restore it to about
{f(2 * devs[(devs['device'] == 'Antminer S21')]['breakeven_usd_kwh_p50'].iloc[1], 3)} USD/kWh. After 2028, mining is viable only at very cheap,
mostly industrial or stranded power, consistent with how mining migrated after earlier halvings. The dashboard's
Future Lab lets the reader test any price and fee scenario.

# 13. Interpretation and critical evaluation

**Q1: Can fingerprints identify the miner?** Partly. The decision tree clearly beats every baseline and puts the
true pool in its top three {p(T[op].get('top3_accuracy'), 0)} of the time; pools with distinctive version-bit habits or
signalling are recognised well. Most large pools, however, build blocks the same way, so exact-pool accuracy is capped
at about {p(T[op]['accuracy'], 0)}. The cap is informative rather than a failure: contrast mining finds no distinctive
signature for the largest pools, and newcomer pools are mapped onto existing templates. Modern solo blocks are largely
indistinguishable from pool blocks.

**Q2: Eras and families.** The unsupervised eras match documented history (ARI {f(ward['ari_vs_hardware_eras'], 2)} with
Ward), and the pool families explain the classifier's confusions.

**Q3: Should a small miner mine?** In Hong Kong, for profit, no; for fun, it is a lottery ticket with known odds. After
the 2028 halving the economics tighten further for everyone.

**Limitations.** (1) Labels are self-declared and may be copied or shared; mempool.space's attribution is the
reference for 2019+. (2) Fingerprints drift; the model is dated to its training period and must be retrained. (3)
"Other pools" is a heterogeneous class. (4) Solo results rest on a few dozen blocks. (5) Electricity prices are retail
snapshots; industrial miners pay less, and prices change. (6) The Future Lab is conditional on its assumptions and its
backtest error is large. (7) Family similarity is not proof of common ownership.

# 14. Ethics and practical implications

* **Privacy.** Blocks are public and pseudonymous; no personal data is used. Fingerprinting miners is dual-use: it can
  support decentralisation research but could also help de-anonymise solo miners. We publish aggregate findings and
  model behaviour only, and no address-level analysis.
* **No financial advice.** The advisor shows odds, costs and break-even prices; the dashboard and report state that
  outputs are historical analysis and scenarios.
* **Environment.** Break-even analysis shows why mining concentrates where power is cheap; the energy-efficiency
  frontier (J/TH) fell about a millionfold from CPUs to ASICs, but total consumption is outside our scope.
* **Implications.** Pool names overstate decentralisation; regulators and analysts should look at *template* diversity.
  For individuals in high-tariff economies like Hong Kong, home mining is entertainment, not income.

# 15. AI-agent use and verification

The team used AI coding agents (see `agent_trajectories/`) following the course's workflow: humans defined the
problem and constraints; the agent proposed plans; humans reviewed them; the agent implemented; humans verified
outputs; then revised. Examples where human review changed the agent's output:

* An early class design scored macro-F1 over *all* classes, including pools that had stopped mining; reviewers changed
  it to classes present in the evaluation period (predicting a vanished pool is still an error).
* The first association-rule run produced **zero rules** because a 50% confidence threshold ignored base rates of 1-30%;
  the threshold was set from base rates and per-pool contrast mining was added.
* The first Future Lab method overshot hash-rate growth in its own backtest; the resampling window is now chosen by
  backtest error, and the remaining weakness is reported.
* When the free data quota ran out mid-download, the agent's retry loop kept failing silently (HTTP 402); the team
  switched the 2019+ era to mempool.space and added a completeness check (no missing heights).

**Independent verification** (`uv run hashatlas verify`) recomputes key results through separate code paths:
**{ver['passed']} of {ver['total']} checks passed**.

{table(['Check', 'Result'], [[ch['check'], 'pass' if ch['passed'] else '**FAIL**'] for ch in ver['checks']], ['l', 'l'])}

Unit tests (`uv run pytest`) cover bit decomposition, leakage exclusions, day-relative features, Apriori against brute
force, impurity measures, miner economics and the bootstrap; the dashboard has its own tests and a browser check.

# 16. Conclusion

A small Bitcoin miner can still win, but only as a lottery: the odds have fallen from near-certainty in 2009 to about
{odds(float(bitaxe['solo_p_block_per_year']))} per year for a 1.2 TH/s device today, and they will roughly halve again in value
after April 2028. Data mining on 975,494 blocks shows *why* the industry looks the way it does: the eras are visible in
the data, pool names hide fewer distinct block builders, and behavioural fingerprints narrow a block down to a few look-alike
pools. Future work: per-transaction template features, Stratum V2 adoption (which lets miners build their
own templates and may change fingerprints), and live retraining.

# 17. Team members and contributions

Each member was primarily responsible for specific components of the project while maintaining continuous
collaboration and consultation throughout development. The workload was distributed as evenly as possible across the
group, with the captain undertaking a slightly larger share of the core technical implementation, system integration,
deployment, and final production tasks.

Responsibilities were divided by stage of the data-mining lifecycle rather than by deliverable, so that the same
person owns a stage end to end: its code module, its page on the dashboard, its sections of this report, its slides
in the presentation and its record of AI-agent use. This kept every part of the project traceable to one accountable
owner, while the hand-over points between stages (the cleaned block table, the frozen feature list, the frozen model,
the cluster and rule outputs, and the dashboard data export) were agreed jointly and reviewed by the next owner in the
pipeline before work continued.

''')
    md.append(table(["Member", "Role (report sections)", "Contributions and code"],
                    [[m["name"] + (f" ({m['student_id']})" if m.get("student_id") else ""),
                      f"{m['role']} (§{m['report_sections']})",
                      "; ".join(m["contributions"]) + f". Code: `{m['code']}`"] for m in members], ["l", "l", "l"]))
    md.append(f'''

''')
    md.append(table(["Member", "Dashboard page", "Slides presented"],
                    [[m["name"] + (" (captain)" if m.get("captain") else ""), m.get("dashboard", ""), m.get("slides", "")] for m in members],
                    ["l", "l", "l"]))
    md.append(f'''

Collaboration did not stop at these boundaries. Problem framing, the choice of questions and the evaluation design
were decided by the whole group; each owner's agent-generated code and results were checked by at least one other
member before they were merged; and the conclusions, limitations and presentation were rehearsed and revised together.
Each member's individual work is also visible in the Git history of the repository and in their own exported
AI-agent trajectory (Section 15).

# 18. Reproducibility and references

**Run.** `uv sync`, then `uv run hashatlas run-all` (Python 3.12, versions locked in `uv.lock`); dashboard:
`cd web && bun install && bun run build`. Repository: {team['github_url']}. Live dashboard: <{team['live_site']}>.

**Data sources.** Blockchair daily block dumps (blockchair.com/dumps); mempool.space REST API and the open
`mempool/mining-pools` definitions; blockchain.com chart API; GlobalPetrolPrices electricity prices (snapshot
retrieved {src['retrieved_utc'][:10]}). Hardware specifications are manufacturer figures (approximate).

**Methods.** Course lectures 2-10 (CDS3004, Lingnan University); scikit-learn user guide (trees, KNN, SVM, clustering,
model selection); Nakamoto, S. (2008) *Bitcoin: A Peer-to-Peer Electronic Cash System*; BIP 9 and BIP 320 (version-bit
signalling and general-purpose version bits).
''')
    import re
    out = "\n".join(md)
    # LaTeX numbers subsections itself: drop the manual "2.1 " prefixes from level-2/3 headings
    return re.sub(r"^(#{2,3}) \d+(?:\.\d+)+ ", r"\1 ", out, flags=re.M)


def readme_results() -> None:
    """Refresh the key-results block of README.md from the artifacts (between the KEY RESULTS markers)."""
    tm = read_json(ARTIFACTS / "test_metrics.json")
    cl = read_json(ARTIFACTS / "clusters.json")
    ru = read_json(ARTIFACTS / "rules.json")
    dec = read_json(ARTIFACTS / "decisions.json")
    fu = read_json(ARTIFACTS / "future.json")
    ver = read_json(ARTIFACTS / "verification.json")
    q = read_json(ARTIFACTS / "quality_report.json")
    op = tm["operational_family"]
    T = tm["families"]
    adv = pd.DataFrame(dec["advisor"])
    bit = adv[adv["device"].str.startswith("Bitaxe")].iloc[0]
    hk = adv[(adv["device"] == "Antminer S21") & (adv["country"] == "Hong Kong") & (adv["tariff"] == "business")].iloc[0]
    rows = [
        ["Data", f"{n(q['rows_loaded'])} blocks (heights 0-{n(q['height_range'][1])}), 0 missing / 0 duplicate heights; label precision {p(q['label_audit']['precision_when_tag_found'], 2)} vs mempool.space"],
        ["Fingerprint classifier (sealed test 2025-04 → 2026-10)", f"{FAM[op]}: macro-F1 {f(T[op]['macro_f1'])} (95% CI {f(tm['bootstrap']['macro_f1_95ci'][0])}-{f(tm['bootstrap']['macro_f1_95ci'][1])}), accuracy {p(T[op]['accuracy'], 0)}, top-3 {p(T[op].get('top3_accuracy'), 0)}, template-family accuracy {p(T[op]['family_accuracy'], 0)}; baselines ≤ {f(max(T[b]['macro_f1'] for b in ('majority', 'stratified_random', 'decision_stump')))}"],
        ["Blocks mined after the freeze", f"{p(dec['new_blocks']['accuracy'], 1)} correct on {n(dec['new_blocks']['labelled'])} unseen blocks"],
        ["Eras (unsupervised)", f"K-means K={cl['k_selected']} ARI {f(cl['ari_vs_hardware_eras']['kmeans'], 2)}; Ward ARI {f(cl['hierarchical']['ward']['ari_vs_hardware_eras'], 2)} vs documented hardware eras"],
        ["Association rules", f"{n(ru['frequent_itemsets'])} frequent itemsets from {n(ru['transactions'])} blocks; {ru['n_rules']} rules; brute-force check {'passed' if ru['brute_force_check']['passed'] else 'FAILED'}"],
        ["Hong Kong miner advice", f"S21 {'profit' if hk['profit_usd_day'] >= 0 else 'loss'} {f(abs(hk['profit_usd_day']), 2)} USD/day at {f(hk['price_usd_kwh'], 3)} USD/kWh (break-even {f(hk['breakeven_usd_kwh'], 3)}); 1.2 TH/s home miner: {odds(bit['solo_p_block_per_year'])} per year"],
        ["Future Lab", f"2028 halving ~{fu['halving']['date_p50']}; backtest 80% band coverage {p(fu['backtest']['summary']['coverage_80pct_band'], 0)}"],
        ["Verification", f"{ver['passed']}/{ver['total']} independent checks passed"],
    ]
    block = "## Key results\n\n" + table(["", "Result"], rows, ["l", "l"]) + "\n"
    rp = ROOT / "README.md"
    txt = rp.read_text(encoding="utf-8")
    a, b = "<!-- KEY RESULTS START -->", "<!-- KEY RESULTS END -->"
    txt = txt[: txt.index(a) + len(a)] + "\n" + block + txt[txt.index(b):]
    rp.write_text(txt, encoding="utf-8")


def run() -> None:
    readme_results()
    md = build_markdown()
    (REPORTS / "technical_report.md").write_text(md, encoding="utf-8")
    print("wrote reports/technical_report.md", len(md.split()), "words")
    r = subprocess.run(["sh", str(REPORTS / "latex" / "build.sh")], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr[-2000:])
    if r.returncode != 0:
        raise SystemExit("PDF build failed")
