---
name: supervise-slurm-experiment
description: Monitor Slurm research jobs and continue authorized phases or recovery.
---

# Supervise Slurm Experiment

Read the target project's `AGENTS.md`, current state, experiment record, and
execution instructions. Resolve run/job identities, dependencies, frozen gates,
and remaining allowances. A status request is read-only; supervision continues
already-authorized work without fresh approval.

- **Monitor:** Take one bounded status/log snapshot, then wait passively for ten
  minutes unless project/user cadence differs. Check sooner only for an imminent
  transition, failure, or explicit request. Shorter wait calls must not cause
  extra reads. Use `squeue` for known jobs and `sacct` for disappeared/terminal
  jobs; inspect a small log tail and structured progress.
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
