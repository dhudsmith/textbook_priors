This repository is one Snakemake workflow following the conventions in the `research-workflow`
skill (`~/.claude/skills/research-workflow/SKILL.md`). Load it before adding or changing rules,
environments, resource requests, or running jobs. The project plan is WORKFLOW.md and the
concept-bank procedure is CONCEPT_BANK.md; read both first. WORKFLOW.md §2 fixes the three
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
