---
name: supervise-slurm-experiment
description: Monitor Slurm research jobs and continue authorized phases or recovery.
---

# Supervise Slurm Experiment

Read the target project's `AGENTS.md`, current state, experiment record, and
execution instructions. Resolve run/job identities, dependencies, frozen gates,
and remaining allowances. A status request is read-only; supervision continues
already-authorized work without fresh approval.

- **Monitor:** Retain the last bounded snapshot and its absolute `next_check_at`
  deadline (ten minutes by default). Before that deadline, wait passively;
  shorter waits do not trigger another scheduler/log read, goal/clock query,
  ETA calculation, or replanning. Handle incoming events and required user
  communication; respect higher-priority wait limits and update cadence. Do not
  end a turn just to wait or treat a ten-minute heartbeat as permission to
  override those limits. Check early only for an imminent transition, detected
  failure, or explicit request, retaining that reason. At the deadline, take
  one snapshot and set the next deadline from it.
- **Recover:** Inspect the failed predecessor and actual launcher. Retry only
  admissible operational failures after resolving their cause, within project
  replacement rules and remaining budget. Preserve logical-run identity,
  consumed evidence and evaluation accesses; never replace a valid failed
  scientific gate. Verify resume state and checksum-bound inputs, retaining
  contributing attempts and progress ranges. Stop unresolved repeated failures;
  do not bypass dependencies, expand scope, or cancel without authorization.
- **Advance:** Check scientific gates independently of scheduler success before
  continuing authorized phases. Use the project's guarded publication workflow;
  do not force acceptance of incomplete evidence. Reconcile outcomes through
  `log-experiment` if available, otherwise follow the project's evidence and
  synthesis rules, verifying artifacts and reporting unavailable evidence.
- **Report:** Give snapshot time, progress, gate/blocker, next action, and recheck
  time. Estimate broadly from observed progress; separate queue delay from
  runtime. State what progresses without the agent and which transitions need
  orchestration; do not imply monitoring persists after the session ends.

## Snapshot helper

Use the portable Python 3.6+ stdlib [helper](scripts/slurm_snapshot.py) with explicit
job IDs and log paths. It batches `squeue`, checks `sacct` only for missing or
terminal jobs, and reads bounded log tails. JSON progress fields are selectable.
Unknown/missing state and scheduler errors are not completion; scheduler success
does not establish a scientific gate.

```bash
python3 /path/to/supervise-slurm-experiment/scripts/slurm_snapshot.py \
  --jobs-file /tmp/jobs.json --previous /tmp/slurm-snapshot.json \
  --output /tmp/slurm-snapshot.json
```

Run `--help` for the input schema and bounds. The first call tolerates an absent
previous file; calls before its deadline reuse the snapshot without Slurm/log
reads. Use `--force` only for an authorized early check. Stdout is a compact JSON
summary; `--output` preserves full bounded detail and the deadline as disposable
monitor state. Keep it outside canonical experiment evidence. The helper does
not sleep, poll, submit jobs, or edit experiment records.
