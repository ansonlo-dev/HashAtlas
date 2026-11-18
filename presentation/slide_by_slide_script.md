# HashAtlas presentation script

**Slot: 20:00 (Q&A not included).** Planned: 1:30 video + 16:38 speaking = **18:08**, leaving **1:52** for hand-overs, clicks and the unexpected. Speaking time = words at 130 wpm + 8 s per slide; the demo is a fixed 90 s slot. Generated from `presentation/build/build_deck.js` together with the slides (the same text is in the speaker notes); every number comes from the pipeline outputs.

| Presenter | Slides | Speaking | Ends by |
| :--- | :--- | ---: | ---: |
| LO Chi Kong (captain) | 1, 2, 3, 4, 5, 18, 19 | 3:22 | 18:08 |
| POON Tsz Chun | 6, 7, 8 | 3:17 | 7:26 |
| SUBEDI Anukaran | 9, 10, 11 | 3:18 | 10:44 |
| YE Xiaochen | 12, 13, 14 | 3:18 | 14:02 |
| LO Ka Hung | 15, 16, 17 | 3:23 | 17:25 |
| *Video (played, not spoken)* | 2 | 1:30 | |

Rehearsal rule: if a presenter runs more than 15 s over their total, cut a sentence from their *own* slides, never from the next person's.

## Slide 1 · Can a small Bitcoin miner still win?

**LO Chi Kong** · 20 s speaking (ends at 0:20)

Imagine plugging a Bitcoin miner into a Hong Kong wall socket. Would you join a pool, try solo, or switch it off? Keep your choice in mind.

## Slide 2 · Introduction video

**LO Chi Kong** · 10 s speaking + 90 s video (ends at 2:00)

[Click to play the 90-second introduction video; do not talk over it. When it ends:] Let’s look at the evidence.

## Slide 3 · What can a block reveal about its miner?

**LO Chi Kong** · 40 s speaking (ends at 2:40)

We asked three questions. First, from a block's behaviour alone, never its name, can we tell who mined it? Second, clustering and association rules: do the data rediscover the CPU, GPU and ASIC eras on their own, and which pools build blocks alike? Third, decision making: should a miner in Hong Kong join a pool, mine solo as a lottery, or switch off, today and after the 2028 halving?

## Slide 4 · What makes miner identification difficult?

**LO Chi Kong** · 45 s speaking (ends at 3:25)

Five constraints shaped our design. API rate limits meant our downloads had to resume after an interruption. Labels are self-declared: a pool's name is text written into the block, so it is the label and never an input. No look-ahead: we train on the past and test on the most recent period. Solo blocks are extremely rare. And we report costs and uncertainty. We rejected four alternatives: predicting the price, simply reading the tag, tracing transactions, and black-box deep learning.

## Slide 5 · 975,494 blocks, zero gaps, audited labels

**LO Chi Kong** · 44 s speaking (ends at 4:09)

Our table includes the November follow-up blocks, 975,494 of them. Blockchair's daily dumps cover 2009 to 2018; from 2019 we pulled blocks pool by pool from mempool.space, about 4,364 API calls. The final table has zero missing and zero duplicate heights. To trust our labels, we compared our own tag-matching labeller with mempool.space on 424,464 blocks: when it finds a tag, the two sources agree 99.95% of the time. POON Tsz Chun will now explain our features.

## Slide 6 · How we built a miner fingerprint

**POON Tsz Chun** · 74 s speaking (ends at 5:23)

Thank you. A block header contains a 32-bit version field and a 32-bit nonce. They are stored as integers, but they are really nominal bit fields, so we decomposed them into individual bits. This matters because the coinbase text can be missing or copied, so behaviour is the one signal a pool cannot simply rename. Modern ASIC miners roll the general-purpose version bits 13 to 28, and pools differ in how many bits they roll. From the block body we built ratios such as fullness and witness share. We also built day-relative features: each block's fee level or size minus that day's median, which removes market conditions and leaves only the miner's policy. We deliberately added the hour of day as a control feature that should be useless. And we excluded everything that leaks the label: coinbase text, payout address, height and calendar time.

## Slide 7 · Feature selection: 77 → 51

