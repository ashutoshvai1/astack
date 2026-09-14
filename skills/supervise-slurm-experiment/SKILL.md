---
name: supervise-slurm-experiment
description: Supervise research experiments on Slurm with passive heartbeats, evidence-aware recovery, and gated continuation. Use for authorized execution or a bounded Slurm status request.
---

# Supervise Slurm Experiment

Work in the experiment-owning project. Read its `AGENTS.md`, linked current
state and experiment record, and execution/environment instructions. Derive
paths, account, resources, launcher, tracker, and evidence rules there. This skill
requires Slurm; it does not prescribe a cluster, research domain, or codebase.

## Establish ownership and scope

Resolve experiment and logical-run identities, job attempts, dependency chain,
frozen inputs, gates, and remaining resource/retry/evaluation allowances. Use
records and submission receipts; timestamps alone do not establish ownership.
Ask about ambiguous identities before acting. Preserve unrelated work.

A one-time status/ETA request is read-only and ends after its snapshot. For
supervision, continue already-authorized phases and recovery when prerequisites
pass, without requesting the same approval again. Do not infer permission for
cancellation, a changed recipe, larger allocations, or additional final accesses.
Inspect the actual launcher and its supported phases/arguments before submission.

## Monitor passively

Take one initial bounded snapshot, then one every ten minutes while the job
progresses independently, unless the user or project specifies another cadence.
Read sooner only for an imminent transition, detected failure, or explicit
request. Use interruptible passive waits within tool limits; shorter wait calls
must not trigger extra scheduler/log reads. Avoid continuous polling and log tails.

- Query known job IDs with bounded `squeue` output for state, elapsed time,
  dependencies, and pending reason. Use `sacct` for terminal or disappeared jobs;
  disappearance from the queue is not proof of completion.
- Read a small relevant stdout/stderr tail and available structured progress or
  gate output. Reuse that snapshot for ETA; separate queue delay and runtime,
  and report `unknown` when the evidence is insufficient.
- Give a compact update: snapshot time, phase/progress, next gate or blocker,
  next action, and next heartbeat time. Keep the agent responsive to new input.

State whether jobs progress without the agent and which transitions still need
orchestration. Do not imply monitoring continues after the session ends.

## Recover and advance

For blocked dependencies, inspect the predecessor's terminal state and evidence.
`afterok` establishes exit success, not scientific success. Correct the actual
failure within authorization; never remove a dependency to bypass a failed gate.

Distinguish infrastructure, interruption, protocol, or implementation failure
from a valid unfavorable result. Use the project's replacement rules and reason
codes. Preserve logical-run identity for an admissible retry, prior evaluation
accesses, and evidence already consumed by valid gates. A changed recipe requires
new scientific lineage; a valid failed gate is not a replaceable attempt.

Before retrying, establish that the cause is resolved and the retry fits the
remaining budget. For exact resume, verify source artifact identity and restored
execution state; retain contributing attempts, progress ranges, and source
checksums as trajectory provenance. A partial state restore is not an exact resume.
Stop dependent actions for unresolved repeated failure, exhausted allowances, or
unsupported recovery. Ask only for the missing decision; avoid unbounded retries.

Use the project's supported publication workflow to keep run, artifact, and
tracker inventories consistent. Honor its locking/transaction protections; do
not clear incomplete markers or hand-edit accepted evidence to force acceptance.
Advance only after checking scientific gates and remaining allowances separately
from scheduler success. Preserve valid failures and final-evaluation boundaries.

## Close the experiment

Reconcile the outcome with its canonical experiment/run/artifact records and
tracker, including source provenance and failed decisions. Use an installed
logging skill if appropriate, otherwise follow `AGENTS.md` directly. Validate
actual artifact existence, checksums, and ownership using the project's checks;
missing evidence means incomplete validation. Refresh discovery when required.
Update the live devlog for changed state, durable decisions in their designated
record, and campaign synthesis only when the interpretation changes. Keep raw
logs in their designated store, not per-heartbeat prose. Report the outcome,
validation limits, and remaining authorized action; distinguish measured results
from estimates and claims the experiment did not test.
