# astack

Reusable agent skills for hypothesis-driven research: explicit experiments,
reproducible evidence, detailed run records, and concise devlog synthesis.

Your project's `AGENTS.md` defines the research goal and operating contract.
These skills use it to discover record layouts, environments, trackers,
launchers, validation commands, and evaluation rules. They are independent of
any particular research repository or model framework.

## Start a project

1. Adapt a research `AGENTS.md` you trust to the new project. Define campaign,
   experiment, logical-run, execution-attempt, and artifact ownership; specify
   decision gates, provenance, resource rules, and where live state is kept.
2. Copy selected folders from `skills/` into the project's `.agents/skills/`,
   or into `~/.agents/skills/` for personal use across projects. Avoid duplicate
   installations of the same skill. See [Codex skill setup](https://learn.chatgpt.com/docs/customization/overview#skills).
3. Open the project in Codex and invoke a skill with the relevant plan, experiment,
   job, or branch. The skills use the project's tools; they do not install an
   experiment harness or require a particular tracking service.

## Skills

| Skill | Use it to |
| --- | --- |
| [`experiment-preflight`](skills/experiment-preflight/SKILL.md) | Resolve scope, controls, budgets, and gates through questions; prepare a reproducible experiment. |
| [`supervise-slurm-experiment`](skills/supervise-slurm-experiment/SKILL.md) | Supervise Slurm jobs with passive heartbeats, bounded recovery, and scientific gate checks. |
| [`log-experiment`](skills/log-experiment/SKILL.md) | Interpret results or failures, reconcile evidence, and update relevant devlog synthesis. |
| [`estimate-time`](skills/estimate-time/SKILL.md) | Get a quick ETA and decide whether monitoring can pause. |
| [`validate-integrate-worktree`](skills/validate-integrate-worktree/SKILL.md) | Validate scoped code and evidence, then complete requested integration. |
| [`audit-codex-session`](skills/audit-codex-session/SKILL.md) | Measure a long session and identify obvious token inefficiencies addressable through skills or helpers. |

For example: `$experiment-preflight assess this hypothesis and ask me about
unresolved scope and gates before preparing the experiment.` The preparation,
supervision, logging, and integration skills require explicit invocation;
`estimate-time` and `audit-codex-session` also support automatic selection.
Only live Slurm snapshots require Slurm.

## Helpers

Copy whole skill folders, including `scripts/`. The helpers use the Python
standard library and support Python 3.6 or newer. Run a helper's `--help` for
its inputs and examples.

- `supervise-slurm-experiment/scripts/slurm_snapshot.py` batches known-job
  status queries and reads bounded log tails. Saved snapshots retain the next
  heartbeat deadline and can be reused by `estimate-time` without another query.
- `experiment-preflight/scripts/run_logged_command.py` runs an authorized
  command once, keeps complete output in a new log, and reports status plus a
  bounded failure tail. Supply a trusted project environment with `--env-script`
  when needed; pass literal arguments after `--`. It grants no execution or
  resource authorization; `passed` means command exit zero, not a scientific gate.
- `audit-codex-session/scripts/audit_session.py` summarizes recorded token usage
  and likely sources of repeated work without dumping the transcript. Child
  scope is optional; cached input is distinguished from newly generated output.

Use explicit supervision invocation in launch/resume requests. Preserve the
heartbeat deadline through short waits and follow the active runtime's waiting
and communication rules. These skills do not override a higher-priority wait
limit or start unattended polling services.

Focused helper checks: `python -m pytest -q tests` (requires pytest).

## Research style

Keep hypotheses, gates, outcomes, and decisions in canonical experiment records.
Link logical runs to execution attempts and immutable artifacts. Preserve valid
negative results and the provenance of retries and resumes. Keep detailed logs
in their designated store; use the devlog for current state, durable decisions,
and cross-experiment synthesis. Freeze criteria before testing, distinguish job
completion from scientific success, and keep claims within the evidence.