**POON Tsz Chun** · 59 s speaking (ends at 6:22)

Selection used the training data only, and moved from filters to a wrapper. First a variance filter removed near-constant features. Then mutual information was compared with ten random noise probes: anything no better than noise was dropped, 19 features in total, including both timestamp features. That is a finding in itself: block discovery is a random process for every miner, so timing carries no fingerprint. Next we removed redundant pairs with Spearman correlation above 0.9. Finally, a group ablation on the right: removing the version bits or the body-composition group clearly hurts the cross-validated score, while the hour-of-day control does nothing and was removed. That left us with 51 features.

## Slide 8 · How we tested on future blocks

**POON Tsz Chun** · 64 s speaking (ends at 7:26)

How we learned the models matters as much as which models we used. Shuffled cross-validation would put blocks from the same day on both sides of a split and overstate accuracy, so our folds are grouped by calendar month. We tuned a decision tree, KNN, and both linear and RBF support vector machines on the 2019-to-2023 training period; the table shows the selected settings and how each model scored. Nested cross-validation estimates the whole tuning procedure for the tree at 0.378 macro-F1, which gives us a check on selection bias. Finally, the model choice and the solo threshold were frozen on the out-of-time validation period, before the sealed test was ever opened. SUBEDI Anukaran will now show what happened on that test.

## Slide 9 · How well does the tree identify a pool?

**SUBEDI Anukaran** · 67 s speaking (ends at 8:33)

Thank you. On the sealed test period the decision tree is clearly best: macro-F1 0.244, with a bootstrap interval of 0.24 to 0.25, about 3.0 times the random baseline. Macro-F1 is our main metric because it weighs every pool equally, so a model cannot score well by predicting only the largest pools. KNN and the SVMs struggle, because the signal sits in a few discrete bit patterns that tree splits isolate, while distances and kernels dilute them across fifty features. On the right are three accuracies: the exact pool is right 42% of the time, against 18% for always guessing the largest pool, and the true pool is among the tree's top three 69% of the time. So behaviour narrows a block down to a few look-alike pools.

## Slide 10 · Who looks like whom?

**SUBEDI Anukaran** · 66 s speaking (ends at 9:39)

The confusion matrix shows where the errors go. Pools with a distinctive habit, such as signalling bits or an unusual number of rolled version bits, sit on the diagonal. The largest pools blur into each other, because since 2023 almost everyone fills blocks with the same fee-maximising template. A strong test of this idea is pools that did not exist in training: SpiderPool is predicted as Foundry USA 29% of the time, and MARA Pool is predicted as Other pools 45% of the time. So the model is recognising a block template, not a brand name, which is why top-three accuracy matters. Modern solo blocks look like pool blocks too: the solo class reaches an average precision of 0.01, against a base rate of 0.04%.

## Slide 11 · What happened after we froze the model?

**SUBEDI Anukaran** · 65 s speaking (ends at 10:44)

Finally, we applied the frozen model to new examples, in two ways. First, 92 blocks from the last year carry no pool tag at all; the model assigns each one, 55% of them with high confidence. Second, a true out-of-time check: 1,446 blocks mined after our data freeze, from the first to the twelfth of November. We predicted first and revealed the labels afterwards: 36% were exactly right, a little below the sealed test, which reminds us that fingerprints drift and the model must be retrained. The same fingerprints also measure concentration: by pool name, 3 pools mine half of all blocks; if look-alike families were one builder, it would be 1. That is an upper bound, not proof. YE Xiaochen continues with clustering.

## Slide 12 · Weekly block patterns reveal three mining eras

**YE Xiaochen** · 65 s speaking (ends at 11:49)

Thank you. Now, clustering. We built one row per week, with nine features describing how blocks were produced, and never the dates of the hardware eras. K-means, with K chosen by silhouette because the error curve keeps falling without a clear elbow, four hierarchical linkages and DBSCAN all ran on the same rows. Only afterwards did we compare the clusters with documented history: Ward linkage reaches an adjusted Rand index of 0.89, and K-means 0.71. Three eras emerge: the hobbyist CPU and GPU years, the FPGA-to-early-ASIC transition, and the industrial era. Ward's second boundary falls two days after the 2016 halving. DBSCAN, on the other hand, marks the fast transition weeks as noise: density-based clustering cannot separate eras that blend into each other.

