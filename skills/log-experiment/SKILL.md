---
name: log-experiment
description: Analyze completed research results or failures and reconcile experiment records, artifacts, tracking, and devlog synthesis.
---

# Log Experiment

Work in the experiment-owning project. Read its `AGENTS.md` and linked current
state, decisions, and evidence rules; derive paths, schemas, tracker, and commands
there. Resolve the requested experiment before writing; timestamps alone do not
establish ownership. Logging does not authorize new trials or evaluation access.

1. **Inspect:** Read the hypothesis, frozen inputs/gates, logical runs, execution
   attempts, artifact inventory, tracker records, metrics, and relevant bounded
   logs. Verify source provenance and actual artifact existence, checksums, and
   ownership, including external storage. Report gaps without fabricating evidence.
2. **Interpret:** Evaluate the frozen gate from admissible evidence; job completion
   is not scientific success. Preserve valid negative results and access limits.
   Distinguish measurements from estimates and supported conclusions from causal
   hypotheses. Explain what the result changes about the research question.
3. **Reconcile:** Update canonical status, analysis, decision, and next steps using
   the project's publication workflow and transaction protections. Keep one
   accepted result per logical-run slot; retries follow project replacement rules
   and retain bounded reasons. Preserve consumed evidence and checksum-bound
   resume trajectories. Do not duplicate runs, overwrite immutable artifacts,
   or clear incomplete publication markers to make records pass.
4. **Synthesize:** Update live devlog only for changed state or continuation,
   durable decisions only for cross-experiment policy, and campaign synthesis
   only for changed aggregate interpretation. Keep detailed evidence in its
   designated records and raw logs in storage; avoid copied inventories or prose.
5. **Validate:** Refresh affected discovery and run the project's record,
   artifact, tracker, and documentation checks. Use strict existence/checksum
   validation for completed evidence; unavailable evidence means incomplete
   validation. Read-only audits use check modes and leave records unchanged.

Report the gate decision, key results, evidence limits, changed records, checks,
and next action. Do not retroactively change the hypothesis or gate to fit results.
