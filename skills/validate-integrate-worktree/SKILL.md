---
name: validate-integrate-worktree
description: Check research branches and evidence, then complete authorized Git integration.
---

# Validate and Integrate Worktree

Read the target project's `AGENTS.md` and linked state, environment, and validation
instructions. Resolve source, destination, scope, and endpoint: audit, commit,
merge, or push. An audit is read-only; preserve existing execution authorization.

1. Inspect worktrees, refs, and staged/unstaged/untracked changes. Preserve
   unrelated work; isolate the candidate when necessary. Verify missing
   artifacts against their canonical owners before diagnosing regressions.
   Restore verified artifacts only within scope; report inaccessible storage.
2. Run required checks and focused tests for changed behavior. Verify consumed
   evidence's existence, checksums, ownership, provenance, and tracker linkage;
   schema-only success is insufficient. Follow project publication rules for
   record fixes, preserving failed gates and evaluation-access history. Refresh
   affected indexes/devlog as prescribed; audits use check-only modes.
3. Stage explicit paths and review the diff. Recheck source/destination refs;
   inspect advances before integrating. Prefer fast-forward unless another
   method is requested. Resolve conflicts semantically, preserving current
   research direction and canonical evidence. Ask about unresolved scientific
   choices. Validate changed combined trees and conflict resolutions; unchanged
   validated inputs need no redundant rerun.
4. Push only authorized refs without force. Reconcile remote advances, then
   verify the published SHA with `git ls-remote`; failed publication is incomplete.
   Retain artifact-owning worktrees/stores until separately authorized migration
   and cleanup have been validated.

Report commits, scoped changes, checks and their limits, publication, and blockers.
