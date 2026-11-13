# Assignment 6 · Should RepoMind split the work?

## Part A · Before the experiment

On one issue, the writer has to wait until someone finds the cause. On five unrelated issues, five investigators can start searching right away. That was my reason for trying the split.

```text
One issue     Coordinator → Investigator → Coordinator → Writer → Tracker
Five issues   Coordinator → 5 investigators in parallel
              Each finding → Coordinator → Writer for that issue → Tracker
              Coordinator reads the tracker to check all five issues.
```

| Pair | What they need from each other |
|---|---|
| Coordinator and investigator | The coordinator assigns an issue and a token allowance. The investigator returns a label, file, evidence and open questions. A search that turns up nothing can still leave the cause unknown. |
| Investigator and writer | The writer gets the finding through the coordinator. It can only act on the evidence the investigator includes. |
| Coordinator and writer | The coordinator assigns the writes. The receipts show which actions succeeded. Checking whether the label and file are right takes a separate test. |

| Gate | One issue | Five issues |
|---|---|---|
| 1. Independent work? | **Fail.** The writer needs the diagnosis before its first action. I stopped here. | **Pass.** Each investigation can proceed on its own. |
| 2. Checkable parts? | — | **Pass.** I can check each issue's label, PR and comment, then check that all five issues were handled. |
| 3. Benefit over one agent? | — | **Pass.** One agent can start a fresh context per issue. Separate investigators can also overlap their searches. |
| 4. Worth the cost? | — | **Tentative pass.** At my predicted 1.2× spend, I'd accept the split if batches took at least 25% less time and passed as often as one agent at the same spend. |

I wanted to test **parallelism**, which needs independent issues and enough capacity for simultaneous calls. Context isolation helps when little has to pass between workers. Specialisation made sense here because only the writer needed permission to change the tracker.

My prediction was that the split (M) would use 1.4× the original agent's (S) tokens on singles and 1.2× on batches. I expected M to pass 15/18 singles and 4/6 batches, versus 16/18 and 3/6 for S. I expected one agent at M's spend (S-plus) to do at least as well as M. [Prediction, commit 7fd82c5](PREDICTIONS_06.md)

## Part B · What I built

I gave investigators four tools to read an issue, search code, open files and run tests. Writers could apply a label, open a draft PR and post the final comment. Investigations ran in parallel. The coordinator started one writer at a time as findings came in and skipped issues without a usable finding. All tools went through the policy hook, and code added the disclosure to each comment.

I divided the run budget evenly across issues. Each investigator got two thirds of its issue's share. The writer got the rest, including room for its last request and response. The coordinator made no model calls.

| Check | How it worked |
|---|---|
| Return contract | `split/roles.py` checks each return against `split/contract.schema.json`. The investigator supplies the issue, label, file, evidence, status (found, candidate or out of budget) and what it couldn't determine. Code counts calls and records searches, file reads and search hits left unopened. An invalid return is logged and rejected so the worker can retry. |
| Deadlock | `WaitGraph` tracks who is waiting on whom. In the replay it found the cycle and identified a worker to stop. |
| Shared writes | `SharedState` checks the version before accepting a finding. In the replay, B's stale write failed and A's edit survived. Repeating an accepted write has no further effect. Tracker writes use their existing keys. |
| Combined result | After the last write, I checked each issue's comment against its label and PR in the tracker. The check caught the planted bad batch and accepted the good one. These three guards are in `split/guards.py`. |
| Shared trace | `ways/split.py` gives each worker an ID and parent. I could follow its calls, waits and token use in one run trace. |

## Part C · Results

I ran each arm three times on the same eight tasks with one runner job. All 72 runs used `gemini-3.5-flash-lite`, tool schemas `703c0002892f27ec`, evaluator `55abcd67e6a3b208` and reviewer `scripted:approve-all`. S and M had 250,000 tokens per issue, or 1,250,000 per batch. For each task, S-plus targeted M's actual mean spend. I scored the tracker state. A batch passed only if all five issues passed.

| Arm | Task kind | Passes / runs | Sweep range | Tasks passing 3/3 | Mean tokens | Mean seconds |
|---|---|---:|---:|---:|---:|---:|
| S | single | 12/18 | 3–6 | 2/6 | 54,826 | 7.7 |
| S | batch | 2/6 | 0–1 | 0/2 | 325,985 | 30.0 |
| M | single | 6/18 | 1–3 | 1/6 | 36,731 | 9.4 |
| M | batch | 0/6 | 0–0 | 0/2 | 139,998 | 11.3 |
| S-plus | single | 8/18 | 2–4 | 2/6 | 35,750 | 9.5 |
| S-plus | batch | 0/6 | 0–0 | 0/2 | 139,110 | 37.7 |

Each task ran three times. Tokens and seconds are averages.

| Task | S passes / tokens / s | M passes / tokens / s | S-plus passes / tokens / s | S-plus spend vs. M |
|---|---:|---:|---:|---:|
| batch-a | 0/3 · 370,902 · 30.0 | 0/3 · 136,636 · 11.3 | 0/3 · 135,920 · 37.8 | -0.5% |
| batch-b | 2/3 · 281,068 · 30.0 | 0/3 · 143,360 · 11.3 | 0/3 · 142,300 · 37.6 | -0.7% |
| one-4402 | 1/3 · 75,679 · 9.8 | 0/3 · 47,291 · 9.2 | 0/3 · 45,882 · 8.5 | -3.0% |
| one-4403 | 3/3 · 33,713 · 6.1 | 0/3 · 29,846 · 8.5 | 1/3 · 28,572 · 10.5 | -4.3% |
| one-4405 | 2/3 · 54,298 · 9.5 | 1/3 · 43,697 · 10.6 | 1/3 · 43,196 · 10.9 | -1.1% |
| one-4406 | 1/3 · 61,891 · 6.8 | 3/3 · 40,234 · 11.0 | 3/3 · 38,968 · 9.8 | -3.1% |
| one-4409 | 2/3 · 66,677 · 8.5 | 2/3 · 23,283 · 7.6 | 3/3 · 22,569 · 7.7 | -3.1% |
| one-4413 | 3/3 · 36,699 · 5.7 | 0/3 · 36,031 · 9.3 | 0/3 · 35,316 · 9.7 | -2.0% |

