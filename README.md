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

For example: `$experiment-preflight assess this hypothesis and ask me about
unresolved scope and gates before preparing the experiment.` The preparation,
supervision, logging, and integration skills require explicit invocation; `estimate-time`
also supports automatic selection. Only the Slurm skill requires Slurm.

## Research style

Keep hypotheses, gates, outcomes, and decisions in canonical experiment records.
Link logical runs to execution attempts and immutable artifacts. Preserve valid
negative results and the provenance of retries and resumes. Keep detailed logs
in their designated store; use the devlog for current state, durable decisions,
and cross-experiment synthesis. Freeze criteria before testing, distinguish job
completion from scientific success, and keep claims within the evidence.
