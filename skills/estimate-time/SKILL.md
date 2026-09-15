---
name: estimate-time
description: Estimate remaining time for a running job or research workflow. Use for a rough ETA or pause decision, not ongoing supervision or job changes.
---

# Estimate Time

Use the named job and target project's `AGENTS.md` and status sources when
available. Resolve ambiguous ownership; do not assume a scheduler or log layout.
Reuse the latest supervision snapshot while it is current, including its
observation time and next-check deadline. Take one bounded read-only snapshot
only when it is missing, due, or an explicit request or transition warrants it.
Do not change jobs, continuously poll, or exhaustively search logs and history.

- Estimate a broad range from progress and throughput or a comparable run.
  Separate queue delay, startup, and remaining work; a time limit is not an ETA.
  State the basis and uncertainty; say `unknown` without sufficient evidence.
- Reuse the previous ETA until new progress changes its basis. If available,
  `supervise-slurm-experiment/scripts/slurm_snapshot.py` provides structured
  progress; an existing snapshot is sufficient without invoking another skill.
- Include workflow ETA only when its critical path is clear. Account for parallel
  phases without summing them as sequential work.
- State whether pausing leaves independent progress running or stops needed
  orchestration. Suggest a recheck using project cadence, normally ten minutes
  for long-running work unless an imminent transition warrants sooner.

Report snapshot time, ETA, next gate, and pause recommendation concisely.
Do not imply monitoring continues after the response.
