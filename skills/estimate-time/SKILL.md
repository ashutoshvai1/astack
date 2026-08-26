---
name: estimate-time
description: Quickly estimate time remaining for a running job and, when relevant, the active goal. Use for rough ETA checks or deciding when monitoring can pause.
---

# Estimate Time

Aim for a useful rough range with minimal inspection, not a precise forecast. Use a quick read-only snapshot; do not modify the job, continuously poll, or exhaustively mine logs and history.

- Check readily available status, elapsed time, progress, and whether the job continues without Codex. Stop once there is enough evidence for a rough estimate.
- Estimate from recent progress or a convenient comparable run. Separate queue delay from runtime; a time limit is not an ETA. Broad ranges and low confidence are acceptable.
- Optionally estimate goal ETA from the obvious remaining critical path. Omit it when it would be mostly speculation.
- Say whether pausing is safe and suggest an approximate recheck time; flag if pausing stops orchestration.

Report the snapshot time, rough ETA range and basis, optional goal ETA, next gate, and pause recommendation. Say `unknown` when even a broad estimate lacks support.
