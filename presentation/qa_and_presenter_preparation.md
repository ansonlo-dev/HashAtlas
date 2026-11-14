# Q&A preparation and presenter checklist

The talk is about 16 minutes including a ~2-minute live demo (adjust to the announced slot) (timings in `timing_check.csv`, full script in
`slide_by_slide_script.md`, also in the speaker notes of `HashAtlas.pptx`). Each member answers questions on the stage
they own.

## Hand-overs

| Slides | Presenter | Hand-over line |
|---|---|---|
| 1-4 (opening, problem, data) | Member 1 | "Over to Member 2 for how we turned blocks into fingerprints." |
| 5-7 (features, selection, models) | Member 2 | "Member 3 will now show the results." |
| 8-11 (results, eras, families, rules) | Member 3 | "Over to Member 4: what should a miner actually do?" |
| 12-14 (advisor, live demo, Future Lab) | Member 4 | "Member 5 will close." |
| 15-17 (limits, ethics, agents, conclusion, Q&A) | Member 5 | – |

## Likely questions and short answers

| Question | Owner | Answer (check the numbers in the report before the day) |
|---|---|---|
| Isn't the coinbase tag enough to know the miner? | M1/M2 | It *is* the label, so it can't be an input. The question is what behaviour reveals; that matters when tags are missing, shared or copied, and for how decentralised block building really is. |
| Why is pool-level accuracy modest? | M3 | Most large pools build blocks with the same fee-maximising template; contrast mining finds no distinctive itemset for them. Top-3 and template-family accuracy are much higher. The ceiling is itself the finding. |
| Why did the tree beat KNN and SVM so clearly? | M2 | The signal sits in a few discrete bit patterns (signal bits, number of rolled version bits). Axis-aligned tree splits capture them; distances and kernels dilute them across ~50 standardised features. We tested top-k and MI-weighted distances: no material gain. |
| Why not shuffled cross-validation? | M2 | Blocks on the same day share conditions, and pools change over time; folds are grouped by month and the final test is a later, sealed period. |
| How do you know your labels are right? | M1 | 2019+ labels are mempool.space's attribution; our own tag labeller agrees with it 99.95% of the time when it finds a tag (audited on ~424k blocks). |
| Is DBSCAN "noise" an error? | M3 | No: it marks rare but genuine weeks/blocks (transitions, empty blocks). |
| Do similar fingerprints prove a pool is controlled by another? | M3 | No. They suggest a shared template or software; ownership needs other evidence. |
| Is this investment advice? | M4 | No. The advisor shows odds, costs and break-even prices; electricity prices are retail snapshots. |
| How reliable is the Future Lab? | M4 | Only the halving height is certain. The 80% band covered most backtest cases, but a no-growth guess had a smaller median error, so we read it as a range. Price and fees are user scenarios. |
| How did you use AI agents, and how did you check them? | M5 | Plan → review → implement → verify. Examples of caught errors are in report §15; the independent verification recomputes key numbers through separate code paths. |
| Why Bitcoin and not a Kaggle dataset? | M1 | Complete, public, verifiable data at scale, with a real decision for people in Asia; all three course techniques fit naturally. |

## Presenter checklist

- [ ] Two timed rehearsals with hand-overs and the live demo; record the actual times in `timing_check.csv`.
- [ ] Laptop on mains power; dashboard open on the Mission Control page; second tab with Block Radar.
- [ ] Demo fallback: if the network fails, use the screenshots on slide 13 and `reports/screenshots/`.
- [ ] Speak to the audience, not the slides; one presenter clicks for the demo.
- [ ] Professional attire; arrive 15 minutes early; test the projector and HDMI/USB-C adapter.
