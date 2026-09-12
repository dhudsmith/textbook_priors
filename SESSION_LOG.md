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

## 2026-09-12 09:02 — Literature benchmarks, pulled and cited, not rerun

"I would like to pull results from the literature on these particular med mnist tasks and verify
and add them as benchmarks in the paper. I don't want to rerun those results. I just want to pull
the results from published works."

Read as: a third fixed input beside the concept bank and the pinned release (WORKFLOW.md section
4), not a rule that recomputes anything. `data/literature/benchmarks.yaml` pins the AUC and ACC
Yang et al. 2023 report (Table 3) for five fully supervised methods on these six tasks at 224
pixels — the same paper the concept bank already cites as its anchor, `yang2023` in
`references.bib`, reused rather than duplicated. Fetched the arXiv PDF, extracted Table 3's text
directly (not from memory) and cross-checked every value twice: once against the paper's own
across-dataset average table as a sanity check, once by re-reading the extracted text a second
time before committing it.

It is an extension like arm D — decides no hypothesis, WORKFLOW.md section 2 — but unlike arm D it
costs nothing to compute: no new calls, no new bootstrap, just one more table the `tables` rule
writes by reading the pinned file beside results/ already on disk. Placed inside `rule all` for
the same reason arm D is: cheap, and keeping a costless, hypothesis-neutral table out would only
cost the reader a second document. Added a schema test (`test_literature.py`) holding the file to
the datasets the workflow runs and to the bibliography, a loader in `priors/data.py` alongside the
bank and release loaders, and a `WORKFLOW.md` §10 entry recording the same reasoning here in
briefer form. `results/` does not exist in this worktree (README: agent sessions do not run the
pipeline), so the table's actual numbers are unverified beyond the pipeline test's synthetic
fixture; the owner's checkout will produce the real one on the next `tables` build.

## 2026-09-12 09:35 — Arm D landed, and two estimates that were wrong

The run finished at 09:34, exit 0. Asked mid-run to estimate the total time, I gave 08:45–08:55 and
it took until 09:34. The first estimate assumed contention would cost a factor of three or four on
the per-call latency; it cost a factor of thirty. The second, made after the first had visibly
failed, misread the job CPU counters — at 43 s per call, four minutes of real work rounds to under
one second of CPU, which is indistinguishable from a stalled process — and briefly concluded the
jobs were doing almost nothing. What settled it was one timed call through the same code path,
costing one call and five minutes, and it is recorded in CHANGELOG.md as a finding about the
service rather than here as an anecdote about the delay.

The arm the user asked for works and says something specific, also in CHANGELOG.md: arm B's readout
was lossy (D beats B on 4 of 6, recovering nearly all of pneumoniamnist's deficit), and the bank is
not information the model lacked (D loses to A on 4 of 6). It is reported post-hoc throughout, and
the three hypothesis verdicts were computed without it and did not move.

## 2026-09-12 14:40 — Analysis stops here; attention turns to the talk

"I think we have sufficient results for the talk. I will stop here on the analysis itself and
turn attention to structuring the talk itself."

The user attached the HPC Day 2026 agenda: the talk is the 1:15–1:45 keynote on Friday
2026-09-18 in McKissick Theater, directly after lunch, with a second keynote following and the
same speaker on the 3:35 generative-AI workshop panel. Asked for a review of everything in the
repository and an initial plan for a 30-minute talk, with scoping questions first rather than a
finished outline. Stated preferences, recorded because they shape every later draft: highly
visual; casual, simple, direct; deliberate repetition to tie ideas together; a story rather than a
data dump; this project as a running example for the principles, not as the subject.

Nothing in the workflow changes. Reviewed for the talk: WORKFLOW.md, TALK.md, CHANGELOG.md (every
entry), this log, README, CONCEPT_BANK.md, the Snakefile banners, the config, the three generated
figures and the report structure in the owner's checkout. The draft skeleton and the questions went
to the user in the session; the plan lands in TALK.md once the answers narrow it.

## 2026-09-12 15:05 — Stepping back: the question was about understanding, not substitution

"I think I was more interested in the question, 'to what extent do VLMs understand visual
features needed for medical image classification?' This is partly motivated by replacing labeled
data, but also simply out of curiosity on its own. It also leans toward interpretable machine
learning rather than merely classification performance."

Asked whether that needs a return to the workflow design or can be served by what exists, and
whether the scale ladder can be pushed higher. No rule changed. Two throwaway checks, neither
citable: a per-concept reading of the existing archive for three datasets (agreement of each
model's answer with the textbook's expected level, four-model agreement, single-concept AUC),
which showed the archive already holds the data for the reframed question at zero new calls; and
one tiny image call to each newer model on the service, which showed no open-weight
vision-capable model larger than gemma-4-31b is served (glm-5.3, deepseek-v4-pro and the
qwen3-30b instruct reject images; qwen3.6-27b, qwen3.6-35b-a3b and qwen3-omni-30b-a3b accept
them; the gpt-5 family is served but is closed and needs a different token parameter). The
assessment went to the user in the session; the decision is theirs.

## 2026-09-12 15:20 — Does thinking work, can we try an OpenAI model, and the service docs

Three directions in one turn. "Were we able to get thinking to work? Looking at the rcd docs, most
of these models should support thinking. Can you perform a simple test?", then "And does this allow
me to try openai model? Should we do that?" with a screenshot of the OpenAI credits page (10.00
project allocation, 648.79 in the shared pool), then the RCD *Available Models* page attached with
"Add it to the repo context".

