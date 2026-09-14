## Work in `~/Code/textbook_priors`, and nowhere else

**Edit, run, commit and push from the owner's checkout at `~/Code/textbook_priors`.** Not from a
session worktree under the runner's `_sessions/` tree, for any of it. This is the owner's standing
instruction, it is what `config/config.yaml`'s `run_root` names, and the Snakefile refuses to
execute anywhere else (set `PRIORS_ALLOW_ANY_CWD=1` only if you truly mean to).

Two reasons, both of which cost this project real time before the rule existed:

- **The results have to be findable.** `results/`, the write-protected response archive under
  `results/score/`, `report/`, `benchmarks/`, `logs/` and `.snakemake/` all live beside the
  Snakefile. The owner builds the talk from those files. A run from a worktree puts them somewhere
  they will hunt for and somewhere that is deleted without warning.
- **A session worktree is recreated underneath you.** It happened four times in one session. A
  commit made there can be parented to a stale base and silently truncate an append-only file such
  as `SESSION_LOG.md`; it happened, and was caught by a rejected push rather than by review. Before
  trusting a worktree, `git log --oneline -1` it against `origin`.

**One session touches the checkout at a time.** Two Claude sessions ran at once on 2026-09-13; the
second switched this checkout onto its own branch mid-run, five jobs read the wrong code, and its
`--touch` reached the shared `data/cache` symlink and made the whole archive look stale
(`CHANGELOG.md`, 2026-09-13). If another session may be running, check `git status` and
`squeue -u $USER` before starting, and say so rather than working around it.

**After editing any module, `--touch` before running.** `priors/stages.py` is a declared code input
of nearly every rule, so editing it makes Snakemake plan to re-buy the entire 58,186-call archive.
The sequence that works: run `smoke`, then `snakemake --profile profiles/local --touch <upstream
targets>`, then read the job-stats table and confirm it holds no `score_` lines before launching.
`results/score/` is `protected()` and will refuse the write, which is the backstop, not the plan.

**One trunk: `main`.** Everything this project has produced is on `main`, and the checkout sits on
it. When the runner hands a session its own `claude/...` branch, commit there if you must, but
fast-forward `main` onto the same commit and push both before the session ends, so the next session
inherits one lineage rather than a fan of stale heads. Superseded exploration is kept as a tag under
`retired/`, never as a branch that hangs around (`SESSION_LOG.md`, 2026-09-14). The one branch that
is not a leftover is `claude/textbook-priors-workflow-2kdgap`, which WORKFLOW.md §10 cites by name
for the wider plan that was cut.

---

This repository is one Snakemake workflow following the conventions in the `research-workflow`
skill (`~/.claude/skills/research-workflow/SKILL.md`). Load it before adding or changing rules,
environments, resource requests, or running jobs. The project plan is WORKFLOW.md and the
concept-bank procedure is CONCEPT_BANK.md; read both first. WORKFLOW.md §2 fixes the seven
hypotheses, their metric and their decision rules: work that serves none of them belongs in the
extensions list, not in `rule all`. TALK.md is the presentation narrative and constrains nothing.

`docs/rcd_llm_service.md` is the reference for the LLM service the score stage calls: which models
see images, their lifecycle tiers, the `reasoning_effort` levels each accepts, the aliases that
would break an archive, and the measured throughput. Read it before changing a model, a reasoning
setting or a concurrency cap, and prefer the service's `/v1/models?full=true` metadata over probing.

In short: every computation is a rule, modules are inputs via `code()`, config values reach rules
as `params`, grids live in `config/config.yaml`, every submitted rule has `benchmark:` and `log:`,
README is structure only and findings go to CHANGELOG.md. The VLM response archive under
results/score/ is a fixed input from the moment it is written; re-scoring is deliberate, not
incidental.

Append a timestamped entry to SESSION_LOG.md whenever a prompt materially directs the work — what
was asked and why it changed the plan — separately from CHANGELOG.md, which stays the owner's
record of scientific understanding, not of agent activity. SESSION_LOG.md is talk material
(WORKFLOW.md §5.10).
