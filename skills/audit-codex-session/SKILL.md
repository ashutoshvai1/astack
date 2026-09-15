---
name: audit-codex-session
description: Audit a long Codex session for obvious token inefficiencies that existing skills or small reusable helpers could address. Use for retrospective session-efficiency reviews.
---

# Audit Codex Session

Find the highest-confidence workflow improvements supported by the session.
Keep the audit smaller than the work it evaluates; propose changes unless the
user also authorized implementation.

## Gather bounded evidence

Run the bundled Python 3.6+ standard-library helper using the supplied session
ID or JSONL path. Resolve an unspecified current session from available context;
ask for its identity if ambiguous rather than choosing the newest file silently.

```bash
python3 <skill-directory>/scripts/audit_session.py --session <id-or-path>
```

Use `--sessions-dir <directory>` to override `$CODEX_HOME/sessions` or
`~/.codex/sessions`. Scope defaults to that session only. Add
`--include-children direct` or `--include-children recursive` when child work is
part of the requested audit. `--output <file.json>` optionally saves metrics.
The helper streams logs, prints a compact summary and line references, and
does not export transcripts or generated reasoning.

## Interpret and propose

- Own response IDs are deduplicated, including owned compaction usage. Cached
  input is part of input; reasoning is part of output. Never sum inherited
  thread totals. Counter-only fallback and missing evidence limit conclusions.
- Action categories are heuristics and their tokens are **action-attributed**,
  not proven waste, billable cost, or guaranteed savings. Check a few referenced
  calls and outputs before making causal claims; avoid full transcript reads.
- Separate skill paths present in instructions from read attempts and visible
  successful reads. Forked context may already contain a skill: inspect bounded
  inherited evidence only when it changes a recommendation. Absence of a local
  read does not prove the skill was unavailable or ignored.
- Compare obvious repetition, waits/polls, truncation, large context, and inline
  helper rebuilding against the relevant existing skills. Prefer one small
  reusable helper or a precise existing-skill edit over new checklists.
- Respect governing runtime and communication constraints. A skill cannot
  override a higher-priority wait limit; distinguish runtime fixes from skill
  fixes. Necessary validation and successful task work are not waste by count.

Return scope and accounting limits, then up to three ranked concrete skill or
helper proposals with line evidence, the repeated mechanism, and expected
qualitative benefit. Report fewer when evidence is weak; avoid billing estimates.
