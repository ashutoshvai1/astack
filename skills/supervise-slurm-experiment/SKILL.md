---
name: supervise-slurm-experiment
description: Supervise a vd2moe Slurm experiment with passive ten-minute heartbeats, evidence-aware recovery, and gated continuation. Use for an authorized experiment's execution or a bounded status request.
---

# Supervise Slurm Experiment

This skill follows the vd2moe experiment protocol. Resolve repository paths
against the experiment-owning checkout, including when installed from astack.

## Establish ownership and authorization

Read `AGENTS.md`, `devlog/current.md`, `devlog/decisions.md`, the target experiment
YAML, and `docs/lumi.md` plus any experiment-specific environment override.
Follow active-work links to an owning worktree before inspecting or changing its
records. Check `git status --short --branch` and preserve unrelated changes.

Resolve the experiment ID, logical runs, scheduler attempts, submitted dependency
chain, frozen config, split-access allowance, and agreed resource/retry budget.
Use records, submission receipts, and logs; timestamps alone do not establish
ownership. If several experiments remain plausible, ask which one before acting.

Distinguish a one-time status/ETA request from authorization to supervise and
continue execution. A status request is read-only and ends after its snapshot.
For supervision, carry out already-authorized submissions, recovery, and next
phases when their frozen prerequisites pass; do not ask for the same approval
again. Skill invocation alone does not authorize cancellation, changed training
recipes, larger allocations, extra trials, or additional final-split access.

Inspect the owning checkout's existing `scripts/slurm/` wrapper and underlying
entrypoint before any submission or repair. Confirm their supported phases,
environment, paths, and flags; wrappers can hard-code historical experiment IDs.
Use the documented Slurm account and GPU allocation. GPU work never runs on a
login node. Missing preflight decisions must be resolved before dependent work.

## Take bounded heartbeats

Take one initial snapshot, then one snapshot per ten minutes while a long-running
job progresses independently. Poll sooner only for an imminent transition,
detected failure, or explicit user request; identify the reason for that exception.
Use an interruptible passive wait within the harness's wait limits. Shorter wait
calls must not cause extra scheduler/log reads. Do not use shell sleep/poll loops,
`watch`, `tail -f`, or continuously poll an execution cell for unchanged output.

Bound each snapshot to the evidence needed for the next decision:

- Query the known job IDs with bounded `squeue` output for state, elapsed time,
  pending reason, and dependencies. Use bounded `sacct` output for terminal or
  disappeared jobs; disappearance from `squeue` does not establish completion.
- Read a small relevant tail of those attempts' stdout/stderr and the latest
  structured progress or gate artifact. Use exact paths under the experiment ID.
- Note the snapshot time, phase/step progress, next gate, and next admissible
  action. Scheduler failure, artifact availability, and scientific outcome are
  separate observations.

Estimate a broad remaining-runtime range from observed progress or a comparable
run. Separate queue delay, runtime, and any remaining dependent phases; walltime
limits are not ETAs. Say `unknown` when progress provides no defensible estimate.
An installed `estimate-time` skill can assist using this same snapshot; otherwise
apply these rules directly without additional polling.

Keep the user update compact and give the next heartbeat time. Respond to new
user input while waiting. Do not imply monitoring continues after the session
ends; identify any later phase that needs the agent to submit or inspect it.

## Recover only admissible attempts

For `DependencyNeverSatisfied` or another blocked chain, inspect the predecessor's
terminal state and evidence. Scheduler `afterok` dependencies establish exit
success, not scientific gate success. Preserve downstream scientific guards.
Repair/resubmit a dependency only within existing authorization after resolving
the actual failure; do not drop its dependency or bypass a failed gate to run it.

Classify an invalid attempt using the repository's supported values:
`infrastructure`, `interrupted`, `protocol`, or `implementation`, with a concrete
reason. Verify admissibility before replacement: unchanged experiment, seed,
phase/split, and execution-input hash, with no valid gate consuming its evidence.
A decision-only config correction is allowed only if it cannot change evaluated
tensors or metrics. A changed recipe belongs to a newly scoped experiment.
Never replace valid unfavorable metrics or a valid failed scientific gate.

Use the existing entrypoint's explicit replacement option and class/reason fields.
For example, ToMoE/D2DMoE wrappers support `REPLACE_INVALID_ATTEMPT`,
`REPLACEMENT_CLASS`, and `REPLACEMENT_REASON`; confirm current phase support before
using them. These options do not establish that a retry is scientifically valid.

For exact resume, verify that the source checkpoint is a checksum-bound artifact
owned by the accepted logical run and that the entrypoint restores the required
training state. Retain each contributing segment's attempt, step range, and
resume-source checksum as trajectory provenance. Do not classify contributing
segments as discarded retries. Inspect actual resume support; a generic restart
or weights-only load is not an exact continuation.

Publish through the existing lifecycle entrypoint using `src/vd2moe/records.py`
(`begin_run_record`, `commit_run_evidence`). Preserve locked identity revalidation
and the fail-closed transaction marker. Do not independently edit accepted run,
manifest, or MLflow inventories or clear markers to force acceptance.
`scripts/experiments/record_invalid_replacement.py` records bounded metadata for
a terminated provisional attempt; it does not publish replacement evidence.
Retain all consumed final-split accesses, including invalid/terminated attempts.

Before retrying, establish that the cause is resolved and the retry fits the
remaining agreed budget. Stop dependent actions for unresolved repeated failure,
unsupported safe resume/publication, exhausted budget, or needed scope changes;
report the specific blocker and ask only for the missing decision/authorization.
Do not enter an unbounded retry loop or silently cancel existing jobs.

## Evaluate completion and reconcile evidence

On termination, check the frozen scientific gate and evidence independently of
Slurm's exit status. Continue an authorized next phase only when the required
checksum-bound gate, provenance, and remaining split-access allowance all permit
it. Preserve valid failed gates as outcomes; do not tune against final-split data.

Use `log-experiment` if installed and applicable. Otherwise reconcile the YAML's
status/decision, accepted logical runs, immutable artifact manifest, and MLflow
parent/child linkage through the existing publication entrypoint. Update
`devlog/current.md` only for changed live state, blockers, or continuation; follow
`AGENTS.md` for any synthesis updates and avoid per-heartbeat Markdown inventories.

Load the documented environment and validate changed evidence with
`scripts/validation/check_experiment_records.py --require-existing-artifacts` and
`scripts/validation/check_artifact_manifest.py --require-existing`, passing the
target record/manifest and required registry/experiment arguments. Inspect their
current CLI if needed. Regenerate discovery with
`python scripts/experiments/render_experiment_index.py` after record edits, then
run it with `--check`; use only `--check` for an audit.
Run `python scripts/validation/check_devlog.py` for devlog edits and `git diff --check`.
Unavailable artifacts mean incomplete validation, not structure-only success.

Report the experiment outcome, checks, remaining blocker or next authorized
action, and rough ETA if still running. Keep routing quality, analytical selected
expert cost, actual execution, and measured deployment benefit distinct.
