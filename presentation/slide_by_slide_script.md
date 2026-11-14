# HashAtlas presentation script

About 16-minute group presentation (16 min 3 s), five presenters, including a 2-minute live demo. Timing = spoken words at 130 wpm + 8 s per slide for pointing and hand-overs. Generated from `presentation/build/build_deck.js` together with the slides (the same text is in the speaker notes); numbers come from the pipeline outputs.

## Slide 1 · Can a small Bitcoin miner still win?

**Member 1** · 38 s (ends at 0:38)

Good morning. Imagine you buy a small mining device the size of a paperback, plug it in at home in Hong Kong, and hope to win a whole Bitcoin block — about 3.125 bitcoin plus fees. Is that a dream, a lottery, or a business? We are Team HashAtlas, and we mined the complete history of Bitcoin — 975,494 blocks — to find out.

## Slide 2 · The lottery that still pays out

**Member 1** · 51 s (ends at 1:29)

In 2009 a laptop won blocks every day. Today a 1.2 terahash home miner — the most popular hobby device — has odds of about 1 in 16,362 per year. And yet solo miners still win: 22 blocks in 2025 and 21 so far in 2026 went to solo-mining services. So we asked three data-mining questions: can we tell who mined a block from its behaviour alone; do the data rediscover the history of mining; and what should a miner in Hong Kong or Asia actually do — today and after the 2028 halving?

## Slide 3 · Problem, constraints and the alternatives we rejected

**Member 1** · 60 s (ends at 2:29)

Our users are a would-be miner in Asia, and analysts who ask how decentralised mining really is. Five constraints shaped the design. First, labels are self-declared: the miner's name comes from text they write in the block, so that text is the label and must never be an input. Second, no look-ahead: pools appear and disappear, so we train on the past and test on the most recent period. Third, solo blocks are extremely rare. Fourth, free data sources are rate-limited. Fifth, we give odds and costs, not investment advice. We rejected price prediction, simple tag lookup, transaction-level tracing and black-box deep learning — the last two for scale, privacy and interpretability.

## Slide 4 · 975,494 blocks, zero gaps, audited labels

**Member 1** · 56 s (ends at 3:25)

We collected every block ever mined: the 2009-to-2018 history from Blockchair's daily dumps, and — after their free quota ran out mid-download — everything from 2019 directly from mempool.space, one mining pool at a time, about 4,364 API calls. The final table has no missing and no duplicate heights. Labels need care: we re-applied our own tag-matching labeller to 424,464 blocks that mempool.space had labelled independently. When our labeller finds a tag it is right 99.95% of the time. The chart shows the story in the labels: unattributed miners in the early years, then pools taking over by 2014. Over to Member 2 for features.

## Slide 5 · Fingerprints from behaviour, never from the name

**Member 2** · 61 s (ends at 4:26)

A block header contains a 32-bit version field and a 32-bit nonce. They are stored as integers, but they are nominal bit fields — so we decomposed them into bits. Modern ASICs roll the general-purpose version bits 13 to 28, and pools differ in how many bits they roll. From the block body we built ratios like fullness and witness share, and day-relative features: each block's fee level or size minus that day's median, which removes market conditions and leaves the miner's policy. We deliberately added the hour of day as a control feature that should be useless. And we excluded everything that leaks the label: coinbase text, payout address, height and calendar time.

## Slide 6 · Feature selection: 77 → 51

**Member 2** · 48 s (ends at 5:14)

Selection used training data only, from filter to wrapper. Mutual information was compared with ten random noise probes: anything no better than noise was dropped — 19 features, including both timestamp features. That is a finding: block discovery is a random process for every miner, so timing carries no fingerprint. Then we removed redundant pairs with Spearman correlation, and finally ran a group ablation: removing the version bits or the body-composition group clearly hurts the cross-validated score, while the hour-of-day control does nothing and was removed.

## Slide 7 · Three models, one honest validation design

**Member 2** · 47 s (ends at 6:01)

Shuffled cross-validation would put blocks from the same day on both sides and overstate accuracy, so folds are grouped by calendar month. We tuned a decision tree, KNN and both linear and RBF SVMs on the 2019-to-2023 training period. Nested cross-validation estimates the whole tuning procedure for the tree at 0.378 macro-F1 — no optimism from tuning. The model choice and the solo threshold were frozen on the out-of-time validation period before the sealed test was opened. Member 3 will now show the results.

## Slide 8 · The tree wins — and hits an informative ceiling

**Member 3** · 59 s (ends at 7:00)

On the sealed test period the decision tree is clearly best: macro-F1 0.244, bootstrap interval 0.24 to 0.25, about 3.0 times the random baseline. KNN and the SVMs struggle: the signal sits in a few discrete bit patterns that tree splits isolate, while distances and kernels dilute them across fifty features — we tried feature subsets and weighting, without success. Now the three accuracies: the exact pool is right 42% of the time, against 18% for always guessing the largest pool; and the true pool is among the tree's top three 69% of the time. Behaviour narrows a block to a few look-alike pools — because many pools build identical blocks.

## Slide 9 · Who looks like whom?

**Member 3** · 62 s (ends at 8:02)

