# `.agent-operability/`

Agent-owned operational state for this repo.

| Path | Purpose |
|---|---|
| `task-queue.json` | Structured queue accessible to agents. |
| `worksheets/` | Resumable per-task worksheets. |
| `feedback-log.md` | End-of-session feedback that improves workflow/docs. |
| `reports/` | Local validation/review/benchmark artifacts. |
| `baselines/` | Visual/performance baseline metadata. |

Do not store secrets here. Do not delete reports to hide failures.
