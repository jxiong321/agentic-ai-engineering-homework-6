# 0006 · Keep RepoMind single-agent

I'd keep one agent for single issues and batches. The split took 11.3 seconds per batch against 30.0 for the original agent, but all six split batches failed. The original agent passed two.

**What I expected.** One issue failed the first gate because its writer had to wait for a diagnosis. I stopped there. Batches passed all four gates provisionally. The issues were independent, I could check them separately, and overlapping the searches seemed worth 1.2× the tokens for a 25% speedup. I predicted that the split would pass 4/6 batches against the original agent's 3/6. On singles I expected 1.4× the tokens and 15/18 passes against 16/18. I expected a single agent at the split's spend to match it. [Prediction, commit 7fd82c5](../reports/PREDICTIONS_06.md)

**What I tested.** All arms used `gemini-3.5-flash-lite`, tool schema hash `703c0002892f27ec`, evaluator hash `55abcd67e6a3b208` and reviewer `scripted:approve-all`. I ran three sweeps of batch-a, batch-b and single issues 4402, 4403, 4405, 4406, 4409 and 4413. The original agent (S) and split (M) had 250,000 tokens per issue. S-plus targeted M's mean spend on each task.

| Result | Single issues | Five-issue batches |
|---|---:|---:|
| Tokens used by M relative to S | 0.67× | 0.43× |
| Passes by S at its higher spend | 12/18 | 2/6 |
| Passes by M | 6/18 | 0/6 |
| Passes by S-plus at matched spend | 8/18 | 0/6 |

I expected the split to spend more. It spent less in both groups. S passed more tasks at its higher spend, though S-plus also changed how it made attempts. At matched spend, one agent beat the split on singles and tied it on batches. Some split investigations ended before the writer could act.

**What would change my mind.** Keeping one agent costs batch time and gives one role both read and write access. Splitting limits those permissions, but the writer depends on someone else's diagnosis. I'd repeat three sweeps on fresh, independently checked batches at matched spend. I'd switch if the split passed at least one whole batch, matched or beat S's batch pass count, and cut mean time by at least 25%. For singles, I'd reconsider if the split passed more issues at matched spend. [Full results and failed runs](../reports/LAB_06.md)

ARCHITECTURE.md remains unchanged.
