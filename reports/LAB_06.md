# Assignment 6 · Split it, measure it, decide

Model: Google Gemini (gemini-3.5-flash-lite), the same for every run.

## Part A · The gates, before you build

The coordinator owns the issue list and token budget. Each issue gets a read-only investigator and a writer with permission to label the issue, open a draft PR and post the closing comment.

| Pair | What they exchange | Cost or limitation |
|---|---|---|
| Coordinator and investigator | The coordinator sends an issue ID and allowance. The investigator returns the proposed label and file, supporting evidence, status, observed calls and search coverage, and unresolved questions. | Validating the return takes work. Even a valid return can omit relevant evidence. |
| Investigator and writer | The writer needs the finding for its own issue. The coordinator relays the validated return between rounds. If evidence is ambiguous, the coordinator can request a targeted read within the remaining budget. | The writer waits for the investigation and cannot inspect source code itself. Treating an exhausted search as proof that no file is responsible could suppress a needed PR. |
| Coordinator and writer | The coordinator assigns the write to an issue. The writer returns the outcomes of its label, conditional PR and final comment, including any refused action. | A write receipt establishes what the tracker accepted. It cannot establish that the diagnosis was correct. |

**One issue**

```text
Coordinator → Investigator → Coordinator → Writer → Coordinator
 issue, cap     finding, gaps     write order   receipts
Coordinator → tracker → combined check
```

The whole task follows one dependency chain. The coordinator can report whether the recorded actions agree. Determining whether the chosen file actually caused the issue requires evidence beyond that consistency check.

**Five issues**

```text
Coordinator → Investigators 1…5 (in parallel, one issue each)
Each investigator → Coordinator → Writer for the same issue → Coordinator
Coordinator → tracker → combined check over all five issue IDs
```

Each investigator reads the same repository snapshot. No investigation needs another issue's finding. Issue IDs stay attached to findings and receipts so that the coordinator can detect a missing issue or an action applied to the wrong one.

| Gate | One issue | Batch of five |
|---|---|---|
| 1. Can the parts work mostly independently? | **Fail.** Every substantive write depends on the diagnosis, and an ambiguous finding sends work back upstream. | **Pass.** Each issue has its own investigation and tracker records. The handoff stays within that issue. |
| 2. Can each part be checked on its own? | Not reached | **Pass.** For each issue, compare the cited evidence to its source and check the label, draft PR and comment against the tracker. Across the batch, also check coverage and agreement for all five IDs. |
| 3. What can a team buy more cheaply? | Not reached | **Pass.** Independent searches can overlap. Fresh contexts and a saved work log can help a sequential agent keep issues straight, but neither overlaps model calls. |
| 4. Is the benefit worth the cost? | Not reached | **Pass provisionally.** At the predicted 1.2× token spend, I would accept the extra cost for at least a 25% reduction in mean batch elapsed time with whole-batch reliability at least as high as S-plus. The measured runs will test that judgment. |

The intended benefit is parallelism. It depends on independent issues and enough provider capacity for concurrent calls. Context isolation needs small handoffs and is also available to S-plus. Tool specialisation helps because the investigator only needs reads and the writer needs narrowly scoped writes. Different prompts alone would leave both roles able to make the same write mistakes.

The prediction in `reports/PREDICTIONS_06.md` (commit `7fd82c5`) puts M at 15/18 single runs and 4/6 batches, compared with 16/18 and 3/6 for S. I expect S-plus to equal or exceed M's pass count in both groups.

## Part B · The split

- The coordinator and the roles, and the tools each holds:
- Why they split by tool surface:
- The return contract, field by field, and which fields come from the worker's tool calls:
- Each worker's share of the budget, and what is held back:
- The five checks, where each is in your code:

## Part C · Measured

**The five constants** (slide 59): model, tools, budget, evaluator, task set.

**The results.**

| Arm | Kind | Passes / runs | Lowest and highest sweep | Tasks all three passed | Mean tokens | Mean wall-clock (s) |
|---|---|---|---|---|---|---|
| S | single | | | | | |
| S | batch | | | | | |
| M | single | | | | | |
| M | batch | | | | | |
| S-plus | single | | | | | |
| S-plus | batch | | | | | |

- Your multiplier (M over S), single and batch, beside the lecture's 15×:
- Whether S-plus's spend matched M's in fact, task by task:

**Slide 18's three questions**, for each kind of task.

| Question | One issue | A batch of five |
|---|---|---|
| Did the split spend more? | | |
| Does spending more raise the score? | | |
| Given the same budget, did one agent do as well? | | |

- What you would have claimed from arms S and M alone, and what you claim now:

**Every arm M run that failed.**

| Run | What each agent read, wrote and waited on | The first thing that went wrong | Anomaly | MAST category |
|---|---|---|---|---|
| | | | | |

## Part D · The decision

- One issue:
- A batch of five:
- The condition that would reopen it:
- The record: `decisions/0006-topology.md`

## AI assistance

Codex drafted the Part A analysis and predictions and checked the recorded gate values against the report.
