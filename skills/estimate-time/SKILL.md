---
name: estimate-time
description: Estimate remaining time for a running job or research workflow. Use for a rough ETA or pause decision, not ongoing supervision or job changes.
---

# Estimate Time

Use the named job and target project's `AGENTS.md` and status sources when
available. Resolve ambiguous ownership; do not assume a scheduler or log layout.
Take one small read-only snapshot or reuse a recent one. Do not change jobs,
continuously poll, or exhaustively search logs and history.

- Estimate a broad range from progress and throughput or a comparable run.
  Separate queue delay, startup, and remaining work; a time limit is not an ETA.
  State the basis and uncertainty; say `unknown` without sufficient evidence.
- Include workflow ETA only when its critical path is clear. Account for parallel
  phases without summing them as sequential work.
- State whether pausing leaves independent progress running or stops needed
  orchestration. Suggest a recheck using project cadence, normally ten minutes
  for long-running work unless an imminent transition warrants sooner.

Report snapshot time, ETA, next gate, and pause recommendation concisely.
Do not imply monitoring continues after the response.
