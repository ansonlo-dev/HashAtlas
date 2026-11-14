# Agent-use trajectories

The CDS3004 group project requires **each member's own agent-use history**: the instructions they gave an AI agent,
the agent's responses, and the revisions they asked for. The instructor expects **at least ten rounds of interaction
per member**, covering problem selection, data preparation, techniques and evaluation. Multiple sessions are fine;
list every link.

| Member | Agent / harness used | Share link(s) or exported file(s) | Rounds (approx.) | Main topics |
|---|---|---|---|---|
| LO Chi Kong (captain) | _e.g. Claude Code_ | _add link or file_ | _n_ | problem definition, data acquisition, cleaning and label audit, integration, deployment, video |
| POON Tsz Chun | _e.g. VS Code Copilot_ | _add link or file_ | _n_ | fingerprint features, leakage checks, feature selection, tree / KNN / SVM tuning, Fingerprint Lab |
| SUBEDI Anukaran | _..._ | _add link or file_ | _n_ | sealed-test evaluation, bootstrap, explanations, predictions on new blocks, Block Radar |
| YE Xiaochen | _..._ | _add link or file_ | _n_ | K-means / hierarchical / DBSCAN, Apriori and rules, independent verification, tests |
| LO Ka Hung | _..._ | _add link or file_ | _n_ | miner advisor, Future Lab and backtest, dashboard data, ethics, live demo |

Names must match `configs/team.json`.

## How to export a trajectory

- **ChatGPT / Codex:** open the conversation, choose *Share*, and copy the link (as in the instructor's example).
- **VS Code Copilot Chat:** use the chat's export option (*Chat: Export Chat...*) and save the JSON file in this folder.
- **Claude Code:** run `/export` in the session to save the transcript as a text file, and place it here as
  `member-N-<topic>.txt` (or share it through your own storage and paste the link above).

Before sharing, remove API keys, passwords, personal e-mail addresses and anything you would not want the instructor
to read. Do not edit the substance of the conversation: the trajectory is evidence of how the agent was directed and
checked.

## What a good trajectory shows (human-agent workflow from the special tutorial)

1. **Human defines the problem**: the question, the constraints and what "good" means.
2. **Agent proposes a plan**: for example, the three candidate data sources, or the validation design.
3. **Human reviews the plan**: rejects or corrects it (for example, "the coinbase tag is the label, so it must not be a
   feature"; "use month-grouped folds, not shuffled CV").
4. **Agent implements**.
5. **Human verifies the outputs**: reruns tests, checks a number by hand, inspects a plot, compares against
   `artifacts/verification.json`.
6. **Revise and repeat.**

Examples of agent outputs this project rejected or corrected after verification are listed in section 15 of the
report. Rejected suggestions are as valuable as accepted ones.