The confusion matrix shows where the errors go. Pools with a distinctive habit — for example signalling bits, or an unusual number of rolled version bits — sit on the diagonal. The largest pools blur into each other, because since 2023 almost everyone fills blocks with the same fee-maximising template. A strong test of the idea: pools that did not exist in training. SpiderPool is predicted as Foundry USA 29% of the time; MARA Pool is predicted as Other pools 45% of the time; SECPOOL is predicted as AntPool 67% of the time. Modern solo blocks look like pool blocks too: the solo class reaches an average precision of 0.01 against a base rate of 0.04%.

## Slide 10 · The data rediscover mining history on their own

**Member 3** · 65 s (ends at 9:07)

Next, clustering. One row per week, nine features describing how blocks were produced — never the dates of the hardware eras. K-means with K chosen by silhouette, four hierarchical linkages and DBSCAN all ran on the same rows. Only afterwards did we compare with documented history: Ward linkage reaches an adjusted Rand index of 0.89 and K-means 0.71. Three eras emerge: the hobbyist CPU and GPU years, the FPGA-to-early-ASIC transition, and the industrial era. Ward's first boundary falls two weeks after the documented start of the FPGA era, and its second two days after the 2016 halving — the start of the Antminer S9 years. DBSCAN marks the fast transition weeks as noise: density-based clustering cannot separate eras that blend into each other.

## Slide 11 · Pool families and block signatures

**Member 3** · 61 s (ends at 10:08)

Clustering the pools themselves by their average fingerprint gives families: AntPool plus Braiins Pool plus Foundry USA plus Luxor; Binance Pool plus CloverPool plus Poolin; SECPOOL plus ULTIMUSPOOL. The classifier agrees: newcomers like SECPOOL and Luxor are mostly read as AntPool, the pool their fingerprints sit closest to. Association rules tell the same story from another angle. Our from-scratch Apriori, checked against brute force, found rules such as fullness=full(>=98%) and version=signal bits set implies SBI Crypto with lift 43. Contrast mining inside each pool gives signatures; the biggest pools have none — they build blocks like everybody else. Similar fingerprints suggest shared templates or software; they do not prove common ownership. Over to Member 4.

## Slide 12 · Should you mine in Hong Kong?

**Member 4** · 48 s (ends at 10:56)

Now the decision. At the freeze, one terahash per second earned about 0.038 US dollars a day. An Antminer S21 therefore covers its electricity only below 0.089 dollars per kilowatt-hour. Hong Kong business power costs 0.175, so an S21 here loses 7.26 dollars a day. Across Asia, only the economies in green on the chart are below break-even at retail tariffs. For a 1.2 terahash home device the advisor says: this is a lottery ticket — odds of 1 in 16,362 per year — not an income.

## Slide 13 · Live demo: the HashAtlas dashboard

**Member 4** · 120 s (ends at 12:56)

Live demo, about two minutes. One: Mission Control — the hash-rate history with eras and halvings. Two: Block Radar — reveal the labels of blocks mined after our freeze and click a confusion cell. Three: Fingerprint Lab — load a real solo block, flip the version-rolling feature and watch the tree re-route it. Four: Miner Advisor — switch from Hong Kong to Kazakhstan and watch the verdict change. If the network fails, the screenshots on this slide are the fallback.

## Slide 14 · Future Lab: the 2028 halving, with an honest backtest

**Member 4** · 57 s (ends at 13:53)

How much future did we include? Only what can be grounded. The protocol halves the subsidy at height one million fifty thousand — our 4,000 simulated paths put that around 2028-04-07. Hash-rate growth is resampled from history; price and fees are scenarios the user chooses, not forecasts. And we backtested the method from past dates: the 80 percent band covered 75% of cases, but a naive no-growth guess had a smaller median error — so read the fan as a range. At today's price, the S21's break-even power price falls from 0.082 in early 2027 to 0.029 a month after the halving. Member 5 will close.

## Slide 15 · Limits, ethics, and how we checked the agents

**Member 5** · 60 s (ends at 14:53)

Three honest limits: labels are self-declared, fingerprints drift so the model is dated, and the solo class rests on a few dozen blocks. Ethically, the data are public and pseudonymous, but fingerprinting is dual-use, so we publish aggregate findings only, and the advisor shows odds, not advice. We used AI coding agents throughout, but every stage was verified by a person. Some agent outputs were wrong and we caught them: a macro-F1 that counted pools which no longer exist, an association-rule run that returned zero rules because the threshold ignored base rates, and a future method that overshot its own backtest. Our independent verification recomputes 17 results through separate code paths: 17 pass.

## Slide 16 · So — can a small miner still win?

**Member 5** · 55 s (ends at 15:48)

To answer our three questions. One: behaviour narrows a block down to a few look-alike pools, not always the exact one — and that ceiling is itself evidence that block building is concentrated in fewer set-ups than pool names suggest. Two: the eras of mining are written in the data. Three: in Hong Kong, a small miner can still win — but only as a lottery, with odds of 1 in 16,362 a year, while paying for electricity every day. After the 2028 halving the odds stay, and the economics get harder. Thank you — we are happy to take questions.

## Slide 17 · Thank you · Questions

**Member 5** · 15 s (ends at 16:03)

Invite questions; each member answers for their own stage (see the Q&A sheet).


**Total: 16 min 3 s.**
