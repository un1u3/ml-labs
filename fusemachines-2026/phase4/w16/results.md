# Evaluation results

Task completion: 5/7
Tool-call correctness: 6/7
Average trajectory length: 3.9 iterations
Average tokens per query: 3198

| case | completed | tool calls correct | iterations | tokens | seconds |
|---|---|---|---|---|---|
| single fact | yes | yes | 3 | 2622 | 3.2 |
| two sources | yes | yes | 5 | 5031 | 8.4 |
| search plus math | no | no | 6 | 4913 | 64.5 |
| vague question | yes | yes | 1 | 514 | 0.8 |
| not in docs | no | yes | 6 | 6538 | 40.2 |
| inject: search down | yes | yes | 2 | 1131 | 4.4 |
| inject: malformed | yes | yes | 4 | 1636 | 17.7 |

## Failure log

- search plus math: hard (Stopped after reaching the step limit.)
- not in docs: hard (Stopped after reaching the step limit.)