The test was worth running and the answer changed a standing conclusion: thinking works, and the
reason it appeared not to was `max_tokens: 512` in this workflow's own config. Recorded in
CHANGELOG.md as a correction, with the per-model budgets. The user's reading of the documentation
was right and this project's inference was wrong.

Reading the documentation also replaced this session's earlier probe with the service's own
metadata endpoint (`/v1/models?full=true`), which reports per model the `images` feature, the
lifecycle tier and the `reasoning_effort` levels accepted. That is now `docs/rcd_llm_service.md`,
written as a reference with documented and measured claims separated, and pointed at from
CLAUDE.md, README.md and WORKFLOW.md §7. The OpenAI question is answered there and in the session:
the gateway models work with this key and this prompt, and the decision about whether to spend on
them is the user's, not taken here.

One thing deliberately not done. `priors/llm.py` carries the old thinking claim in its docstring
and is a `code()` input to all 300 protected score chunks, so correcting the comment marks the
whole 30,000-call archive stale. It is left for a deliberate edit plus `snakemake --touch` from the
owner's checkout, which CLAUDE.md's rule about the archive requires and a session that does not run
the workflow should not do by itself.

## 2026-09-12 15:45 — Scrub arm D, and propose a thinking arm and an OpenAI arm

"Can you propose how we could integrate a thinking arm and an openai arm, on more limited cases to
keep overall calls relatively low while still giving bite? Also, I want to scrub the confusing arm
D afterall from the entire repo."

The scrub was done in full and is recorded in CHANGELOG.md as a decision with its reason. Two
boundaries were drawn rather than assumed, both of which the user can overrule:

- `CHANGELOG.md` and `SESSION_LOG.md` say of themselves that they are appended and never
  rewritten, so arm D was *not* edited out of either. The removal is a new entry. Rewriting the
  record of what was found and how the work was directed would defeat the purpose both files
  exist for, and it is the one reading of "the entire repo" that the repo's own conventions forbid.
- The 30 `__directed__` chunks in `results/score/` were not deleted. They cost 3,000 calls, they
  are write-protected as principle 7 requires, and nothing in `rule all` reads them any more.
  Deleting an archive is deliberate, not incidental (CLAUDE.md), and removing an arm is not by
  itself a reason to destroy the evidence it produced.

The proposal for the two new readers went to the user in the session and is not yet written into
WORKFLOW.md, because its whole point is that a decision rule is fixed before any call is bought -
which means the user chooses the scope and the rule first. What arm D taught is the rule the
proposal is built around.

## 2026-09-12 15:41 — A human-readable txt render of each prompt

A separate session, asked in parallel: add a rule that saves a txt file of the prompt render for
each dataset and arm, for a person to read rather than parse. Added `render_prompts_txt` (target
`prompts_txt`, opt-in, outside `all`): it formats the JSON `render_prompts` already wrote - one
block per arm, each with its sha256 - rather than re-rendering from the bank, so the text is the
same artifact hashed into every score manifest and not a second copy of the prompt logic
(WORKFLOW.md §7). No manifest: nothing is computed here, so there is no run to record, and no rule
below it reads the output. Decides no hypothesis, so it stays out of `rule all` per CLAUDE.md's
rule about §2.

Built on 6186c16, this session's edit landed just as the arm-D scrub above was pushed to this same
branch from elsewhere - the working tree still carried the directed prompt and arm D's fingerprint
block when the local ref moved to that commit. `git status` showed it as a pending revert of every
file the scrub had touched; the fix was a `git stash push -u` (tagged, never a bare stash) to bank
the in-progress edit safely, landing cleanly on the real HEAD, then reapplying only the new rule -
one prompt fewer than first written, since arm D's `directed` prompt no longer exists to render.

This rule needs no shared state - only the committed bank files and `config/medmnist.yaml`, not
`data/raw` or `data/cache` - so it was safe to dry-run, lint and actually run from this worktree
without touching the owner's checkout; the six `results/prompts_txt/*.txt` files it produced here
are gitignored and do not persist, only the rule itself is committed.
