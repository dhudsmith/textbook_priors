# Session log

A timestamped record of how the user directed the agent, and why — appended, never rewritten,
never summarized away. This is raw material for the talk (`TALK.md`), which argues that an AI
coding agent's work is inspectable when it produces a recipe rather than a transcript; this file
is the transcript side of that argument, kept on purpose. It is distinct from `CHANGELOG.md`,
which stays the owner's dated record of scientific understanding — findings, decisions,
corrections — not a log of agent activity. An entry here can be as short as what was asked and
what changed; it does not need a finding to justify itself.

## 2026-09-11 15:15 — Session log started, at the user's direction

The user asked for a standing instruction so future sessions keep a timestamped log, including
records of how they directed the agent through prompts, as a helpful record for building the talk.
Added this file, a principle in `WORKFLOW.md` §5, a layout entry in §11, and a pointer in
`CLAUDE.md` telling the agent to append here — separately from `CHANGELOG.md` — whenever a prompt
materially directs the work.

## 2026-09-11 15:26 — Build the workflow one rule at a time, starting with the prompts

The user asked to start implementing `WORKFLOW.md`, but explicitly not all at once: first list the
rules the workflow will have, then implement the first one and test it, then stop for review
before proceeding. They named the first rule themselves — render the prompts.

That changed the order of work in `WORKFLOW.md` §9, which starts with the skeleton and the bank
schema test (`smoke`). `render_prompts` needs no samples, no service and no labels, so it can go
first and the skeleton it needs is small: `config/config.yaml` (paths, the dataset list, the
anchors switch), `config/medmnist.yaml` (the pinned label maps), `envs/priors.yml`, both profiles,
and `priors/{data,prompts,stages,manifest}.py`. `smoke` is next, and every rule then gains its
marker as an input.

Two conventions settled while doing it, both recorded because they will be asked about again:

- `config/config.yaml` grows section by section as the rules that read it land, rather than
  arriving whole from `WORKFLOW.md` §8, so that no key in the file is unread by a rule.
- `config/medmnist.yaml` is generated once from the `medmnist` 3.0.2 wheel rather than retyped,
  and is read by rules as an *input file* rather than as a second configfile, so that a change to
  a label map reruns the prompts and everything below them. The `smoke` target will hold it to the
  installed package.

## 2026-09-11 16:05 — Fix the octmnist collision rather than exempt it

Asked to fix the octmnist issue reported at the end of the previous turn, and to see a rendered
prompt file in the session rather than only on disk. The choice was between renaming two scale
levels in a reviewed input and recording an exemption in the smoke test; the user chose the first,
so the bank changed and `data/concepts/README.md`, the file's own header and `CHANGELOG.md` all
record the correction. The rule itself did not change.

## 2026-09-11 16:20 — Smoke next, and show the artifacts in the chat

The user asked for stage 0 next, and for representative artifacts and rule code to be linked in
the session afterwards so that readiness for the next stage can be judged without hunting through
the repository. The tests that had been run by hand at the end of the previous turn became
`tests/`, and two tiers of stage 0 that WORKFLOW.md §6 lists are deliberately absent because the
code they test does not exist yet: the arm-B estimator fixture and the LLM client's retry.

One design question came up that the plan does not settle, and the answer is in the Snakefile's
stage-0 banner: a marker that every rule depends on propagates its timestamp, so the obvious
`ancient()` wrapper was tried first, rejected on evidence (it suppressed rerun detection for the
whole job), and replaced by keeping the bank files out of the marker's inputs.

## 2026-09-11 17:30 — Stage 1, and the storage links as a script rather than a rule

Asked to proceed to the next step, which the rule list puts at `sample_dataset`. Two choices in it
are worth recording because neither is settled by `WORKFLOW.md`.

The sampled images go to `data/cache/sample/<dataset>.npz` on the project filesystem rather than
beside the result JSON in `results/`, which is what the `research-workflow` skill's sidecar
convention would say. A quarter of a gigabyte of pixels per dataset is an input to the score and
features stages, not a result anything reads, and `WORKFLOW.md` §11 already reserves `data/cache`
for exactly this. The JSON stays the unit of work and carries what defines the sample.

The two symlinks (`data/raw`, `data/cache`) are made by `scripts/link_storage.sh`, not by a rule.
A symlink is not a computation, the releases behind it are prior work no rule fetches, and a rule
that created it would be a rule whose output is a promise about someone else's filesystem. It is
the only setup step a fresh clone needs, and it is named in the README.

## 2026-09-11 20:05 — The probe, and a workspace that disappeared underneath it

