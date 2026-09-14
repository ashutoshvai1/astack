---
name: validate-integrate-worktree
description: Validate a scoped research worktree and its evidence, then complete requested commits, integration, and remote verification. Use for merge-readiness reviews or closing an approved development branch.
---

# Validate and Integrate Worktree

Resolve the target project and source/destination worktrees from the request.
Read their applicable `AGENTS.md`, linked current state and decisions, and
validation/environment documentation. Derive record paths, artifact storage,
tracker, and test commands from the project, not this skill's location.

## Establish the candidate

Identify scope and endpoint: readiness report, commit, local integration, or
push. Preserve existing authorization; a readiness review alone does not
authorize merging or publication. Inspect Git status, worktree inventory,
source/destination SHAs, staged and unstaged changes, and relevant diffs.
Keep unrelated modifications and untracked files intact. Use an isolated
worktree when needed; do not silently stash, discard, or stage others' work.

For a read-only assessment, do not rewrite records or materialize artifacts.
Use read-only/check modes where available. For authorized integration, inspect
affected evidence records before treating a missing local artifact as a code
regression. Locate its canonical owner and verify identity/checksums. Restore
needed artifacts with the documented mechanism when within scope; inspect size
and destination before copying, and never overwrite mismatched evidence.
Report unavailable storage separately while continuing independent checks.

## Validate applicable behavior and evidence

Use the documented environment and backend. Select tests for the actual diff
and affected callers; ordinary documentation edits need no invented regression
tests. Run required checks without automatically expanding to the full suite.
Resource-intensive experiments are not implied by a merge request.

For changed or consumed completed evidence, verify actual artifact existence,
checksums, logical-run/attempt ownership, provenance, and tracker linkage.
Schema-only success does not establish reproducibility; planning records do not
establish completed results. Preserve valid failed gates and evaluation-access
history. Use the project's guarded publication path for authorized record fixes.

Refresh generated indexes after relevant edits and check them; use check-only
modes in audits. Validate changed devlog and other documentation as prescribed.
Check whitespace and review the effective file inventory and diff. State which
checks are incomplete rather than weakening them to obtain a passing result.

## Integrate and verify

Stage explicit scoped paths and inspect the staged diff before committing.
Recheck source/destination refs; inspect changes if either moved. Use the
requested integration method, otherwise prefer a fast-forward when possible.
Resolve routine conflicts semantically: preserve current research direction,
canonical record ownership, immutable evidence, and valid scientific decisions.
Do not select favorable metrics to resolve evidence conflicts. If a conflict
requires an unresolved scientific choice, ask before changing dependent evidence.

Validate the actual combined candidate when integration or conflict resolution
changes the tested tree. Re-run affected checks; an unchanged validated tree
needs no redundant rerun unless its environment or evidence inputs changed.

For an authorized push, check the intended remote branch, push only the intended
ref without force, and verify its published SHA with `git ls-remote`. Reconcile
remote advances instead of overwriting them; a failed push is incomplete work.
Do not remove worktrees or stores owning referenced artifacts during integration.
Separately authorized cleanup requires migration and revalidation first.

Report the integrated branch/commit, scoped changes, validation and its limits,
publication result when requested, and any remaining blocker.