**Did the split spend more?** It used 0.67× S's tokens on singles and 0.43× on batches. My prediction was high for both. Lecture 6 gives Anthropic's figures as about 15× chat for a team and 4× chat for one agent. I compared the two designs directly on RepoMind.

**Did spending more help?** The higher-spend single agent, S, passed more singles (12 vs. 8) and batches (2 vs. 0) than S-plus. S-plus also used fresh attempts and voted before writing, so I can't attribute the difference to tokens alone.

**Could one agent match the split at the same spend?** Yes. S-plus came within 4.3% of M's mean spend on every task. It passed two more singles and tied M at zero whole batches. From S and M alone, I'd have said that splitting saved batch time at the cost of accuracy. S-plus showed that one agent also struggled at the smaller budget. Some of M's speed came from skipping writes after an investigator failed.

### Why the split failed

I found no concurrency anomaly in any of the 18 failed runs. In each case the coordinator waited for a finding on that issue. When an investigator ran out of turns, the writer never started. When the investigator returned a wrong answer, the writer could carry that error into the tracker.

A recurring mistake was passing the string `"null"` as a path filter. The tool looked for matching paths and returned zero hits. Passing JSON `null` would have searched the whole repository. The table gives one cause per failed run and lists every issue that failed.

| Failed run | Failed issues | What went wrong | MAST category |
|---|---|---|---|
| `split-batch-a-s01-5170e4` | 4410, 4412, 4414, 4423 | #4410 used the wrong path filter on `TOKEN_TTL_MINUTES`. | system design |
| `split-batch-a-s02-f6cb79` | 4410, 4412, 4414 | #4410 used the wrong path filter on `TOKEN_TTL_MINUTES`. | system design |
| `split-batch-a-s03-ad7677` | 4410, 4414, 4420 | #4410 used the wrong path filter on `TOKEN_TTL_MINUTES`. | system design |
| `split-batch-b-s01-65e0db` | 4424, 4431 | #4424 used the wrong path filter on `travel-expenses`. | system design |
| `split-batch-b-s02-a036c4` | 4424, 4426, 4429, 4431 | #4424 used the wrong path filter on `travel-expenses`. | system design |
| `split-batch-b-s03-b0b54e` | 4424, 4431 | #4431 used the wrong path filter on `report-`. | system design |
| `split-one-4402-s01-ce3918` | 4402 | Reached turn 12 after reading `src/util/money.ts`, `src/ingest/schema.ts`. | system design |
| `split-one-4402-s02-f5eaba` | 4402 | Reached turn 12 after reading `src/util/money.ts`. | system design |
| `split-one-4402-s03-163d7f` | 4402 | Reached turn 12 after reading `src/util/money.ts`. | system design |
| `split-one-4403-s01-4f500e` | 4403 | #4403 used the wrong path filter on `\ufeff`. | system design |
| `split-one-4403-s02-bb634b` | 4403 | Reached turn 12 after reading `src/export/csv.ts`, `src/ingest/parser.ts`. | system design |
| `split-one-4403-s03-cddeb3` | 4403 | The writer copied `src/export/csv.ts` into the comment. The investigator had cited it as a file to change on a question. | task verification |
| `split-one-4405-s02-38f227` | 4405 | The investigator called remembering an export preference a bug. The writer applied that label to a feature request. | task verification |
| `split-one-4405-s03-e94475` | 4405 | #4405 used the wrong path filter on `Export`. | system design |
| `split-one-4409-s02-8c945f` | 4409 | Reached turn 12 after reading `README.md`. | system design |
| `split-one-4413-s01-a75095` | 4413 | #4413 used the wrong path filter on `toast`. | system design |
| `split-one-4413-s02-ebcb11` | 4413 | Reached turn 12 after reading `src/components/Toast.tsx`, `src/components/UploadForm.tsx`. | system design |
| `split-one-4413-s03-5d1b55` | 4413 | #4413 used the wrong path filter on `toast`. | system design |

## Part D · My decision

I'd keep one agent for both tasks. On singles it passed twice as often as the split and finished sooner. On batches the split beat my speed target, averaging 11.3 seconds against 30.0 for S. What changed my mind was the tie with S-plus. Both passed zero batches. S passed two.

I'd retry the batch split on fresh groups of five independent issues, with a check per issue and three sweeps at matched spend. To switch, I'd want at least one whole batch to pass, at least as many batch passes as S, and a 25% drop in average time. For singles, I'd reconsider if the split passed more issues at matched spend. [Decision record](../decisions/0006-topology.md)

## AI assistance

I used OpenAI Codex to help write and debug the code, generate results tables, and run automated checks. For the written answers, AI helped me understand what the questions were asking, break down the concepts, interpret my results and their implications, and brainstorm and draft some responses. I reviewed the code and explanations, ran the live experiments, and checked and revised the written answers to reflect my understanding.