## Slide 13 · Pool families and block signatures

**YE Xiaochen** · 68 s speaking (ends at 12:57)

Clustering the pools themselves by their average fingerprint gives families: AntPool plus Braiins Pool plus Foundry USA plus Luxor; and Binance Pool plus CloverPool plus Poolin. This agrees with the classifier, which read newcomers as the pool closest to them. Association rules tell the same story from another angle. Our from-scratch Apriori, checked against a brute-force count, found rules such as fullness=full(>=98%) and version=signal bits set implies SBI Crypto, with a lift of 43. Lift matters here: confidence alone would favour the largest pools, so we keep only rules whose lift is well above one. Contrast mining inside each pool gives the signatures on the right, while some large pools have no distinctive rule at our thresholds. Similar fingerprints suggest shared templates or software; they do not prove common ownership.

## Slide 14 · What our checks caught

**YE Xiaochen** · 65 s speaking (ends at 14:02)

Before the decisions, three honest limits. Labels are self-declared, fingerprints drift so the model is dated, and the solo class rests on only a few dozen test blocks. A single extra correct prediction can move recall for that class. We used AI coding agents throughout, but a person verified every stage, and some agent outputs were wrong. We caught a macro-F1 that counted pools which no longer exist, an association-rule run that returned zero rules because the threshold ignored base rates, and a forecasting method that overshot its own backtest. Our independent verification recomputes 17 key results through separate code paths, and all 17 pass; the deck reads these checks from the pipeline outputs. LO Ka Hung will now turn the results into decisions.

## Slide 15 · Should you mine in Hong Kong?

**LO Ka Hung** · 54 s speaking (ends at 14:56)

Thank you. Now the decision. At our data freeze, one terahash per second earned about 0.038 US dollars a day. An Antminer S21 therefore covers its electricity only below 0.089 dollars per kilowatt-hour. Hong Kong business power costs 0.175, so an S21 here loses 7.26 dollars a day. Across Asia, only the economies in green are below break-even. For a 1.2 terahash home device, the advisor's answer is clear: it is a lottery ticket, with odds of 1 in 16,362 per year, not an income. Because this is real money, the advisor shows odds and costs, never investment advice.

## Slide 16 · Live demo: the HashAtlas dashboard

**LO Ka Hung** · 90 s speaking (ends at 16:26)

[Live demo, 90 seconds; switch to the browser.] One: the Overview, with seventeen years of hash rate, eras and halvings. Two: Block Radar: reveal the labels of blocks mined after our freeze. Three: Fingerprint Lab: load a real solo block, flip the version-rolling feature and watch the tree re-route it. Four: Miner Advisor: switch from Hong Kong to Kazakhstan and watch the verdict change. [If the network fails, use the screenshot on this slide.]

## Slide 17 · What could the 2028 halving change?

**LO Ka Hung** · 59 s speaking (ends at 17:25)

How much future did we include? Only what can be grounded. The protocol halves the block subsidy at height one million fifty thousand, and our 4,000 simulated paths put that around 2028-04-07. Hash-rate growth is resampled from history, while price and fees are scenarios the user chooses, not forecasts. We also backtested the method from past dates: the 80 percent band covered 75% of cases, but a naive no-growth guess had a smaller median error, so the fan should be read as a range. At today's price, the S21's break-even power price falls from 0.082 in early 2027 to 0.029 a month after the halving. LO Chi Kong will close.

## Slide 18 · So, can a small miner still win?

**LO Chi Kong** · 27 s speaking (ends at 17:52)

Behaviour narrows down the pool. Weekly patterns recover the hardware eras. And a home miner in Hong Kong faces solo odds of 1 in 16,362 a year, while paying for electricity every day. At this tariff, the S21 loses money each day.

## Slide 19 · How does proof of work secure Bitcoin?

**LO Chi Kong** · 16 s speaking (ends at 18:08)

For an animated explanation of proof of work, save this 3Blue1Brown video for later. We welcome your questions. [Advance to Q&A.]


**Total: 18:08 of 20:00.**
