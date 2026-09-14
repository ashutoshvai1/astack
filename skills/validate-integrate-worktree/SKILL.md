---
name: validate-integrate-worktree
description: Validate a scoped vd2moe worktree with its external evidence, then complete requested commits, integration, and remote verification. Use for merge-readiness reviews or closing an approved development branch.
---

# Validate and Integrate Worktree

Resolve the target vd2moe checkout from the request and Git worktree inventory.
All project paths below belong to that checkout, never the skill installation.
Read its `AGENTS.md`, `devlog/current.md`, `devlog/decisions.md`, and relevant
validation/environment documentation. This skill needs no other installed skill.

## Establish scope and mode

Identify the source branch/worktree, destination branch, requested file scope,
and requested endpoint: readiness report, scoped commit, local integration, or
push. Preserve authorization already given in the conversation; do not introduce
a fresh approval step for an action the user has authorized. A readiness review
alone does not authorize integration or publication.

Inspect `git status --short --branch`, `git worktree list --porcelain`, relevant
local refs, upstream configuration, and source/destination diffs. Distinguish
committed changes from staged, unstaged, and untracked work. Record current SHAs
and unrelated changes so later actions can be checked against the actual scope.
Inspect configured remote URLs without exposing credentials; identify the
intended remote and branch before any push.

For a read-only review, inspect without rewriting records, materializing files,
creating commits, or merging. Use the experiment renderer only with `--check`.
Run appropriate checks when their outputs are permitted; if a check would write
into protected input evidence, use an existing read-only mode or report the gap.

For authorized integration, use the existing scoped worktree when suitable.
Create an isolated sibling worktree if required to preserve unrelated work or
validate a combined candidate. Inspect before reusing an existing branch/path.
Do not automatically stash, discard, stage, or commit unrelated changes.

## Resolve evidence and environment

Before treating a missing checkpoint as a regression, inspect affected manifests,
their `external_uri` values and hashes, and the checkout owning each retained
MLflow store. Read `docs/workflow.md` for the current external-artifact contract.
Check source availability and destination identity; a local cache does not
replace verification of the retained external artifact.

When materialization is within scope, inspect the existing helper and its CLI:

```bash
python scripts/experiments/materialize_external_artifacts.py results/<experiment_id>/artifact_manifest.json --destination-root <target-checkout>
```

Select affected manifests only. The helper restores all externally referenced
artifacts in a supplied manifest, so inspect its inventory before copying large
files. Preserve checksum mismatches as failures; do not overwrite source evidence
or weaken manifests to make a check pass. If evidence storage is unavailable,
report which validations remain incomplete and continue independent checks.

Load `docs/lumi.md` and any applicable experiment environment override. Use its
documented Python, module stack, `PYTHONNOUSERSITE`, and required repository or
submodule import paths. Do not substitute a guessed environment after an import
failure. Keep submodules read-only unless their changes are explicitly in scope.
CPU checks may run on login nodes; GPU work requires a separate authorized Slurm
action and is not implied by worktree integration.

## Validate the candidate

Select focused `python -m pytest` tests from the behavior changed and affected
callers. Documentation-only or other low-impact edits do not require invented
regression tests. Follow required repository checks; do not default to the full
suite or repeat passing tests without a changed candidate or unresolved concern.

For changed or consumed completed evidence, use strict existence/checksum checks:

```bash
python scripts/validation/check_experiment_records.py --registry experiments/registry.yaml experiments/<experiment_id>.yaml --require-existing-artifacts
python scripts/validation/check_artifact_manifest.py results/<experiment_id>/artifact_manifest.json --experiment-id <experiment_id> --require-existing
```

Apply record checks to planning records without claiming they verify completed
evidence. Verify affected run identities, manifest ownership, and MLflow linkage
as required by the experiment; structure-only success is insufficient.

After authorized experiment-record edits, regenerate discovery with
`python scripts/experiments/render_experiment_index.py`, then run `--check`.
For devlog edits, run `python scripts/validation/check_devlog.py`. Run
`git diff --check` for working changes and check the scoped committed diff for
whitespace problems as well. Review the effective diff and file inventory.

## Integrate within the authorized scope

Stage explicit scoped paths and inspect the staged diff before requested commits.
Check that no unrelated change or generated/raw artifact entered the commit.
Re-read source and destination SHAs before integration; if either moved, inspect
the new diff rather than relying on the earlier validation result.

Use the requested integration method; otherwise prefer a fast-forward when
possible. Resolve routine conflicts within scope. Preserve valid scientific
gate failures, split-access history, immutable artifact identities, and accepted
run provenance. Never resolve evidence conflicts by selecting favorable metrics.
Merge live coordination semantically into `devlog/current.md`; experiment YAMLs
own decisions, manifests own inventories, and current state must remain current.
If a conflict requires an unresolved scientific choice, prepare the independent
work and identify that choice before changing its dependent evidence.

Validate the actual combined candidate when integration changes the tested tree,
including conflict resolutions or new destination commits. Re-run affected tests
and record/devlog checks; do not reuse a passing source-branch result as proof of
an untested merged tree. A fast-forward to the same validated tree needs no
redundant rerun unless its environment or evidence inputs changed.

For an authorized push, inspect the current remote branch with `git ls-remote`
and push only the intended ref without force. If the remote has advanced,
reconcile and validate the resulting candidate instead of overwriting it.
After push, use `git ls-remote <remote> refs/heads/<branch>` to verify that the
published SHA equals the intended local commit; a local tracking ref alone is
not remote verification. Report a failed push or mismatched ref as incomplete.

Do not delete artifact-owning worktrees. Any separately requested cleanup must
first establish that retained artifacts were migrated and manifests revalidated.
Finish with the source/destination branch and commit, scoped changes, checks and
their limits, publication result if requested, and remaining concrete blockers.
