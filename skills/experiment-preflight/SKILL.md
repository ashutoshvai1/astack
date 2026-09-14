---
name: experiment-preflight
description: Assess and prepare a research experiment, using questions to finalize hypotheses, scope, controls, budgets, and decision gates. Use before new experiments or controlled ablations, not for routine status checks or completed-result logging.
---

# Experiment Preflight

Make the intended experiment reproducible and ready for its authorized next step.
Work in the target research project, not this skill's installation directory.
Read its `AGENTS.md` and linked current state, decisions, experiment plan, and
environment instructions. Derive paths, schemas, tracker, and commands from that
project; do not require a particular repository, framework, or scheduler.

## Resolve the scientific choices

Identify the campaign, experiment, hypothesis, reference/control, and decision
the result should inform. Connect the experiment to the project's research goal.
Distinguish planning, preparation, and authorized execution. Carry forward prior
answers and approvals; inspect existing work before creating another experiment.

Ask focused questions during assessment to finalize unresolved scope and gates.
Use the available question tool when permitted, preferably asynchronously while
continuing independent checks; otherwise ask in plain text. Batch up to three
related questions, with concrete choices and a recommendation when justified:

- **Scope:** treatment and control, independent or combined arms, variables held
  fixed, replicates/seeds, included phases, and exclusions.
- **Budget:** resource/time/cost limits, search allowance, accounting units, and
  stopping rules. Distinguish theoretical estimates from measured costs.
- **Gates:** primary outcome, evaluation procedure, numeric threshold or other
  operational criterion, rationale, and action on pass or failure. Separate
  mandatory validity checks from descriptive metrics.
- **Evaluation access, when applicable:** selection data versus final evaluation,
  allowed accesses, prerequisites, and authorization for that phase.

Do not invent scientific thresholds. Propose a criterion with its evidence or
rationale and resolve it with the user before freezing it. If every relevant
choice is already settled, summarize it without another approval round.
Silence and preselected options are not answers. Keep material choices pending
until answered; a planned record may capture settled facts and open questions,
but dependent execution inputs must not be frozen or launched yet.

## Check the proposed experiment

- Compare the actual config and implementation with the reference. For a
  controlled ablation, change only the named factor; keep separate arms separate.
  For reproductions, reuse pinned reference code where appropriate and document
  adaptations that could affect interpretation.
- Identify the consumed source revision and modifications, resolved config,
  inputs/data, and reused artifacts with the project's provenance and checksum
  conventions. A commit alone does not describe dirty or untracked source.
- Verify required dependencies, artifacts, execution environment, allocation,
  and phase ordering. Inspect the real launcher and supported arguments;
  execution must follow the project's backend and resource rules.
- Check prior evidence, evaluation accesses, and accepted decisions. A changed
  scientific recipe needs the identity/lineage required by the project; never
  erase an unfavorable valid result or retrospectively repair its provenance.

## Prepare and continue

For planning-only work, update only the planned record and relevant roadmap.
Once choices are settled and preparation is authorized, use the project's setup
workflow to freeze inputs and establish the required run/artifact/tracker records.
Keep campaign, experiment, logical-run, and attempt identities consistent.
Do not create fake execution evidence or assume a missing helper exists. If a
required capability is absent, identify the smallest implementation needed and
handle it within the authorized scope before claiming readiness.

Run applicable preparation checks and strictly verify any reused evidence,
including artifact existence and identity. Update canonical records and discovery
as documented. Update the live devlog only for changed state or continuation;
keep detailed run evidence in its designated records, not duplicated prose.

Report the settled scope and gates, checks, unresolved prerequisites, and exact
next commands. Continue already-authorized execution when prerequisites pass.
If additional permission is required, finish the reviewable preparation first
and ask only for the remaining action. Readiness is not a passed scientific gate.
