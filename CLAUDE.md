This repository is one Snakemake workflow following the conventions in the `research-workflow`
skill (`~/.claude/skills/research-workflow/SKILL.md`). Load it before adding or changing rules,
environments, resource requests, or running jobs. The project plan is WORKFLOW.md and the
concept-bank procedure is CONCEPT_BANK.md; read both first. WORKFLOW.md §2 fixes the three
hypotheses, their metric and their decision rules: work that serves none of them belongs in the
extensions list, not in `rule all`. TALK.md is the presentation narrative and constrains nothing.

In short: every computation is a rule, modules are inputs via `code()`, config values reach rules
as `params`, grids live in `config/config.yaml`, every submitted rule has `benchmark:` and `log:`,
README is structure only and findings go to CHANGELOG.md. The VLM response archive under
results/score/ is a fixed input from the moment it is written; re-scoring is deliberate, not
incidental.
