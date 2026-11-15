# Q&A preparation and presenter checklist

The 20-minute slot is planned as a 1:30 intro video + ~16:30 speaking (3:14–3:23 per presenter, including a 90-second live demo) + ~2:00 buffer; Q&A is extra (timings in `timing_check.csv`, full script in
`slide_by_slide_script.md`, also in the speaker notes of `HashAtlas.pptx`). Each member answers questions on the stage
they own.

## Hand-overs

| Slides | Presenter | Hand-over line |
|---|---|---|
| 1-5 (title, intro video, questions, problem, data) | LO Chi Kong (captain) | "POON Tsz Chun will now explain our features." |
| 6-8 (features, selection, validation design) | POON Tsz Chun | "SUBEDI Anukaran will now show what happened on that test." |
| 9-11 (results, confusion, new blocks) | SUBEDI Anukaran | "YE Xiaochen continues with clustering." |
| 12-14 (eras, families and rules, limits and checks) | YE Xiaochen | "LO Ka Hung will now turn the results into decisions." |
| 15-17 (advisor, live demo, Future Lab) | LO Ka Hung | "LO Chi Kong will close." |
| 18-19 (conclusion, Q&A) | LO Chi Kong, then everyone | Each member answers for their own stage. |

## Likely questions and short answers

| Question | Owner | Answer (check the numbers in the report before the day) |
|---|---|---|
| Isn't the coinbase tag enough to know the miner? | LO Chi Kong | It *is* the label, so it can't be an input. The question is what behaviour reveals; that matters when tags are missing, shared or copied, and for how decentralised block building really is. |
| Why is pool-level accuracy modest? | SUBEDI Anukaran | Most large pools build blocks with the same fee-maximising template; contrast mining finds no distinctive itemset for them. Top-3 and template-family accuracy are much higher. The ceiling is itself the finding. |
| Why did the tree beat KNN and SVM so clearly? | POON Tsz Chun | The signal sits in a few discrete bit patterns (signal bits, number of rolled version bits). Axis-aligned tree splits capture them; distances and kernels dilute them across ~50 standardised features. We tested top-k and MI-weighted distances: no material gain. |
| Why not shuffled cross-validation? | POON Tsz Chun | Blocks on the same day share conditions, and pools change over time; folds are grouped by month and the final test is a later, sealed period. |
| How do you know your labels are right? | LO Chi Kong | 2019+ labels are mempool.space's attribution; our own tag labeller agrees with it 99.95% of the time when it finds a tag (audited on ~424k blocks). |
| Is DBSCAN "noise" an error? | YE Xiaochen | No: it marks rare but genuine weeks/blocks (transitions, empty blocks). |
| Do similar fingerprints prove a pool is controlled by another? | YE Xiaochen | No. They suggest a shared template or software; ownership needs other evidence. |
| Is this investment advice? | LO Ka Hung | No. The advisor shows odds, costs and break-even prices; electricity prices are retail snapshots. |
| How reliable is the Future Lab? | LO Ka Hung | Only the halving height is certain. The 80% band covered most backtest cases, but a no-growth guess had a smaller median error, so we read it as a range. Price and fees are user scenarios. |
| How did you use AI agents, and how did you check them? | YE Xiaochen (+ each member for their own trajectory) | Plan → review → implement → verify. Examples of caught errors are in report §15; the independent verification recomputes key numbers through separate code paths. |
| Why Bitcoin and not a Kaggle dataset? | LO Chi Kong | Complete, public, verifiable data at scale, with a real decision for people in Asia; all three course techniques fit naturally. |

## Presenter checklist

- [ ] Test the intro video on the classroom PC (slide 2: click to play; the .mp4 and .srt are in `presentation/video/` as a fallback).
- [ ] Two timed rehearsals with hand-overs and the live demo; record the actual times in `timing_check.csv`.
- [ ] Laptop on mains power; dashboard open on the Overview page; second tab with Block Radar.
- [ ] Demo fallback: if the network fails, use the screenshot on slide 16 and `reports/screenshots/`.
- [ ] Speak to the audience, not the slides; one presenter clicks for the demo.
- [ ] Professional attire; arrive 15 minutes early; test the projector and HDMI/USB-C adapter.