Asked to continue, which the rule list puts at the `probe`. Wrote `priors/llm.py` (the boundary),
`priors/score.py` (the deterministic half: image encoding, reply parsing, the retry policies), the
`vlm:` config block, `rule probe` outside `rule all`, and 31 tests that hold all of it without
calling the service.

Mid-way through, the session's checkout was recreated and every gitignored path went with it —
`results/`, `.snakemake/`, the storage symlinks. Committed work and the uncommitted new files
survived. Recovery was `scripts/link_storage.sh` plus one workflow run; the 1.5 GB of sampled
arrays never moved, because they live under `storage_root`. Recorded in CHANGELOG.md as an
operational finding, because the same event during the scoring fan-out would destroy the response
archive, and the decision about where `results/score/` lives is the owner's.

The probe also contradicted a measured number in the plan (0.1 to 0.4 s per call, measured without
an image). WORKFLOW.md §4 now carries both measurements with their dates rather than the older one
alone; the hypotheses and the scope were not touched.

## 2026-09-11 21:20 — Runs move to the owner's checkout

Asked to make sure the workflow runs from the persistent filesystem. It was worth checking what
that meant: every path involved is on the same `/project/dane2` mount, so nothing here is about
disks. What is ephemeral is the agent session's *worktree* under the runner's `_sessions/` tree,
which is recreated without warning and takes every gitignored path with it — as happened earlier in
this session.

So runs move to `~/Code/textbook_priors`, the owner's own checkout, which was three commits behind
and carried one local `.gitignore` edit (`.snakemake/`, already committed here, and `.scratch`,
which was not). Rather than discard their edit to make the fast-forward possible, `.scratch` was
committed on the branch, which made their local change redundant and the fast-forward clean. The
session worktree stays the place to edit, commit and push.

Two consequences worth knowing. Manifests written from that checkout record `git_dirty: false`,
because it runs what was pushed rather than what is being typed. And since `data/raw` and
`data/cache` are shared symlinks, only one checkout may run the workflow at a time; the README
says so under "Where the workflow runs".

## 2026-09-11 21:45 — Thin classes: keep the sample, document the limit

The user asked whether stratifying was not simply cheap and analysis-neutral. It is cheap; it is
not neutral, and it is not one thing. The reply carried the measured allocations for both readings
of "stratify", which showed that the proportional one changes nothing and the equal-as-possible one
gains a factor of two to four while changing what each one-vs-rest column is measured against. On
that evidence the user chose to keep the sample as drawn and document the limit, which is now in
WORKFLOW.md §3 and CHANGELOG.md. Work continues on the scoring rules.

## 2026-09-11 22:00 — Go for the fan-out, and what the first chunk caught

The user said go for the 270-job fan-out. One chunk had been submitted first as a deliberate check
of the archive format, `protected()` and the gather; it came back holding gemma-4-31b's answers
under the primary model's file name, which is recorded in CHANGELOG.md as a finding rather than
here, because it changes what the code has to look like and not merely what was asked for. Fixing
it cost four explicit rules in place of a loop, a model wildcard so the command cannot disagree
with the file name, and a guard in the stage that refuses the mismatch before the first call. The
fan-out goes out after the replacement chunk verifies.

## 2026-09-12 09:05 — A fifth arm, asked for after the results: the bank in the prompt

"I know it's not clean but I want to try an arm who we ask for a classification zero shot that we
give all the concept information. Integrate this throughout."

Not clean is the right description and worth recording as the user's own, because it is the only
thing about arm D that needed a decision. The arm itself follows directly from the H2 result: the
permutation controls say the bank carries class information while arm B loses to arm A, so the
nearest-fingerprint readout is the suspect, and the cheapest way to test that without labels is to
let the model do the integrating. What is not clean is the timing — the arm was designed after the
numbers were in hand, so nothing it produces can be reported as a test of anything.

So "integrate this throughout" was read as: everywhere a pre-registered arm appears (the prompt
renderer and its tests, the fan-out, the classify and evaluate stages, the report's tables, figures
and macros, WORKFLOW.md, README), and nowhere a *hypothesis* appears. It is in `rule all` and in
the shared paired bootstrap, because an arm outside that bootstrap cannot be differenced against
the arms inside it; it is under `extensions` in `evaluation.json`, in a report section that opens
by saying it decides nothing, and in a table whose caption says post-hoc. The three `supported`
flags are computed from H1, H2 and H3 alone and were not touched.

Cost: 3,000 calls on the primary model, 30 chunks, the budget from 27,000 to 30,000. The existing
archive is untouched — arm D is 30 new files beside it, not a re-score.
