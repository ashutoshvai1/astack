---
name: experiment-preflight
description: Assess and prepare a vd2moe experiment before GPU execution, using questions to finalize scope, controls, budgets, and scientific gates with the user. Use for new experiments or controlled ablations, not routine status checks or logging completed results.
---

# Experiment Preflight

Turn the intended vision dense-to-MoE comparison into a reviewable, reproducible
launch. Resolve scope and gates with the user before freezing execution inputs.
This skill follows the vd2moe evidence protocol; installing it from a skills
repository does not make that repository an experiment workspace.

## Establish the assessment

Resolve the experiment-owning checkout from the request or active project. All
project paths below are relative to that checkout, not this skill's directory.
Read its `AGENTS.md`, `devlog/current.md`, `devlog/decisions.md`, and only the
relevant plan, experiment record, and environment instructions in `docs/lumi.md`
and experiment-specific overrides. Inspect Git status and existing worktrees;
preserve unrelated changes and keep reference submodules read-only.

Distinguish planning, preparation, and already-authorized execution. Carry
forward the user's previous answers, approved scope, and authorization. Explain
how the hypothesis advances deployable vision conversion, or identify its
limited role as a diagnostic or reference comparison.

## Finalize scope and gates through questions

During assessment, ask focused questions about unresolved scientific choices.
First extract what the user and existing records already establish; do not make
the user repeat those answers. Show concrete proposed choices and their
consequences, using the inspected reference as the default when appropriate.

Prefer the available clarification tool, such as `request_user_input_async`,
while continuing independent code, environment, and provenance checks. Use
`request_user_input` only where its current mode and tool rules permit. Do not
depend on a tool literally named `AskUserQuestion`. When question tools are
unavailable or inappropriate for a required answer, ask a concise plain-text
question and wait for the answer before dependent work.

Batch at most three related questions at a time, with a recommended choice and
short alternatives when useful. Prioritize decisions that change evaluated
tensors, compute expenditure, or scientific interpretation:

| Decision | Resolve with the user when not already established |
| --- | --- |
| Scope and controls | Exact treatment, reference checkpoint and recipe, independent versus combined arms, trainable/frozen parameters, seeds, and included phases. |
| Budgets | Conversion/search/training allocation, accounting units, inference target, and whether a cost is analytical, actually executed, or measured on a target device. |
| Selection and gates | Primary metric, split, numeric threshold and rationale, mandatory integrity checks, diagnostic-only metrics, and action on pass or failure. |
| Final evaluation | Official split, permitted access count, prerequisites, and whether the request authorizes that phase or only train-derived work. |

For example, ask whether recovery is a separate arm with the reference losses
unchanged, or an explicitly combined treatment. For a proposed quality gate,
state the baseline and threshold source and distinguish it from a descriptive
metric. Do not invent thresholds such as an effective-expert minimum or quality
ratio simply because they seem reasonable. If a new gate is needed, propose a
justified candidate for the user's decision before freezing it.

Incorporate answers into the existing experiment YAML and relevant config;
keep hypotheses, gates, and decisions there rather than in a second assessment
ledger. Summarize the settled scope and gates. Silence, elapsed time, and a
preselected UI option are not answers. Leave material unanswered choices
pending; do not declare launch readiness or freeze dependent choices by
assumption. If all choices are already settled, carry them forward without a
new approval round.

For a preparation request with pending answers, the planned YAML may record
settled facts and unresolved decisions now. Withhold frozen execution artifacts
until those material choices are settled.

## Check fidelity and prerequisites

- Compare the proposed recipe with the pinned upstream implementation. Identify
  reused functions and necessary vision adaptations. Check actual parameter
  freezing, routing, losses, expert construction, and finalization behavior.
- For a controlled ablation, inspect the resolved config and relevant code diff
  against its reference. Change only the named term; keep independent arms
  separate. Equal finalized width need not imply equal learned masks or training
  cost. A masked-dense result cannot establish sparse runtime savings.
- Identify exact consumed source, submodule commits, config, checkpoint, data,
  and split identities using the project's provenance/checksum machinery. A
  nominal Git commit does not describe consumed dirty or untracked code. Capture
  permitted differences through the existing protocol or resolve the gap before
  a launch that requires clean provenance.
- Verify upstream executables, dependency versions, paths, and checkpoint
  availability in the documented environment. Review how the Slurm wrapper
  establishes that environment; a working login shell alone is insufficient.
  GPU smoke checks, training, capture, and evaluation run through Slurm only.
- Inspect prior final-split accesses, accepted runs, and consumed gates. A new
  recipe needs its own experiment identity; never repair historical provenance
  retrospectively or replace a valid failed scientific gate.
- Check the requested resource allocation and phase dependencies. Count the
  full Slurm allocation separately from visible-device process time. Scheduler
  `afterok` is not evidence that a scientific promotion gate passed.

## Prepare and report

For planning-only work, create or update only the planned experiment YAML and
the relevant roadmap/registry surfaces when needed. Do not create execution
evidence, MLflow runs, or submit jobs for a planning request.

Once scope and gates are settled and preparation is authorized, use the
experiment's inspected preparation/publication entrypoint to establish:

```text
experiments/<experiment_id>.yaml
results/<experiment_id>/frozen_config.yaml
results/<experiment_id>/runs.jsonl
results/<experiment_id>/artifact_manifest.json
```

Keep the same identity in configs, logs, MLflow, and artifact ownership. Preserve
one canonical logical run per execution-input identity, seed, and phase/split.
`scripts/experiments/prepare_experiment.py` is Stage 0-specific: do not use it
indiscriminately or overwrite an existing frozen config to make a rerun fit.
Use the existing guarded lifecycle for attempts and evidence publication.

Run the relevant documented CPU/config/provenance checks. Regenerate discovery
with `python scripts/experiments/render_experiment_index.py` after record changes,
then check with `--check`; read-only assessments use only `--check`. Validate any consumed
completed evidence with the strict record/manifest existence and checksum
flags, not structure-only checks. Update `devlog/current.md` only if live state,
blockers, or continuation changes, and validate it when changed.

Report settled treatment/control scope and gates, unresolved prerequisites,
checks actually performed, and exact environment and next launch commands.
Distinguish ready, planning-only, and pending decisions; this assessment does
not replace a machine-checked scientific gate. Continue an already-authorized
launch once prerequisites pass, using its existing Slurm entrypoint. If further
permission is actually required, finish the reviewable preparation first and
ask only for that remaining action. For continued supervision, use
`supervise-slurm-experiment` if available or follow the checkout's monitoring
and evidence rules directly.
