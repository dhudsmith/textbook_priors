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

## 2026-09-12 16:05 — H4 joins the hypotheses, at medium effort, and the build goes out

"Join the hypotheses in workflow. Let's do medium. Let's go!"

Both open questions from the proposal answered, so H4 is a hypothesis in WORKFLOW.md §2 and not an
extension, and both new readers run at `medium` — which also makes H4b a comparison at matched
effort rather than a comparison of models and effort together.

What the implementation actually settled, beyond what the proposal said:

- **A reader is a model plus an effort, and it reuses the arm vocabulary rather than adding to it.**
  The four ladder models are readers at effort `none`, so they join H4 by being subset to the same
  200-image prefix. No new arm letter exists, which was a deliberate reaction to arm D.
- **`priors/llm.py` changed, which marks all 270 protected chunks stale.** Resolved the way the
  conventions prescribe: `snakemake --touch` in the owner's checkout, not a re-score. Guarding that
  is a new test which pins the thinking-off request body field by field, so the module that claims
  to have produced the archive still sends exactly what bought it.
- **Running one chunk before twenty-four earned its keep again.** The gateway's reasoning models
  reject `temperature: 0` outright. The fix is to omit the field, and the consequence is a real
  limit on H4b now stated in WORKFLOW.md §2 and in the report: the frontier reader is the only one
  in the study whose answers are sampled rather than deterministic.

Also removed the arm-D reference from `evaluate_across`'s docstring, which had survived the scrub.

## 2026-09-12 17:40 — "What's left to run?" — and what the answer turned up

The user asked for a status. Answering it honestly meant measuring rather than reporting the job
count, and the measurement found a real risk: eleven thinking chunks in flight at 134 s per call
were on course to finish seventeen minutes inside a four-hour time limit, where overrunning writes
nothing. Cancelled and resubmitted under a cap of four, at a cost of about 200 spent calls. The
reasoning is in CHANGELOG.md; the numbers are in config and the profile beside the values they set.

Nothing about H4's design changed. This was an operations decision, taken on a measurement, of
exactly the kind the workflow exists to make visible.

## 2026-09-12 21:25 — The talk plan, fixed: workflow first, H4 as the follow-on

"I would like to take your original talk plan and basically keep it. I don't want the talk to
center around the hypothesis but the workflow, the basic spirit of the problem we're solving and
what the evidence says. ... with the frontier and thinking incorporated as additional follow on
'what if we added reasoning?' directions, to demonstrate the real research workflow in practice.
... Let's target 25 minutes with 5 minutes for questions."

Written into TALK.md §5 as a slide-by-slide table with minutes and the picture for each slide,
and §4 rewritten from a live demo to two recorded clips. The spine is the one proposed at 14:40:
cold open, old way and new way, the recipe, scenes where it nearly went wrong, what the evidence
says, close. Two changes from that draft: the scenes drop from four to three to make room, and a
new four-minute section carries today's H4 work as the workflow seen in practice over one day —
the standing claim overturned by a test, the rule written before the calls, the one chunk that
caught the temperature refusal, the wave measured and capped, and the result. Arm D appears for one
beat as the contrast: added after the numbers, removed the same day; H4 pre-registered and kept.

The follow-on section is written on the assumption, stated by the user, that the evening's pattern
holds — frontier no better, thinking conditional. The analysis chain was at 33 of 40 jobs when this
was written; if the final numbers disagree, §5 scene 6 is what changes.

## 2026-09-12 21:45 — The H4 chain lands; the talk's scene 6 stands

No prompt. The run launched at 17:42 under the cap of four finished at 21:40, 40 of 40, with
every thinking chunk complete and no cell flagged. The evening's pattern held under the real
estimator on the full 200 images, so TALK.md §5 scene 6 is not rewritten. One number moved in the
direction that justifies the preview having been marked uncitable: bloodmnist's thinking effect
shrank from a clear loss on 100 images to noise on 200. The finding is in CHANGELOG.md.

## 2026-09-12 22:30 — Embeddings, and the redirect to the service's own embedding model

"I would like to try using embeddings. Add this in in a principled fashion, run it, analyze the
outputs, and put it in the report. Think about how it could (or couldn't) be put into the talk."
Then, mid-design, with the RCD local-API documentation attached: "I want to use the LLM based
embeddings supported by the rcd llm service. Make sure you use that."

The first design read "embeddings" as a contrastive image-text encoder run locally (BiomedCLIP) and
had reached a written plan, a config block, a module and its tests before the redirect. None of it
was committed and all of it was replaced. The service's only embedding model, `qwen3-embedding-4b`,
is text-only, which forced a better design: the archive already holds every image described in the
bank's own words - the VLM's concept answers - so embedding those descriptions and the bank's class
fingerprints in one text space gives arm B's comparison with a learned distance in place of ordinal
arithmetic, on identical inputs. That isolates the readout more purely than a pixel encoder would
have, asks no VLM anything new, and costs no credits. It is H5 in WORKFLOW.md §2, with both decision
rules written before a single embedding was requested.

Two things the endpoint probe fixed: the space is anisotropic (unrelated anchor sentences at cosine
0.8, the two pneumoniamnist class names at 0.90), which is why only within-image ranking is read; and
the gateway models' metadata carries pricing after all, which answers the credit question of the
afternoon exactly (docs/rcd_llm_service.md).

One thing done on purpose: the embedding client lives in `priors/embed.py`, reusing `llm.py`'s key
loader and backoff, rather than in `llm.py` itself, so that adding an endpoint does not change the
provenance of the 294 protected chunks behind it.

## 2026-09-12 23:05 — "If the embed API can't take pixels my idea is a no go"

Checked at the wire rather than from the model listing: the embedding model rejects an
`image_url` input with a validation error, the three OpenAI embedding models are text-only, and
the vision chat models are not available at `/v1/embeddings` at all. Nothing on the service embeds
pixels. The user's idea as stated cannot be built on this service.

What exists at this point is the reinterpretation built in its place - H5, the same concept answers
and the same bank read by a learned text distance - pre-registered, committed as a plan and a data
layer, and run on one dataset for the hand-check the plan requires. That hand-check is recorded in
the session and not in CHANGELOG.md, because whether H5 continues is now the user's decision and
the numbers are a preview from a scratch script, not a rule. Work stopped here pending that
decision; nothing downstream of the embed stage was written.

## 2026-09-12 23:15 — "Remove all the nonsense not using pixels. Just rewind."

"This idea doesn't make any sense going through the fingerprints." Done. WORKFLOW.md,
config/config.yaml, the Snakefile, priors/stages.py, tests/test_score.py and the palmetto profile
are restored byte-for-byte to the commit before H5 existed; priors/embed.py and tests/test_embed.py
are deleted; 297 tests pass, the count before any of it. The one embedded dataset's outputs in the
run checkout are removed with the rule that made them: they cost nothing and nothing reads them.

Kept on purpose: the session-log entries above, because a record of how the work was directed is
worth most exactly where it records a dead end, and the service notes' two factual additions - the
embeddings endpoint's behaviour and the gateway models' published pricing - which are true whether
or not anything uses them.

The study stands where it stood at 22:09: four hypotheses, four verdicts, the report built. The
user's underlying idea - an image embedding from the same family of model that read the concepts -
is not possible on this service, and that is the finding, not a redesign of it.

## 2026-09-13 07:00 — Cleaning audit: everything the talk needs, and only that

"Now that the workflow is set and all results are in, perform a cleaning audit to make sure we have
everything needed and only everything needed for the talk workflow. Remove unused code files or
other extraneous things we made. Also, make sure all the results are in my primary directory ...
Don't do anything that would trigger running rules ... Don't add any new complexity. Just clean and
simplify. Make sure all documentation is up to date, clear, and concise. Make sure talk.md has our
clearest most up to date plan."

What the audit found, before anything was changed: every function in `priors/` is referenced, every
key in `config/config.yaml` is read by a rule, a stage or the smoke tier, and `~/Code/textbook_priors`
holds every result `rule all` names — 336 jobs from a clean clone, "Nothing to be done" there. So
there was no code to remove, and the constraint that nothing may rerun shaped what was touched: the
`priors/` modules and `tests/` are rule inputs, so their few stale docstrings ("three figures", "all
three prompt strings") were left alone rather than paid for with a `--touch` of the archive.

What changed: the documentation. The Snakefile header, README, WORKFLOW.md §6, §8 and §11, CLAUDE.md,
TALK.md, CONCEPT_BANK.md, the bank README, the service notes and the config comments all still said
three hypotheses, three or four figures, a smoke tier that did not exist yet, a thinking reader that
shared the primary model's cap, and an H5 that had been rewound. TALK.md now states that the H4
chain landed and scene 6 is not provisional, moves the thinking-effect scatter from "to make" to
"already generated" (`fig_thinking.png`), and holds the embedding dead end as a third alternate. Two
sentences in `report/report.tex` were wrong — "three hypotheses", and a literature paragraph that
still named arm D — so the PDF is the one output left to rebuild: a single local pdflatex job with no
calls, deliberately not run here because the instruction was that nothing should run. The owner's
checkout is otherwise at "Nothing to be done", on this branch.

Two things found and left for the owner. `results/prompts_txt/` holds six files from the
`render_prompts_txt` rule of commit d43a4d3, which the H4 commit an hour later silently dropped along
with its tests (a parallel-session clobber; the message never mentions it): restore the rule or
delete the files. And the 30 `__directed__` arm-D chunks stay in the archive as CHANGELOG.md's
removal entry asked — deleting 3,000 bought calls wants a deliberate word, not a cleanup pass.

## 2026-09-13 07:30 — "Restore the txt rule. Update and recompile the tex. You can delete the D results"

All three decisions the audit had left open, answered in one line. `render_prompts_txt` comes back
exactly as d43a4d3 committed it (a clean cherry-pick: rule, module function, entry point, six tests,
its README and WORKFLOW.md lines), and since `priors/stages.py` and `priors/prompts.py` were changing
anyway, the four stale module docstrings the previous entry had left alone are fixed in the same
commit. The 30 arm-D chunks, their logs and their benchmarks are deleted from the owner's checkout;
WORKFLOW.md §4 and §10 and a CHANGELOG.md entry say so. The checkout is then brought back to
"nothing to be done" with `snakemake --touch` and the PDF rebuilt, the only recomputation.

## 2026-09-13 08:05 — "Why don't I have a hypothesis that compares ... with zero shot?"

The owner asked why no hypothesis sets the concept regression (arm C) against zero-shot (arm A);
the answer - the plan paired arms by label budget, and H2's result made A the zero-label line that
matters after the fact - and the reading of the curve it implies are in CHANGELOG.md. They asked for
it in the talk without pre-registering it, so TALK.md scene 5 now names it as a reading of the
figure, not a verdict.

Then: how are arm B's class fingerprints determined, and should they be re-examined? They are set
from cited literature by the rule each bank file's header states - commit only where the sources
report the feature in a majority of the class or it is definitional, else `any` - with simulated
review and no clinician. A throwaway check in the session (scratch, uncited) compared every
committed fingerprint cell with the primary model's modal answer for that class on the labelled
pool, which arm B never reads: 391 cells, 70% agree, 93% within one level, organamnist worst at 56%.
The disagreements mix a fingerprint the literature may have wrong (monocyte nucleus-to-cytoplasm
ratio, lymphocyte size, immature-granulocyte chromatin - the last already flagged in the bank README
as resting on an unsourced floor) with features the model does not see at 224 pixels (opacity on
half of pneumoniamnist's pneumonia films). Whether to make that check a rule, and whether an expert
pass follows, is the owner's call; nothing in the bank or the workflow changed.

## 2026-09-13 08:20 — "Expand the full analysis to all 12 MedMNIST. Follow it through from start to finish."

"I know this is a long request that will involve many calls. Proceed until complete and documented."
The talk version's six datasets become the twelve 2D benchmarks, the whole workflow run to the
report. What the build settled before a call was bought:

- **Eight release files were on disk; four were the full branch's half-finished byte-range
  segments** (chestmnist, organcmnist, organsmnist, tissuemnist). The full branch's resumable fetch
  script and rule come back as `rule fetch`, scoped to files not on disk, with the sizes and MD5s
  the release description now carries for all twelve.
- **Samples cap at the official split** (breastmnist 156 and 546, retinamnist 400 and 1080) and the
  curve drops the points a pool cannot reach; nothing else changes for the ten datasets that do not
  cap.
- **chestmnist runs in arms C and P alone**, scored by the primary model on the concept prompt only:
  a nearest fingerprint and a distribution over class names are not defined over fourteen
  co-occurring findings. Its regressions are one-vs-rest per finding with the L2 strength chosen by
  out-of-fold AUC, because a finding present in two percent of films makes accuracy blind, and its
  AUC is the package's mean over findings. It joins H1's count and nothing else.
- **retinamnist's classes are the digits 0 to 4**, so the zero-shot listing glosses each with its
  ICDR grade; the JSON keys stay the release names and the six archived datasets render byte for
  byte as they did, which a test now pins by hash.
- **The decision rules become one level, alpha = 0.05**, the full branch's own pre-registered
  thresholds restated: 6 of 6, 9 of 11 (H2 to H4, which exclude chestmnist), 10 of 12 (H1). The
  six talk datasets' verdicts were known when this was written and the six new ones' were not;
  WORKFLOW.md says so rather than pretending otherwise.
- **Budget**: 51,718 calls in 521 chunks, of which 22,318 in 227 are new; 1,000 of those go to the
  gateway reader, about four dollars at flex.

378 tests pass, including an end-to-end run of the multi-label path on a toy dataset; the DAG from a
clean clone is 616 jobs.

## 2026-09-13 10:15 — Twelve datasets, start to finish, complete

The expansion asked for at 08:20 ran to the report in under two hours of wall clock: four fetches
in a minute each, six samples, 227 chunks in 66 minutes on an uncontended Sunday service, the
analysis chain for twelve datasets in 25 minutes, and the owner's checkout back at "Nothing to be
done". Mid-run the user asked for the hypothesis statements to be adjusted for the expansion;
WORKFLOW.md §2 now states each rule over the datasets it covers at one level (10 of 12, 9 of 11),
says which six verdicts were known when it was written, and the report reads those counts from
macros. The six original datasets reproduce exactly under the extended code, checked against a copy
of their evaluate outputs taken before the run. Findings are in CHANGELOG.md: all four hypotheses
unsupported on twelve, H2 flipping on the tasks the model cannot name, H4a's pattern holding on
eleven. TALK.md's scene 5 and scene 6 carry the two sentences that changed.

## 2026-09-13 10:40 — "Hypothesize that P + C beats P. Register the hypothesis, then run it and integrate it"

Asked alongside a question about whether the study is publishable (answered in the session, with the
literature search behind it). The hypothesis is the one H1 does not answer: H1 shows the concept
scores cannot replace the pixel features at equal labels, which is not the same as showing they add
nothing on top of them.

Registered as **H5** before any of its numbers existed, and this commit is the evidence: WORKFLOW.md
§2 states the arm, the primary grid point (n = 50, from `config.yaml h5.n`) and the rule (10 of 12,
the same alpha every other rule uses); the code, the tests and the report section are all in place;
arm C+P has never been fitted. The numbers arrive in the next commit.

What separates H5 from arm D, which was removed for being post-hoc, is not that H5 is uninformed by
the earlier results — it exists precisely because H1 failed — but that the comparison it makes had
never been computed when the rule was written. It also costs no calls: both feature blocks are
already on disk, so the whole test is a re-analysis. WORKFLOW.md §2 and §10 say all of this in the
plan rather than only here.

One limit is registered with it rather than discovered later: a dozen concept columns join 512 pixel
columns under a single L2 penalty, so a null means "no detectable gain under the classifier every
other arm uses", not "no information".

## 2026-09-13 12:25 — A second session on the same task, and the damage it did

A second Claude session was given the P + C prompt at 11:45 without the owner intending two to run
at once, and did not know the 10:40 session existed. It built the same arm (as `PC`, with a
permutation control) on its own branch, `claude/p-plus-c-hypothesis-57k952`, then at 11:52:34
switched this checkout onto that branch to run, while the 10:40 session's chain had been submitted
from here a minute earlier. Three things followed, each now undone; the owner's "clean up any
damage you caused" at 12:05 directed the repair.

- **Five classify outputs were written by the wrong code.** SLURM jobs read the working tree when
  they start, so of the twelve classify jobs the 10:40 run submitted, five (bloodmnist,
  breastmnist, octmnist, pneumoniamnist, retinamnist) imported the other branch's `stages.py` and
  wrote arm `PC` arrays where this branch's evaluate expects `CP`; their evaluate jobs failed with
  `KeyError: 'CP__n50__seed0'`. The manifest's `git_commit` field named the culprit in each file,
  which is what it is for. The five outputs were deleted at 12:08 so the next run recomputes them;
  the seven written by this branch's code stayed.
- **The checkout was switched back at 11:55:30**, and that switch, like the first, rewrote
  `stages.py` with a new mtime.
- **A `snakemake --touch` in the second session's worktree reached the shared cache.** `data/cache`
  is a symlink onto project storage in every checkout, so touching `sample` and `features` there
  at 11:58 bumped the mtimes of the twelve sample arrays and the twelve feature arrays this checkout
  reads. Together with the `stages.py` mtime, that made every archived chunk look stale: the next
  `snakemake all` from here planned 574 jobs and submitted 127 scoring chunks before the second
  session killed it at 12:17 and cancelled the jobs. None had started; all 521 chunks are on disk
  with their contents untouched. The 10:40 session then ran the documented repair, `--touch score
  features prompts`, and a dry run at 12:20 shows the 29-job analysis chain and nothing above it.

The second session also cancelled its own worktree run (12 classify jobs, nothing written here) and
left its branch on origin as a duplicate implementation for the owner to keep or delete. The lesson
is the one README already states - one checkout runs the workflow at a time - with a corollary the
symlinks make sharp: a `--touch` in any checkout is a `--touch` of the shared cache for all of them.

## 2026-09-13 12:45 — H5 run and integrated, after a concurrent session disturbed the run

The hypothesis registered at 10:40 ran and is **supported**: 11 of 12, p = 0.0032, every winning
interval clear of zero, median gain 0.007 AUC. Integrated into the report as its own section, a
table, a figure and seven macros; CHANGELOG.md carries the reading, and the literature position the
publication question in the same message prompted.

Three launches were aborted first, and the entry above this one, written by the second session,
explains why: it switched this shared checkout onto its own branch mid-run, and its `--touch`
reached the shared cache. My first diagnosis of the five wrong classify outputs was a stale NFS
bytecode cache. That was wrong, and the manifests said so plainly - each recorded the other
branch's commit - which is a small lesson worth keeping: the manifest exists to answer "what code
wrote this", and it should be read before a theory is formed.

Checked before standing behind the numbers: all twelve classify results, all twelve evaluate
results and evaluation.json record commit 383693e, and `git diff 2a4a017 383693e` touches only
SESSION_LOG.md - so every H5 number was produced by code byte-identical to the pre-registration.

## 2026-09-13 14:25 — An accuracy pass over the report, and the prompts as an appendix

Asked to take a pass through the report for accuracy, add anything specific to the analysis that
had been left out, add appendices showing the prompts, and make sure arm C+P's fusion is described.

The Methods section was one paragraph covering five arms; it is now seven subsections and states
what the run actually did rather than what it broadly did. What was missing and is now in: the call
settings (temperature 0, the thinking-off switch, 512 tokens, chunks of 100, the one content retry
at a doubled budget, four transport retries, the 120-second timeout, every attempt archived); the
PNG data URI and that the image is not resized; the concept-vector mapping with its scale-length
consequence and the missing-indicator rule; arm A's zero-fill for an omitted class and arm B's
`-1` for an empty overlap; the cross-validation criterion, which is out-of-fold accuracy for the
single-label arms and out-of-fold AUC for the multi-label one, and that the grid is scikit-learn's
inverse penalty C rather than a penalty; the largest-remainder nested subsets and their class floor;
both permutation controls in their exact form; the shared bootstrap's mechanics and why H4 needs its
own; n_B's ordinal coding; and H4's reader settings, including the 2048/4096 budgets and the
gateway's discounted tier.

**Arm C+P's fusion now has its own paragraph and its own generated table.** Concatenation with the
concept block left of the pixel block, standardised column-wise on the same n labelled images, one
shared L2 penalty over the whole matrix, no per-block weighting, no selection, no reduction.
`tables/features.tex` prints the widths per dataset so the claim "its width is exactly their sum"
is checkable rather than asserted, and it exposes something the prose had not: only organamnist and
organsmnist carry any missing-indicator columns, two each, so the concept block is otherwise just
the concepts.

**The appendix is generated, not pasted.** `appendix_prompts` reads `results/prompts/<dataset>.json`
- the same artifact each score job read and every response manifest hashes - and prints both
prompts for all twelve datasets verbatim with their SHA-256, about 32 pages. Lines longer than 92
characters are hard-wrapped because this cluster's fancyvrb is v2.7a and has no `breaklines`; a test
holds the wrapper to changing whitespace and nothing else, so the printed hash stays checkable
against the JSON, and the appendix says so.

Building it needed the documented dance again: editing `tests/` invalidates the smoke marker every
rule depends on, so a plain `snakemake all` planned all 521 scoring chunks. Ran smoke, touched
`evaluate score features prompts_txt`, then built the four report jobs. 379 tests pass.

## 2026-09-13 20:05 — Arm C+P on the learning curve, and a sampled-image appendix

Two asks. First, put H5's arm on the plot of performance against number of training samples. It is
there now as a dashed line with square markers, and deliberately without a confidence band: it
tracks arm P within a few thousandths on every dataset, so a third ribbon would overlap arm P's
almost exactly and read as a wider red band rather than a second series. The interval that decides
H5 is on the paired difference and already has its own figure.

Two things came out of drawing it that were not asked for and are worth recording. The palette
validator rejected the purple the H5 forest plot had been using: `#9467bd` sits at Delta E 1.7 from
arm C's blue under protanopia and 14.2 for normal vision, which is not a distinguishable pair. Arm
C+P is now `#762a83`, which is 11.1 from that blue under deuteranopia, 16 or more from every other
line on the panel, and 8.6:1 against white for print; the reason is a comment beside the palette so
nobody re-picks by eye. And the six-entry legend no longer fitted inside a panel — it was covering
pathmnist's arm-B and arm-A rules and its y tick labels — so it moved below the figure.

Two pre-existing pairs still fail the same validator and were left alone, because changing them
would repaint five figures and the talk: arm B green against arm P red (Delta E 3.9 deutan) and the
two dotted reference lines, grey against brown (11.3 normal). Both carry line style as a second
encoding, which is the condition under which the guidance allows it.

Second ask: an appendix of sample images from each dataset for each class. `figure_samples` writes
one montage per dataset from the same cached sample arrays every arm was scored on, six images per
class in sample order, each row labelled with how many of that class the seeded sample holds; a
grey cell means the sample holds fewer than six. The multi-label task's rows are findings. It makes
the study's thin-class caveat visible rather than stated: dermamnist's vascular lesions are five of
500, and chestmnist has one hernia, four pneumonias and six fibroses in the whole sample, which is
most of the explanation for its 0.557.

The report is now about 60 pages and 14 MB. Same build dance as before: smoke, touch, four jobs.

## 2026-09-13 20:40 — Four questions about the frontier reader, none of them bought

Asked whether the frontier model might be overthinking, whether to try luna, terra and sol at the
lowest effort, whether the API offers `astra`, and whether the credits stretch to it.

Answered from the archive and the service metadata rather than by running anything, because the
last of those questions is the one that decides the first three and I cannot read the balance: the
service has no credit endpoint and the figure lives only in its UI. The overthinking evidence, the
dermamnist concept-collapse signal and the corrected costs are in CHANGELOG.md; the model family,
the pricing table and the sweep costing are in `docs/rcd_llm_service.md`, which also loses an
estimate that was half the true figure.

Nothing was pre-registered and nothing was scored. If the owner wants the sweep, the design that
follows from the evidence is two separate questions rather than one: effort within the frontier
model (terra at `low` against terra at `medium`, which is the direct test of the overthinking
hypothesis and re-reads H4b's step without the confound), and capability at matched low effort
(luna, terra, sol). They would want the H5 treatment — rule and config committed before the calls.

## 2026-09-13 21:00 — "Test the reasoning level idea on terra. Test the model capabilities at low reasoning for Luna, terra, and Sol"

Approved after the costing of the previous turn, and with the caveat standing that the credit
balance cannot be read from here — the service has no endpoint for it, so this is the owner's
approved spend rather than a verified one.

Registered as two hypotheses rather than one, because they ask different questions of the same
calls. **H6** holds `gpt-5.6-terra` fixed and lowers the effort from `medium` to `low`, which is the
direct test of whether H4b measured a capability or an operating point; it is one-sided toward the
overthinking reading, and the count the other way is reported beside it. **H7** is a capability
ladder inside the family at matched `low` — luna, terra, sol — ordered by price, because nothing
public orders these closed models by size and the plan says so rather than implying a parameter
step.

This commit carries the rules, the three readers, the evaluate steps, the across-dataset verdicts,
the table, the macros, the report sections and the tests, and no numbers: not one of the 6,468
calls has been bought. The budget test caught the change and now pins 58,186 calls in 587 chunks,
up from 51,718 in 521.

Next, before the fan-out: one chunk per new reader, which is standing practice here and matters
more than usual this time, because the service metadata lists no reasoning levels and no image
support for any gateway model — it omits images even for terra, which demonstrably accepts them —
so whether luna and sol can see an image at all is unverified until a call is made.

## 2026-09-13 22:15 — H6 and H7 decided

Both ran to the report in about seventy minutes and cost $38.76 at list, $19.38 at `flex`, under the
$53.59 / $26.79 quoted before the owner approved it. Findings are in CHANGELOG.md.

Short version: **H6 not supported** — lowering the frontier model's effort helped on 3 of 11
datasets and hurt on 8 — but the one interval clear of zero anywhere in it is dermamnist at +0.128,
which is the dataset the archive had singled out before any call was bought, from a concept the
model was collapsing to a single answer. The general overthinking claim is wrong here and the
specific one was right. **H7 supported**, 9 of 11, p = 0.0327: the price ladder inside the closed
family separates cleanly where H3's open-weight parameter ladder found nothing at all.

Two things recorded against H6's null rather than glossed: the `low`-to-`medium` step is a small
lever on this model (109 against 132 median reasoning tokens at the probe, where the local model's
`none`-to-`medium` step is 112 against 986), and the gateway rejects `minimal`, so a wider step
cannot be bought here. The null is about that lever.

The probe before the fan-out earned its place again: it confirmed luna and sol accept an image at
all, which the service metadata could not answer, and it is where the small-lever measurement came
from.

## 2026-09-13 22:25 — A hyperlinked contents page

Asked for one, and the report had grown to seventy-four pages, so it earned it. Three things had to
change beyond adding `\tableofcontents`.

Every results and methods heading was a starred `\subsection*`, and starred headings never reach a
contents page, so a naive ToC would have listed six top-level sections and none of the seven
hypotheses — the entries a reader actually wants. They are unstarred and therefore numbered now,
which also makes them cross-referenceable; nothing else about them changed. The bibliography
section was starred for the same reason and is now appendix C.

The sampled-image appendix had no headings at all, only figures, so its generator now emits a
subsection per dataset. Both appendices are navigable dataset by dataset: prompts under A, montages
under B.

`hyperref` was already loaded but its colour options need a colour model, which failed the first
build with `Undefined color model HTML`; `xcolor` is loaded now and the link colour is a named
navy. PDF bookmarks are on and numbered. `report/report.toc` joined the gitignore beside the other
things pdflatex leaves behind.

## 2026-09-13 23:05 — Visuals for H6 and H7

Two figures, each shaped by what its hypothesis has to show rather than by reusing the forest plot
the report already has twice.

**H6 is a dumbbell**, one row per dataset, the two efforts joined, sorted by the higher effort's
reading, with the difference and its interval printed at the right and only the clear intervals
drawn solid. A forest plot of differences alone would have hidden the finding: what makes
dermamnist interesting is not only that its difference is large but that it sits at the bottom of
the AUC axis, and the sort makes the two facts one picture. The other ten datasets are visibly
short pairs clustered to the right.

**H7 is a ladder drawn deliberately like H3's**, one line per dataset across luna, terra and sol,
because the pair is the finding: the same picture over an open-weight parameter ladder found no
trend and this one rises on nine of eleven. A reader can put the two figures side by side without
translating between styles, which they could not do if H7 were drawn as a forest plot.

Three defects fixed on the way. `figure_ladder` was using matplotlib's default ten-colour cycle
over twelve datasets, so the eleventh silently wore the first's colour; there is now a stable
twelve-hue table with distinct markers, shared by both ladders, so a dataset keeps one appearance
everywhere and no two share both colour and marker. And both new legends sat on top of data in
their first render — H6's over the best-read dataset's pair, H7's over retinamnist, which is the
largest single effect the figure has — so both moved below the axes.

The first rebuild attempt is worth recording: editing `stages.py` cascaded into the archive again
and Snakemake tried to re-score a gemma chunk. The `protected()` output refused it with a
`ProtectedOutputException`. That is principle 7 working as designed, and it caught what the touch
discipline had missed. No calls were spent; the archive is intact at 587 files.

## 2026-09-14 06:55 — "Clean up hanging checkouts or branches that were never merged in"

The ask: one clean lineage for the talk, everything accounted for, and results that are always in
the owner's checkout rather than somewhere a future session left them. Three things were wrong, and
none of them was a branch.

**The results were already only in `~/Code/textbook_priors`** — 587 archive files, twelve each of
sample / prompts / prompts_txt / scores / features / evaluate, twenty-four classify, twenty figures,
twelve tables and the 15M PDF. The session worktree held no results at all. So nothing had to be
moved; what had to change is that nothing can put them anywhere else again. `config/config.yaml`
now carries `run_root: ~/Code/textbook_priors`, and the Snakefile refuses to **execute** anywhere
else, naming both paths in the error and pointing at `PRIORS_ALLOW_ANY_CWD=1` for anyone who means
it. Reading the workflow elsewhere is untouched, deliberately: a dry run, `--lint`, `--touch` and
`--unlock` from a session worktree are all legitimate and all still work. Tested both ways from the
worktree before committing. The guard is module-level and touches no rule's shell line, so it
triggers nothing: the checkout still dry-runs to "Nothing to be done".

**The branches.** Eight `claude/...` heads existed on the remote. Six were fully contained in the
talk branch — the runner opens one per session whether or not the session diverges — and two carried
unique commits, both superseded:

| ref | head | what it holds |
|---|---|---|
| `claude/concept-bank-subagents-io2xt9` | 8c884c4 | contained; also where `main` sat |
| `claude/med-mnist-literature-benchmarks-3wcw8e` | ac2cee4 | contained |
| `claude/workflow-validation-simplify-wz992z` | 1863cf3 | contained |
| `claude/talk-workflow-cleanup-qmi9iy` | 163663a | contained; this session's own |
| `claude/llm-zero-shot-image-variants-asnp2y` | df40793 | 2 commits, WORKFLOW.md only: the zero-shot split and the description-embedding arm, both dropped from the plan on 2026-09-09 |
| `claude/p-plus-c-hypothesis-57k952` | de0e6cb | 1 commit: a second session's arm PC, superseded by the H5 arm C+P that shipped |

Neither unmerged branch holds a result file; both are plan exploration that the shipped plan already
answers. They are kept as annotated tags — `retired/llm-zero-shot-image-variants` and
`retired/p-plus-c-hypothesis` — so the commits stay reachable and findable by name, and the branch
list stays short, then deleted as branches. Deleted too are the three contained session branches and
`claude/textbook-priors-talk` itself, all of which `main` now carries. What remains is `main`,
`claude/textbook-priors-workflow-2kdgap` (eaa7994, which WORKFLOW.md §10 cites by name for the wider
plan that was cut), and `claude/talk-workflow-cleanup-qmi9iy` — the branch the runner assigned this
session, sitting on the same commit as `main` and safe to delete once the session is over.

**`main` is the trunk again.** It had sat at 8c884c4 since the concept-bank work while every later
commit accumulated on the talk branch; it fast-forwards to the talk head with nothing to merge and
nothing lost. `origin/HEAD` now points at it. CLAUDE.md tells the next session the rule that keeps
this true: commit on whatever branch the runner hands you if you must, but fast-forward `main` onto
the same commit and push both before the session ends, and retire superseded exploration as a tag
rather than leaving a head behind.

Three stale documentation claims fell out of the audit and are fixed: WORKFLOW.md §2 still opened
"Four" hypotheses, CLAUDE.md still said four, and the README still described four arms, four
hypotheses and a 616-job clean-clone DAG. The DAG is 665 jobs from a clone (677 forced, including
twelve fetches), 587 of them the scoring fan-out — counted from `-n --forceall`, not estimated.

## 2026-09-16 23:25 — "The talk as a website: science as the spine, reproducibility as callouts"

The talk is no longer a deck. Asked for a science talk about the medical-imaging-with-LLMs study
with commentary throughout about reproducible research assisted by AI, delivered as a scrolling
website with interactive elements, a QR code at the top so the room can follow on its own devices,
and hosted on GitHub Pages. That inverts `TALK.md` §5: the science is the talk, and the
reproducibility-with-AI argument rides on it as on-slide callouts of three kinds — a blue
**Principle** (a `WORKFLOW.md` §5 principle stated as the failure it prevents), an amber **Near
miss** (something that nearly went wrong and *what caught it*, dated to `CHANGELOG.md`), and a
violet **Agent note** (what the agent did, what the human had to do, and the understanding debt it
left or repaid, timestamped to this file). The plan is `talk/PLAN.md`; `TALK.md` now points at it
and keeps §5 as the earlier deck plan.

Three things this changed about the work rather than the prose. **The site hand-types no number.**
`talk/scripts/export_talk_data.py` reads `results/evaluation.json`, the twelve evaluate records,
the config, the pinned release, the literature table, the concept bank, the rendered prompts, a
sample of the write-protected response archive and the cached test images, and writes a snapshot
into `talk/public/`, which is committed — the one deliberate exception to "results are never
committed", because the site is built on GitHub's runners where `results/` does not exist. Every
file it writes carries the run's `git_commit`, the export date and the files it was read from, and
the export checks three of its own numbers against `report/tables/*.tex` before it exits (H1's
pneumoniamnist C−P at n = 50, H5's wins, H7's sol−luna on retinamnist), so the site and the PDF
cannot quietly be different runs. Two fields are hand-authored and both say so in the output: each
session-log entry's kind, and the contention measurements transcribed from `CHANGELOG.md`
2026-09-12.

**The export is a rule.** `rule talk_data` declares those inputs, sits outside `rule all` and in
`localrules`, in the style of `prompts_txt`: opt-in, decides nothing, feeds no rule below it. Its
script lives under `talk/` rather than `priors/`, so it is a code input of no result and adding it
reruns nothing — the dry run plans exactly one job, `talk_data`, and no `score_`, `classify` or
`evaluate` line.

**The snapshot is public, so it says what it does not carry.** The owner-only key path was already
dropped from every manifest; the compute node's hostname is now replaced by the cluster, since the
project names Palmetto2 in its README and has never published a node name. Both redactions are
listed in each file's `provenance` block and printed beside the manifest on the page itself,
because a snapshot whose point is that it can be checked has to say where it differs from the
archive it came from.

The site is Vite + React + TypeScript with D3 for the marks, one scrolling page of twelve sections,
a progress rail, presenter mode on `p`, a dataset picker whose choice is remembered all the way
down, and light and dark by `prefers-color-scheme`; arm and dataset colours are `priors/report.py`'s
own, so a listener who has seen the PDF recognises them. It is deployed by
`.github/workflows/pages.yml` from `main` to https://dhudsmith.github.io/textbook_priors/, with
`claude/**` pushes building but not deploying. A `?static=1` query freezes the page in its final
state — data read in one pass, no entry animation, images eager — which is how the headless
screenshots that checked this page were taken.

## 2026-09-17 12:30 — Three reviews of the talk site, implemented

The user had the talk website read by three reviewers — one for the visuals, one for the text, one
for the presentation flow — and handed the agent their merged, prioritised change list to
implement, with the editorial calls already made and a short list of things not to break.

The blockers were the ones that would have shown in the room. The premise lede named the wrong
weekdays and five day-slots for four days, and the weekday names left the copy rather than being
corrected. The keyboard bound `Space`, `PageDown` and every arrow to a section jump and swallowed
them all, so a presentation clicker moved one and a half to three screens a press and nothing
scrolled a beat; those keys are now left to the browser and section jumps wear `]` and `[`.
Presenter mode hid every `.note`, which took the H5 slider's guard, the verdict-board key and the
ceiling takeaway off the projected page; it now hides only what carries `presenter-hide`, and
scales the root rather than the body so chart ticks grow too. The H3 ladder drew one line per
dataset across an axis that interleaved the two model families, so three of every four segments
joined a qwen model to a gemma one while the note beneath said the families must not be compared —
the axis is now ordered family first and each line is drawn as two paths that do not cross the
divider. The reader chain's nine model ids overprinted each other and the caption; the axis now
carries a stem plus an effort and the bottom margin is computed from the longest one.

The rest followed the list: the refrain moved to one instance each at the open, the middle and the
close; H1 leads with its verdict and defaults to two series with the others behind the legend; the
close's seven-identical-bars chart became two stat tiles and a list; the contention chart became
paired bars, because two measured points joined by a line assert a continuum nobody measured; both
eleven-line ladders now colour and label only the datasets that move most and grey the rest; AUC,
probe, reader and chunk are glossed where they are first used; one name is held per arm; charts
keep a floor width so a phone scrolls them instead of squeezing them; and the page settled on two
content widths. The export script was changed for two of its items only — timeline leads are
stripped of Markdown, cut at a sentence boundary and sorted by timestamp — and re-run, so
`timeline.json` is the one data file that moved.

## 2026-09-17 16:45 — The opening re-cut: the method is the talk, the study is the demonstration

The user began a batch of copy edits on the talk site, delivered in conversation rather than as
review comments on a branch, and the first batch moved the talk's centre of gravity. The title
became *Reproducible Scientific Computing with AI Coding Agents*: the subject is now the method,
and the medical-imaging study is what demonstrates it. The tagline had been a list of the study's
apparatus — twelve benchmarks, five arms, seven hypotheses — and was asked to carry the
proposition instead, stated as the audacious and possibly controversial thing it is: hand the
machinery of a computational study to a generative agent and keep only the part that makes it
science. The objection the room will raise is now named in the tagline rather than left implicit.

The numbers needed a context they had lost. An intro was added between the tagline and the stat
tiles that starts the project in front of the audience — *a project that had been sitting at the
back of my mind* — poses it as "Can out-of-the-box vision-language models classify medical
images?", and says the answering of it was largely automated, so that four days, 58,409 calls,
twelve datasets and 379 tests read as the demonstration's cost rather than as credentials. No
number entered `content/index.ts`: the tiles still assemble them from the snapshot.

The study's own question — whether textbook knowledge stands in for labelled data — was held out
of the title band rather than deleted. Two questions under one header read as a non-sequitur, and
the user asked to leave that line for a later batch; it stays in the content file with a comment
saying why it is not rendered.

The user also asked for a workflow diagram of the code structure. `WorkflowDiagram` draws the
fixed inputs, the one workflow and the generated outputs left to right, with the seven stages and
their job counts inside the Snakemake box. Its point is the distinction the talk depends on and
the room will not make unaided: two different machines wear the word AI here. The coding agent is
an author — dashed violet arrows to the concept bank, to the workflow and to the report and this
page — while the VLM under study authors nothing and hangs below the workflow as a service the
score stage calls. Solid arrows are data, dashed arrows are authorship, and the legend says so.

The diagram was checked by rendering the component headlessly with `react-dom/server` and
`rsvg-convert`, there being no browser on the runner. The first render showed what a build cannot:
a missing human-to-agent arrow, two dashed arrows struck through the column headers they crossed,
and a twelve-pixel gap for a double-headed arrow. All three were fixed before the push.

The premise section now opens on ground the title band has already covered. Grafting the two
together is the user's next batch.

## 2026-09-17 17:05 — A byline under the title

The user asked for their name and department under the talk's title: D. Hudson Smith, School of
Mathematical and Statistical Sciences. Set as a `.byline` under the header and above the tagline,
the name in full ink and the school quieter beneath it — stacked rather than run together on one
line, because the school's name wraps awkwardly beside a person's on a phone. The eyebrow above
the title still names the venue.

## 2026-09-17 17:40 — Presenter mode bulletises the prose

The user asked presenter mode to crunch the longer prose blocks into a few skimmable bullets:
points the room takes in at a glance, and a reminder of the speaker's own flow, with the sentences
said out loud rather than read off the wall.

Each of the twelve prose blocks in `content/index.ts` gained a `bullets` array beside its `body`,
written from that body rather than derived from it — two to six lines, ordered as the paragraphs
are, so the list doubles as the running order. A `Body` component renders the paragraphs on the
page and the bullets when projected; a block with no bullets projects its prose unchanged, so a
section can never be silently blanked by a missing list. Sections that split their prose across a
figure (H2, H3, H4) carry the bullets at the first authored paragraph, and H3's stray paragraph,
whose content is now its first bullet, is marked `presenter-hide` rather than projected twice.

Computed sentences were deliberately left alone. The verdict paragraphs in H2, H3 and H4 assemble
their numbers from the snapshot, and those numbers are the result: the projected page keeps them
verbatim and bulletises only the reasoning around them.

Verified by rendering the sections headlessly in both modes — three bullet lists and fourteen
paragraphs projected, against twenty-one paragraphs and no lists on the page.

## 2026-09-17 18:20 — Presenter mode becomes a deck

The user raised the ask: in presenter mode the site should read almost as slides — one main section
per screen, text collapsed to bullets, the visual and its text together, the title prominent,
everything in chunks sized for delivery — while the ordinary scrolling website is untouched.

The mechanism is one component and a block of CSS. `Slide` wraps a run of a section's content and
is `display: contents` on the page, so its boxes vanish and the scroll flows exactly as it did
before slides existed; in presenter mode it becomes a 100vh grid with `scroll-snap-align: start` —
title across the top, prose left, figure right. Because the page already left `Space` and
`PageDown` to the browser for the clicker, snapping is what turns one press into one slide; no key
handling changed. Thirteen sections became thirty-one slides, continuations repeating their title
quietly as a `conthead` div rather than a second `h2`, which would have stuttered in the page's
heading outline.

Two bugs were found by looking rather than by building. A global `scroll-padding-top: 4rem`, there
so an anchored heading clears the phone's sticky rail, offset every snap by 68px, so each slide
showed a strip of the one before it; presenter mode now zeroes it. And a centred text column
clipped at *both* ends when its content overran, silently eating the lede at the top of the
tallest slides — `justify-content: safe center` was written for exactly that and fixes it.

The runner has no browser, so one was installed: headless Chromium under Playwright, driving the
built site from `vite preview`. A script walks all thirty-one slides, screenshots each at
1920×1080 and reports any whose text or figure column overflows the viewport. The first pass
failed six slides, all of them sections whose chart was still stacked under the bullets rather
than in the figure column; moving those charts into the figure slot, shortening H1's learning
curve when projected, and hiding two footnotes left three, none of which loses content — a figure
taller than its column scrolls rather than clipping. The one genuinely tall slide is the archived
call, which is a thing to explore rather than a thing to read from the back of a room.

## 2026-09-17 20:10 — Replace the four-day strip with a waterfall of who did the work

The user found `TimelineStrip` inscrutable and asked for a waterfall instead: two bands over the
same axis, project-lifecycle activity in one and human against AI against supercomputer time in
the other, to convey that one person can direct an enormous amount of machine work and that the
hard part is understanding and validating what comes back.

The first job was whether the repository can support that picture without inventing anything, and
the answer is half yes. The machine band is solid: every stage writes a manifest carrying
`written` and `wall_seconds`, so 662 jobs are 662 intervals — 290.3 h of job time, run inside
13.2 h of wall clock at a mean of 21.9 jobs in flight, against 4.7 h of CPU in
`benchmarks/**/*.tsv`, because the score jobs spent their wall time waiting on a shared model
service whose GPU time this project never meters.

The human band is not solid and the chart says so. Nothing in the repository separates the person
from the agent: `SESSION_LOG.md` timestamps a prompt, not a worker, and the gaps between prompts
(median 35 min, longest 5h40m) are equally consistent with thinking, with the agent building and
with lunch. Capping those gaps to recover "attended" time moves the answer from 18 h to 60 h
depending on a number nobody measured, so no cap was used: the band is the per-day first-to-last
prompt window, 51.3 h, stated as an upper bound on one person's involvement and drawn as one
inseparable "person + agent" segment. The asymmetry the user expected — minutes against
core-hours — is not in the data at 5.7:1; the one that is, and that the chart labels, is per
prompt: 45 prompts bought 6.45 machine-hours and 1,298 model calls each.

`export_effort` in `talk/scripts/export_talk_data.py` writes `talk/public/data/effort.json` from
those files plus `git log --numstat`, and `talk/src/charts/EffortWaterfall.tsx` draws it. Both
attribution rules are in the export's own `method` and both hold their objections in `caveats`,
so a caption cannot drift from the bars it describes.

## 2026-09-17 21:55 — Not a waterfall: a project timeline, with points where there are no durations

The user's verdict on the two-band waterfall was that "waterfall" had been the wrong word, and
that what he wanted was a project-timeline Gantt: named steps as lanes down the left, one clock
across the top, a bar spanning the period each step occupied. The kind-of-work band is gone, and
with it the last of the estimated human time: "if we have durations for some event types, great;
if not, let's just clearly mark the point in time when the event was."

That instruction is now the figure's rule. A prompt and a commit are dated to the minute and
nothing in the repository says how long either took, so they are marks with no width — a tick, a
dot — and no bar. A job's manifest states its own `wall_seconds`, so a job is a bar.

Two findings came out of building it, both of which changed what the picture could claim:

- The CPU/GPU split the user asked for cannot be read off the workflow, because **no rule in it
  requests a GPU**. `res()` passes `mem_mb`, `runtime` and `cpus_per_task` and nothing else, the
  Palmetto profile names one partition for everything, and there is no `gres` or `gpu` key in the
  Snakefile, `config/` or `profiles/`. What the score rules do declare is an `llm_*` throttle
  token, so the two job lanes are split on that instead: jobs waiting on the model service (587,
  288 h of wall time for 0.61 h of this cluster's CPU) against jobs computing here (75, 2.2 h of
  wall for 4.11 h of CPU). The GPUs that answered 58,409 calls belong to a service this project
  never meters, and the caption says so.
- Git *can* tell an agent's commit from a hand one after all, though not by authorship: every
  commit here is authored by the owner, but 110 of 112 carry a `Co-Authored-By: Claude` trailer.
  That trailer is the AI lane's claim — not "the AI did this" but "this commit says an agent
  co-authored it" — and the two without it are drawn hollow.

## 2026-09-17 19:35 — The slides come back out

The user tried the deck and rejected the constraint: "the slides idea appears to be too difficult a
constraint on differently sized screens." Fixed 100vh panels assume a projector's aspect ratio and
punish every other one. Keep the text idea, drop the layout, keep the heading-skip controls.

So the `Slide` component and its fifty-three lines of presenter CSS are gone, and the thirteen
section files are restored to their pre-slides shape — which the restore made easy, because each
had been changed in one commit and nothing since had touched them except two changes worth
keeping: the effort chart replacing the timeline strip in the premise, and the page QR's size.
Both were re-applied by hand onto the restored files. Presenter mode is now what it was plus the
bulletised prose: the page scrolls normally, the bullets stand in for the paragraphs, the deep
panels and callout bodies stay hidden, and `[` and `]` still jump between sections, since those
never lived in the slide code at all.

Two lessons from the attempt, both worth keeping even though its output is gone. The first is that
`display: contents` made the experiment free: the slide wrapper had no effect on the page, so
removing it could not regress the scrolling site, and the revert was a restore rather than an
untangling. The second is about verification. A screenshot came back blank, and the obvious
reading was that the revert had broken the page. It had not: this session and the chart agent
share one checkout, so they share `talk/dist/`, and the preview server was serving the agent's
half-finished build. Two sessions on one checkout, exactly as this file has recorded before, in a
new costume. Verification now builds to a private output directory of its own.

## 2026-09-17 22:40 — Surface the RCD LLM service calls, at the resolution the archive supports

The user asked whether the calls to the RCD LLM service could be highlighted as events. They are
the largest number the study produced and they were invisible, folded inside the bars for the jobs
that made them.

The archive does not support drawing them as events, and the answer is to say so rather than to
fake it. A response in `results/score/*.json` carries how long it took — `replies[].elapsed_s` —
but no wall-clock time of its own; the only clock is the chunk's, whose manifest dates it and
states its `wall_seconds`. So 58,409 marks cannot be placed. What the record does support is a
rate: a chunk knows how many calls it made and over what interval, so its calls are spread evenly
across its own span and summed into fixed fifteen-minute bins.

That is a third grammar in a figure whose whole argument is that its grammar means something, so
it is labelled as one: a tick is a moment, a bar is a period, an area is a rate. The bin width is
fixed in the export rather than left to the drawing, so the peak the lane names — 9,627 calls in
one fifteen-minute bin, against a mean of 4,561 an hour while the service was busy — is the peak
the lane draws, and stays the same number on a projector and on a phone. The caveat that the calls
are dated to their chunk and not to themselves is in the export and reaches the caption from
there.

The lane is named for the service as `docs/rcd_llm_service.md` names it, and so are the job bars
underneath it, which are the same service seen from this side of the wire.

## 2026-09-17 19:55 — The callout legend comes out, and the calls go in

Two edits in one pass. The user cut the premise's "Three kinds of callout" legend — "too on the
nose. Just use the callouts." A legend that explains a rhetorical device before the device has
done anything is a stage direction read aloud; the callouts introduce themselves. `KIND_BLURB`
existed only to feed it and went with it, as did its five chip rules and the line in PLAN.md's
section-1 screen that specified it.

The user also asked to highlight the RCD LLM service calls as events, and the answer is the honest
one: they cannot be placed. An archived response carries `elapsed_s` — how long the call took —
and no wall-clock time at all. Only the chunk that holds it is dated. So the calls are not 58,409
marks; they are a fifth lane drawn as a rate, each chunk's calls spread evenly across its own span
and summed into fixed fifteen-minute bins, with the bin width fixed in the export rather than at
draw time so the number the lane names is the number it draws on any screen. The figure's grammar
is now declared in three parts — a tick is a moment, a bar is a period, an area is a rate — and
the caption says a wave's shape inside a chunk is smoother than the truth.

## 2026-09-17 20:20 — Inside baseball comes off the page

The user quoted the effort figure's caveat paragraph back and said to remove it "and any such
'inside baseball' comments from the website". It was method notes written for a reviewer and read
by a room: the attended window's unmeasurability, arm D leaving no manifest, which commits an
interval takes its activity from. All true, none of it the audience's problem.

Rather than delete only the paragraph quoted, every long note and caption on the rendered page was
pulled out through the browser and read. Four more of the same genre came off: the caption had
started explaining its own binning; the archived call listed what the snapshot redacts to be
publishable, which is plumbing rather than a finding, on two sections; H5 cited "the report's own
convention" for drawing an interval at half strength; and the title band named the export script
and the commit hash, where the claim — every number comes from the run's own files — was the part
that mattered. `effortCaveats` had nothing left rendering it and went too.

What stayed, deliberately: notes that help a viewer read a chart (which arm a single bar belongs
to, why a divider separates two model families), dataset facts, and the file-provenance line under
each figure, which is the traceability the talk argues for rather than a note about it. The
caveats themselves remain in `effort.json` and in the chart's "read this chart as text" summary,
where a reader who wants the method can still find it.

## 2026-09-17 20:50 — One mode, and it is the talk

The user read the effort chart's text summary, found it a wall, and drew the general conclusion:
"This is primarily a talk. Not a complete documentation of the project. That's what the technical
report is for." Then the structural instruction: commit the current form, remove presenter mode
and make it the only mode, keep the bulleted forms, and find edits for improved presentability.

The current form is tagged `talk/dual-mode-form` so the prose-and-paragraphs version stays
recoverable, and two forks were put to the user before cutting. The authored prose: delete it, the
tag holds it. The callout bodies and deep panels, which presenter mode used to hide: keep them
expandable, so the titles read from the projector and the room can open one on a phone.

So the presenter machinery is gone — the state, the `p` key, the `?presenter=1` parameter, the
rail's toggle, the `presenter-hide` class and the CSS that hid things behind it. `Body`, which
chose between paragraphs and bullets, is now `Bullets`, which has no paragraph form to fall back
to, and the twelve prose blocks it used to choose from are deleted: 6,292 characters of it. Two
paragraphs were rescued first, because they live inside collapsed panels the user chose to keep —
H2's answer to the circularity objection and H4's two limits — and now sit in fields of their own.
What presenter mode did to the type is now simply how the page is set: 19px root, larger chart
tokens, because an axis tick is the thing that fails from the back of a room.

Then the presentability pass, driven by pulling every block over 190 characters off the rendered
page rather than by reading the source. Five ledes were cut to a headline each, the opening
proposition among them; the chart summary went from four paragraphs to two sentences; two
chart-reading notes that explained their encoding twice were cut to one line. Thirty-six long
blocks became thirty, and most of what remains is callout bodies, which are closed until asked
for. PLAN.md now says the page is the presentation and that prose belongs in the report.

## 2026-09-17 21:10 — Say the thing instead of gesturing at it

The user named the failure mode with an example: "'The shape of the thing' is just so vague. Please
make the language more direct while still being candid and simple, not pretentious." A metaphor
that saves the writer from deciding what they mean costs the reader the sentence.

Four headers were naming their sections by gesture and now say what the section is: *How the study
is put together* for the workflow diagram, *How this talk was built* for the premise — which also
loses the awkward "the way it is about" — *What we asked the model* for the question, and *How the
study runs* for the machine. Fourteen phrases followed, found by reading the rendered page rather
than the source: two machines no longer "wear the word AI"; prompts set off hundreds of jobs
rather than waves of machine work; labelled images are what everything is measured in rather than
the study's currency; a negative result is the point of working this way rather than what the
recipe is for; write-protection means re-running has to be deliberate rather than being a decision
and not a timestamp; thinking helps and hurts rather than rescuing and costing; a null means more
thinking is not what the model lacked rather than that the reading is not attention-limited; and
the coda became "then a prediction". Two callout titles that were riddles — "One chunk before 270"
and "A runtime request that costs everything" — now summarise instead: *One chunk run before the
other 270*, *A time limit that loses the whole chunk*.

Kept deliberately: "understanding debt", which the talk coins and then explains, and which is the
argument rather than an ornament; the refrain; and "largely automated — and largely is the honest
word", where the hedge is the point. PLAN.md's section table carries the new headers, and its row
for section 1 now describes the timeline that replaced the strip.

## 2026-09-18 09:40 — The owner's edits, distilled and applied

The user edited the talk's text directly, then asked for the principles behind those edits to be
carried through the rest of it. Reading the diff, four rules:

1. **Bullets carry facts; callouts carry observations.** The user replaced the premise's aphorisms
   — "the code is not the product", "understanding debt" — with four lines of plain counts, and
   then, seeing a callout that merely recorded who did what, said the callouts should hold the
   observations instead: "the model outputs are not the product of science. the claims are. what
   evidence do we have and how can we trust it? understanding debt can accrue very fast if you're
   not careful." So the conclusions moved rather than disappearing.
2. **Plain, first person, short.** "Trying to get AI to do it the way I want" replaced two
   sentences describing the diagram. "Interests me." "Could use a cluster."
3. **Questions where the talk is genuinely asking.** The standfirst became three of them.
4. **Do not narrate what the visual already shows.**

Eleven callouts were rewritten against those rules. Three agent notes that recorded rather than
observed became observations; six principles lost the "Prevents:" formula and say the failure as a
sentence; the near misses were left as they were, because a concrete story that ends on its lesson
already obeys the rule. Six ledes and bullets went plainer — "deserves" to "needs", one duplicated
H4 bullet merged into the other.

Two other things the user cut, both of which had been flagged and kept twice before: the effort
chart's headline, which repeated the premise bullets once those carried the numbers, and — under
every figure on the page — the file-provenance line and the "Read this chart as text" toggle,
6,894 characters of them. The SVGs keep their own aria-labels, so a screen reader still has a text
alternative. The premise's four counts are now filled from the export rather than typed, because
the prompt count moved twice in one day and this file's first rule is that no number lives in it.

## 2026-09-18 10:15 — Motivate the science first

The user found the opening out of order: "what is the 4 days of work 58,409 number etc. Right after
the title... I'd rather jump into the science question." Then the general rule behind it: motivate
the science, which the audience can relate to, and only then talk about how AI was integrated.

So the running order changed. The title band keeps the title, the byline, the proposition and the
project, and loses the four stat tiles — the premise section carries those counts as the owner's
own bullets, and stating them twice was what made the opening feel like a boast. Then the question,
the concept bank and the images; then the hypotheses; then how the study is put together, which
became its own section rather than a subheading hanging off the title, because the workflow diagram
is the first thing the audience is asked to accept on trust and it should arrive after they know
what it is for. The process material — the effort timeline, the prompts and jobs and hours — moved
from first to eleventh, next to the close, where the ledger already lives. Section numbers were
renumbered to match.

A second instruction, applied as a sweep: "avoid bs like this throughout: 'Every number on this
page comes from the run's own files.' this is assumed. Keep it more professional." That sentence
had already gone with the tiles. Four more of the same kind followed: "job counts are this run's
own" became the counts; a figure explaining that its own dots use shape as well as fill so the row
reads without colour, and naming the file its numbers came from, now just says which dot means
what; the sample images lost their cache path and kept the fact that the sample is seeded; the
close lost the host, the write time and the export time. Claiming a virtue the work either has or
does not is not the same as having it.

## 2026-09-18 10:45 — The hypotheses leave the talk

The user cut the pre-registration walkthrough: "hypotheses as tiles doesn't really work. List them
out. Also, for the sake of time, let's not pre-register the hypotheses at all. Let's describe the
arms and then go discuss the results." The seven flip-cards are gone from the design section, which
is now called *Five arms, one classifier* and does what its name says — the diagram, the arm table,
two limits — before the results arrive.

The hypotheses themselves are not lost, they are demoted. They sit in the section formerly called
Explore, renamed *Extra* at the user's instruction, as a plain table: id, question, rule, the
threshold it asks for, the date and commit that registered it, and the verdict. A table, not
cards, because the complaint about the tiles was that a grid of flippable panels makes a reader
work to compare seven things that want to be read down a column.

Two loose ends followed from the cut, both found by re-reading the section rather than by the
build. A bullet said "a sign test across datasets decides each rule" when no rule is shown any
more, so it now decides each comparison. And the third of the section's three limits was
pre-registration bookkeeping — the rules restated for twelve datasets once six verdicts were
known — which now sits with the hypotheses in Extra, leaving two limits behind.

Kept in the talk, deliberately: the callout saying a rule counts only if it precedes its numbers
and that here you can check it. The seven rules are gone from the room, but the practice is a
one-line observation and it is the reproducibility thread the talk is about.

## 2026-09-18 11:20 — MedMNIST first, then the textbook, then a duplication sweep

The user recast the section that had been called *What we asked the model*: name it "Medical images
and associated visual features", make it MedMNIST-focused, describe the dataset in the bullets, and
centre the second half on the textbook knowledge of what those images contain.

So the section now opens on the release rather than on the prompt. Its bullets are the suite: the
twelve 2D tasks and their modalities, the mix of binary, multi-class, ordinal and one multi-label
problem and the span of class counts, the 224-pixel serving, the untouched official splits, and the
fact that a published fully supervised number exists to compare against. Counts come from the
snapshot through the same shape-filling the premise uses, because a release that gains a task
should move the sentence. The second half gained a header and a lede of its own — *What the
textbook says to look for* — and four bullets about the features themselves: how many per task,
the cited anchor text behind each level, the per-class fingerprint, and that the whole bank was
committed before any call went out.

Then the user pointed at a panel and a callout: "remove both of these. the non-callout part is
already in the 'Agent Note'... If there are other sources of duplication like these, go ahead and
simplify simplify simplify!" The bank-provenance panel and the *Pin the inputs* principle both went.

The sweep that followed pulled every lede, bullet, note and callout off the rendered page and read
them side by side, which is the only way this kind of duplication shows itself. Nine more cuts. The
design lede, a bullet and a note each said the arms share one classifier and differ in features;
the lede now says two arms use no labels and three use n. H2's lede was its own bullets written out
as sentences. H5 had a bullet restating the two above it. Verdicts counted its verdicts in the lede
and again in a bullet, and two more bullets said what the takeaway says with numbers. The machine
lede said what the callout beside it says. H3's chart note repeated its first bullet. And design's
pre-registration callout said what H4's says, so the one where the rules actually mattered stayed.

## 2026-09-18 12:30 — The talk cut to twenty-five minutes

Overnight instructions, in the order they arrived: the talk is far too long; the learning curve
should be the headline, with a control that picks which question you are asking and presets the
arms that answer it; keep the thinking plot and the seven verdicts, but give the verdict table a
human-readable description instead of "what it counted"; drop the ceiling figure outright ("just
terrible"); remove "what this study does not claim"; use callouts only for a principle about what
is genuinely different about doing science with AI, or a surprising observation, and otherwise
have none; put H3/H7's detail in Extra and leave only its rows in the summary; keep developer
vocabulary off the page except where the talk names it, as with Snakemake; simplify, simplify,
simplify — and remember the website can support people digging deeper on their own time.

A review agent did the work; this entry records what was verified rather than what was reported.
Five hypothesis sections became one, *One figure, three questions*: the learning curve with a
question picker, each choice presetting the visible arms. All three presets were checked in a
browser against what they claim to show — H1 draws the checklist arm, the concept classifier and
the pixel baseline; H2 draws the two zero-label arms; H5 draws the pixel baseline against the
combined arm — and they are right. An earlier alarm about the combined arm being missing was a
fault in the checking script, not the page.

The page is eleven bands and 17,679 pixels tall, down from 28,643. Callouts went from fifteen to
ten, two of them merged because they stated the same principle. The ceiling figure and its
sentence are gone, and nothing on the spine says what the study does not claim; Extra carries all
four of those. Detail was demoted rather than deleted: the model ladder to Extra, and the n_B
table, the dumbbell, the permutation panel, the forest plot, the reader chain and the day timeline
into closed panels beside the sections they belong to.

The jargon sweep reached the export script, not just its output, which is the part that mattered.
Re-running the export reproduces every renamed phrase — the timeline lane now reads "121 of 125
name an agent as co-author" from generated text — and `study.json` came back identical but for its
timestamp. The counts moved because this session kept adding to them: 49 prompts to 57. What
remains of the old vocabulary is inside the archived record panel, where the field names are the
evidence rather than our prose, under a heading that now explains what the panel is.

Delivery estimate, section by section, is about twenty-three minutes. Three sections run over two
and a half, and each is over because of something the owner asked to keep.

## 2026-09-18 13:25 — The classifiers are not identical, and the models get a section

Three instructions, in the order they arrived. **"The classifiers are not identical. Surrounding
copy needs to be fixed and the diagram."** He is right, and the error was substantive rather than
cosmetic: the arm diagram drew one box labelled *one identical classifier* fed by both feature
blocks and fanning out to C, P and C+P, which says the three arms share one object. They do not.
They are three separate fits of the same specification — a linear classification head, the same
regularisation search, the same seeds and the same nested subsets — each on the features its arm
is defined on (`priors/stages.py` calls `fit_predict` once per arm per n per seed, and
`priors/classify.py` says so in its own header). What is held identical is the procedure, not the
classifier, and the study's fairness argument is the procedure, so the drawing was undermining the
claim it was there to support.

The diagram was redrawn in five columns — image, what reads it, features, *one procedure, three
fits*, arm. Each arm that gets labels now has a head of its own, outlined in that arm's colour,
and every line wears the colour of the arm it ends at, so provenance is readable without a legend:
C's head is entered only by the concept vector, P's only by the pixel features, and C+P's by both.
C+P's head sits between the other two on purpose, so the two blocks converge on it without a line
crossing anything. The zero-label arms are unchanged, because they were right: A leaves the
zero-shot prompt and never becomes features, B reads the concept vector with no head at all.
Seven copy locations repeated the error and were corrected — the section header, a bullet, the
probe note, two of the three question descriptions on the results figure, the H5 forest caption,
the reader sentence in the thinking section, the model-ladder axis label in Extra — plus the
diagram's aria-label, the file's header comment and `talk/PLAN.md`.

**"Removed archived content as well. Everything is committed if we need it."** Acted on as a
deletion, and then corrected mid-session by the owner: *"Reorganize this widget. I really like
it... It just needs to be cleaned up substantially to be more visually intuitive."* The deletion
was reversed from `HEAD` before anything else was built on it. The real defect was that the two
prompts return different shapes of answer — the checklist returns a level per visual feature, the
other prompt a number per class — and one display drew whichever was drawn at random. It now shows
one image with **both** of its answers side by side, which is the contrast the panel exists to
show: two tables, one captioned for each question, the class table sorted with the true class
marked, and the record beside the picture cut to two facts, which model answered and whether it
was thinking. No reply text and no field names anywhere in it. The class distribution was in the
archive but not in the export, so `talk/scripts/export_talk_data.py` now carries the score stage's
parsed `scores` for every zero-shot record; it is parsed against the release's own class names, so
`"0": 0.7` never reaches a reader — except on retinamnist, where the release's class names really
are the grades `0`–`4`.

**"After the 'arms' section, add a brief section for the VLMs considered in this study."** A new
section three, *The models we asked*: a lede, four bullets saying what each column is for, and one
table of seven rows — family, size, the thinking settings the service accepts, open or closed
weights, and calls in this study. Every column answers a question the talk asks later, and nothing
else was added. Two of those facts are in neither the configuration nor the results: whether the
weights are open, and which reasoning efforts a model takes. They are transcribed into the export
from `docs/rcd_llm_service.md` with the source recorded beside them, rather than inferred from
`api: local` against `api: gateway`, which is a transport and not a licence. The closed family's
size reads *not published*, which is the honest cell and is why H7 had to order that family by
price. The page is twelve bands; the sections below the new one were renumbered.

**Checked rather than taken on trust.** The redrawn diagram was read as an image: each labelled arm
now enters its own head, every line wears the colour of the arm it ends at, and the column that
used to claim one shared classifier reads *one procedure, three fits* — which is what the code
does, one call to `fit_predict` per arm per n per seed. The model table's call counts were checked
against `archive.by_model` row by row and they sum to 58,409, the archive total, with the readers
folded into their models. Re-running the export reproduces `study.json` and `archive_sample.json`
with no difference but the timestamp, so nothing in either was hand-patched.

One claim was walked back in review. The table said the closed models take low and medium effort
"never off", which reads as transcribed capability — but `docs/rcd_llm_service.md` says in terms
that its metadata covers locally hosted models only, so for the closed family there is no published
listing at all. Those two cells are the settings this study was able to use, not what a vendor
publishes, and the note under the table now says so. The open rows were checked line by line
against the doc's table and are faithful.

The only developer vocabulary left on the page is inside the two prompts Extra shows verbatim,
which tell the model to reply with a JSON object. That is the instruction actually sent, in a
panel that is closed until someone opens it, and it is the evidence rather than our prose.

## 2026-09-18 15:10 — Titles that name their contents

The user cut a panel and named a habit. The panel — "How many calls each model answered, and under
what name" — repeated the models table three sections above it, so it went. The habit is coyness in
titles: *"I really don't like the style of many of the titles like 'the models we asked'. We asked
what? What does ask mean? Something like models tested is more to the point."*

A title should answer "what is this?" without the reader having to open it. Seven were rewritten
against that. *The models we asked* is *Models tested*. *One figure, three questions* described the
presentation rather than the subject and is now *Test AUC for each arm*, which is what the axes
show. *The images, as the model sees them* is *Sample images*. Inside the archived-call panel,
*Asked the checklist* and *Asked what it is* repeated the same verb the user objected to and are
now *Checklist answers* and *Class answer*. *Everything behind this page* is *Links*, and *The
files behind all of it* is *Files*.

Left alone deliberately: *What if the model thinks?* which the user asked to keep; *How the study
is put together* and *How the study runs*, which already answer the question a title has to answer;
and the titles he wrote himself.

## 2026-09-18 16:05 — Name the model behind every result

Naming the model under the results figure turned out to be an instance of a rule: *"Everywhere we
report a result that depends on model outputs, you should clarify what model is used."*

Every section was pulled off the rendered page and tested for whether it names a model anywhere in
its own text. Three failed while reporting model-dependent numbers. The thinking section said "the
same model, told to think" and "a frontier model in place of an open one" — both now named from
the snapshot, the open one from `study.primary` and the frontier resolved out of the reader table
rather than typed, so the sentence follows the configuration if the comparison ever changes. The
verdict board reported seven verdicts with no model in sight and now says which: five rest on the
one model, and the other two are the comparisons across models.

The third was not a result but belongs to the same rule. The concept bank is a model's output —
compiled by Claude Opus 5 from the literature — and the callout that admits no clinician has read
it did not say who wrote it either. It does now. Of everything on the page this is the claim most
worth attributing: an input built by a model, reviewed by the same model, used as the study's prior.

Sections that name no model and should not: the title, the dataset section, the arms, the workflow,
and the effort timeline, none of which report a number that came out of a model.

## 2026-09-18 17:10 — A plain-language pass over all the copy

The user asked for the standard he has been applying by hand for two days to be carried through
every line on the site: *"avoid vague terminology, unusual metaphors, virtue signaling. Keep it
candid and simple but use plain direct language."* His own words stay untouched — the title, the
byline, the standfirst, the project intro and its five bullets, "How the work unfolded." and its
four counts, the callout about outputs not being the product, and the headers he set.

The pass was driven by pulling every heading, bullet, callout, caption, note, table header and
chart label off the rendered page rather than by reading the source, which is how the chart
strings were found at all: half a dozen of the worst phrases were axis labels and legend entries
in `charts/`, not prose in `content/index.ts`.

Four faults, in the order they were worth fixing. **Unexplained vocabulary**, where the technicality
was not the point: anchor text, penultimate features, the shared prefix, label maps, estimators,
metric conventions, a dataset-model cell, quantisation, permuted, temperature zero, the bootstrap.
Each now says the thing in words the room already has — "the wording the model is shown", "AUC
lost when the bank is shuffled", "it refuses to answer deterministically". **Two names for one
thing**: arm B was "the checklist arm" while arm C was "the concept arm", though both are built on
the checklist; H1's sentence now names each by what was fitted on what, and B is the
"textbook-only arm" as the legend already called it. **Sentences that announced themselves**: the
models lede spent half its length saying that its own columns mattered; the effort chart's caption
restated the legend beneath it word for word; the report stage ended on "no number in it is typed
by hand", which the workflow diagram already says. **Aphorism in a bullet**: "A null is a result"
lost its first clause and keeps the finding.

Some things were left deliberately, and are worth recording as decisions rather than oversights.
"Understanding debt" and the refrain are load-bearing and the user has said so. "Bought" for calls
that cost money is candid, not a metaphor. "Wave" for a batch of jobs is defined by the sentence it
appears in. The seven one-word hypothesis titles in the verdict board — Substitution, Scale,
Complement — come from `WORKFLOW.md` through the export and sit beside a plain-English question
column, so they were left to the owner.

Verified: type check clean, twelve bands and no page errors in light and dark, and the rendered
text diffed line by line against the pass before it.

**One edit in that pass broke the rule it was working under.** The effort chart's new caption read
"Nine days of the project on one clock" — a number typed into the file whose first line forbids
it, and already wrong: the export had reached ten days that morning. It is a shape now, filled
from `effort.days` in the section, which is the pattern the rest of the page uses. Worth recording
because the failure is characteristic: a rewrite for plainness reached for a concrete number, and
a concrete number is exactly the thing that goes stale while the prose around it stays true.

## 2026-09-18 08:40 — The figures get the plain-language pass, and "checklist" loses its place

The prose had been through a plain-language pass and the figures had not, so the same standard was
carried inside them: axis labels, legend entries, direct end-labels, in-figure annotations, column
headers drawn in SVG, tooltip text, captions, panel summaries and every `aria-label`.

The user's worked example set the calibration. The arm diagram had a column headed *one procedure,
three fits* over three boxes reading *linear classification head, fitted on n labels*. He wanted
one word: **classifier**. The history behind that column matters — it replaced *one identical
classifier*, which was false — but the fix had been made in words when the picture could carry it:
three separate boxes each labelled "classifier" already say there are three. So the column header
is gone, each box says "classifier", and nothing on the page claims the arms share one. The boxes
narrowed with their text and the lines into and out of them moved with the boxes; no arm, colour or
connection changed.

**Then the vocabulary itself moved.** The learning curve's legend said *arm C: concept scores* and
*arm B: textbook only* while the prose beside it said *checklist answers* — two names for one
thing, the fault an earlier pass had fixed in the prose and left in the figures. Told to make them
agree, the answer was first "checklist" everywhere; the user then rejected the word outright:
*"Plain language issue. Use 'visual features' or 'feature scores', 'scored visual features'."* A
checklist names the shape of a list without ever saying what is on it. So the page now has one
name per thing: the textbook lists **visual features**, the model returns **feature scores**, and
what arms C, P and C+P each fit is a **classifier**. Arm stays, because the diagram explains it.

The five arm labels live in `study.style.arms`, so the rename was made in
`talk/scripts/export_talk_data.py` and the export re-run rather than hand-patched into
`talk/public/data/`. Re-running reproduces every renamed string and changes nothing else: the arm
and ceiling labels in `study.json`, the two prompt names in `contention.json`, the timeline's kind
labels, three lane notes in `effort.json` and four entries of the close's "caught by" list. The
counts that moved — 59 prompts to 62, 126 code entries to 134 — moved because this file grew
today, not because anything was edited.

Other vagueness of the same kind, judged one at a time against "would someone who has not read
this page know what this refers to?". Changed: *class fingerprints* to the levels the textbook
expects for each class; *the price ladder* to the closed models ranked by price; *the reader
chain* to the comparisons between readers; *n_B* to "500 labels to match arm B" drawn on the
figure itself; *the pixel arm* to arm P; *permutation controls* to the bank being shuffled;
*wave* to "many at once" wherever the sentence did not define it. Kept: concept bank, probe,
reader, chunk, arm and AUC, which the page teaches; *frontier model*, because the model it means
is named in full beside every use of it; and *ceiling*, which the legend now spells out.

**Seven of the ten callouts came out** in the same pass, on the user's audit. Three stay: *No
clinician has read this bank*, *The outputs are not the product* and *Understanding debt* — all
three agent notes, and two of them his own words. The seven near misses and principles are deleted
rather than commented out; the history holds them, and the close's "what caught each one" list
still carries every one of those stories in a line each. Four sections now have no callout at all,
which is the standing rule working: the arms, how the study runs, the results and the thinking
section end on their own material, and the empty `callouts` arrays and `<Callouts>` elements went
with them.

Checked by looking, not by building: twelve bands and no page errors in light and dark, every
figure touched read as an image in both themes, and the learning curve under all three question
presets and on the one dataset whose crossing mark is drawn. Two label faults were found that way.
The closed-model chart's y-axis label ran fifty-six characters up a three-hundred-pixel plot and
overprinted its own ticks at both ends — it now says "probe AUC" and the fitting detail moved to
the note beneath. And the legend chips grew by a line under the longer arm names, which wraps
cleanly and was left. One fault was seen and left alone: the thinking scatter's rotated y-axis
label sits on its tick labels, which is geometry rather than language and predates this pass.

## 2026-09-18 19:40 — "Checklist" goes, and seven callouts with it

Two instructions, one pass. The first: *"I don't like 'checklist'. Plain language issue. Use
'visual features' or 'feature scores', 'scored visual features'. Apply throughout. Identify other
similar vagueness. Arm can stay, because we have the opportunity to clearly explain it with the
diagram."* "Checklist" was the agent's own plain-language substitute for "concept", and it failed
the owner's test in the same way the words it replaced did: it names a form — a list of things to
check — without ever saying what is on it. The page now says the textbook lists **visual
features**, the model returns **feature scores**, and what arms C, P and C+P each fit is a
**classifier**. Arm stays, because the diagram defines it.

The second was the figure pass itself, calibrated on *"one procedure, three fits. Just say
classifier."* That column header is gone: three boxes each reading "classifier" already say there
are three of them, which is the whole point of drawing it rather than asserting it — and it says so
without reviving the "one identical classifier" error the header was written to correct. Arm labels
and the ceiling label moved in `export_talk_data.py` rather than in the JSON, and a re-export
reproduces them exactly.

The owner also audited the callouts and cut seven of ten, keeping only the three agent notes: the
bank no clinician has read, the outputs not being the product, and understanding debt. Four sections
now carry no callout at all, which his own rule allows. The near-miss stories are not lost — the
close still lists what caught each one — and the contention chart, which had been placed to
illustrate the deleted wave-that-wrote-nothing, was kept because it answers the question its own
section asks; its caption lost the word "wave", which only the deleted box had defined.

A measured sweep afterwards found fourteen places where two pieces of text overlap inside a figure,
the worst being two model names colliding by forty pixels on the reader chain. Those are geometry
rather than language, and several predate today; they are the next thing to fix.

## 2026-09-18 21:30 — It is the scholarly record, not a textbook; and the talk ends on takeaways

Nine instructions in one batch, and the first is a factual correction rather than a style one:
*"Calling it textbook features is not quite right. These features were scraped from over 100
scientific papers. So it's more like what does the scholarly record show."* The bank was compiled
from the published literature, and the files say so — 92 distinct citation keys across the twelve
`talk/public/data/bank/*.json`, which is fewer than a hundred, so the page states the real count
and reads it from the bank files rather than carrying a typed number. Every use of *textbook* in
the talk's own language is now *the literature*: the bank's header and bullets, the arms lede, the
three question chips and their descriptions, the H1/H2/H5 sentences on the verdict board, arm B's
legend on the dumbbell, the permutation legend, the archived-call caption, the arm diagram's
description, and what the study does not claim. Three phrases are left because they come through
the export rather than the site source — arm B's label in `study.style.arms` and H1's and H5's
`question` fields — and are for the session that owns `export_talk_data.py`. The repository,
`WORKFLOW.md` and the study's internal names are untouched: the correction is to the talk.

The rest, in the order they arrived. *One kind of callout*, labelled **Note** — "I don't think
people keep track of that in their heads" — so `CalloutKind`, `KIND_LABEL`, the `kind` field, the
three colour rules and two wash tokens are gone, and the three surviving notes are simply notes.
*The arms section's two limits* became a closed `Limitations` panel, and the thinking section's
"two limits on this reading" the same, that being one of the vague references the next instruction
was about: *"'each to settle one question' is a vague reference. Avoid all such vague
references."* That clause now names the comparison it meant, and "the N the rule asks for" — a
rule the talk stopped showing when the hypotheses moved to Extra — is "the N needed to count as
support" in all four places it appeared. *The information architecture is the project, not the
study*: **How the project is structured** and **How the project runs**. *The refrain is cut*,
both the standalone pull quote and the one at the close, along with the `REFRAIN` export and its
band styling; `talk/PLAN.md` records the cut with its date. *"What four days cost" is deleted
entirely* — "it's too hard to parse in a general audience" — with its file, its content block, its
entry in `SECTIONS` and the list of what caught each mistake; the *Understanding debt* note, the
links and the closing QR moved into the new last section. *The model-size result came back onto
the spine* as section 7, immediately after the results figure: the ladder with its two views, one
sentence of what it found, nothing else, and out of Extra — which also loses the archived-call
widget, since the talk already carries it.

*Takeaways*, last, is the section he speaks from: ten bullets in his own words, lightly edited,
and three the agent proposed under a heading that says they are the agent's, to be kept or cut.

One fault was found by looking rather than building, and it predates this session: the ladder's
right margin was fixed at 108 px while the grey band's label, *other datasets*, needs more, so it
was clipped at the edge of the plot in both the readers chart and the model chart. The margin is
now measured from the longest label actually drawn. Verified with the page built to a private
output directory: thirteen bands, the rail and the eyebrows agreeing on the order, no page errors
in light or dark, and every changed section read as an image in both.

*How the project runs* stopped being prose and became the rules themselves. The nineteen Snakemake
rules are a table grouped by stage, each row expanding to the rule's own code — what it declares as
input, what it writes, the resources it asks the scheduler for — and beneath it the dependency graph
drawn from `snakemake --rulegraph` rather than by hand, with the test rule's edges dashed and
labelled so the shape is readable without knowing the tool. The caption makes the point the section
exists for: nobody drew that graph; it is worked out from what each rule says it needs. The export
now needs Snakemake on the path to regenerate it, which is why it reads `PRIORS_SNAKEMAKE`.

Two items each agent left for the other were closed here. The three `textbook` strings that reach
the page through `export_talk_data.py` — arm B's label and the H1 and H5 question fields — now say
*the literature*, so the count of that word in `study.json` is zero and the correction is complete
rather than nine-tenths done; and `StageStrip`, the diagram the rules table replaced, was deleted
along with the import it was the last user of. The export was re-run and diffed to confirm it
reproduces its own output: exactly three changes, the three strings, and nothing else moved.

## 2026-09-18 22:40 — The fourteen label collisions, and what a collision actually is

The sweep that ended the last entry was measuring the wrong thing. It compared the upright
rectangles the browser reports for each label, and a tilted label's upright rectangle is far larger
than the label: nine of the fourteen "collisions" were the model names on the readers ladder, which
sit on parallel diagonals and never touch. Rewritten to take each label's own box through its
transform and test the two shapes for real, the sweep found six, and every one of them was a
genuine overprint. Measuring badly is worse than not measuring; the tool is now worth keeping.

The real faults, all of them the same mistake — a distance guessed once and then relied on:

- The rotated y-axis title sat 40 px from the axis whatever the ticks said, so on the thinking
  chart, whose ticks carry a sign and are the widest on the page, it printed straight through
  them. The gutter is now worked out from the ticks the axis will actually draw, which needs the
  tick values but not the scale's range, so each chart settles its left margin before it places
  anything. The character widths behind that arithmetic were measured off the built page rather
  than guessed: the sans figures are tabular at 7.8 px, a leading sign is 11.7, the mono ticks are
  7.85.
- The same wrong habit under the axis: the title sat 15 px below the numbers, close enough that on
  a phone its descenders met three of them.
- Direct end labels were pushed 12 or 13 px apart when the labels are 16 px tall, so arm B under
  arm C, path under pneumonia and retina under organs all touched. The gap is the height of the
  text now. Where a ladder has a grey band, its one label holds the floor and the named ones stop
  above it.
- The ladder's model names were tilted 22° regardless of how many there were, and the room made
  for them was computed at 6.3 px a character — the figure for a smaller size than they are drawn
  at. The tilt is now whatever it takes for a name to fit the column it labels, and the margin
  follows from the tilt.

Zero collisions at 390, 768 and 1500 px, with every collapsible section open; thirteen bands and no
page errors in light or dark. Nothing about what the figures say changed.

## 2026-09-18 23:20 — The takeaways are a deck, and the agent's three are gone

*"Remove this callout. And these points."* The *Understanding debt* note and the three bullets the
agent had proposed under its own heading are cut; what the section carries now is his ten, and only
his. *"Combine the few that are largely about the same"* leaves six. Magic and *with great power
comes great responsibility* were one point about power, so they are one card. *My understanding has
not caught up* and *I had big surprises about how the workflow actually worked* were the same
admission twice. *Be more prescriptive about your standards* and *keep the distance between what
you want and what the AI produces small* are the same instruction from two sides. *Generating the
talk was the bottleneck* and *presentation is still hard for AI* are the claim and its reason. The
gap before publishing, and the workflow manager being useful twice, stand alone. Nothing was
rewritten beyond the joins.

They are a deck now rather than a list: one card, a counter reading 1/6, and an arrow either side
that cycles past the ends. A list lets the room read ahead; a card arrives when he says it. Every
card is rendered into the same grid cell with the ones not showing hidden rather than removed, so
the deck stands as tall as its longest card and the links below it do not jump as he steps
through. The arrow keys move the deck only while it holds focus: the page deliberately leaves the
bare arrow keys to the browser so a presentation clicker still scrolls one screen a press, and a
deck that stole them would break the clicker everywhere else. Checked by driving it: the counter
runs 1 through 6 and wraps in both directions, exactly one card is ever visible, the deck's height
does not change between cards, and it fits a 390 px screen without the page scrolling sideways.

## 2026-09-18 23:50 — "The compute workflow", and why a workflow manager at all

Section five is *The compute workflow* now, in the heading and in the rail, and the two paragraphs
explaining `make` are replaced by the argument he actually wants made there: what a workflow
manager is worth when an agent is writing the code. Four things — it is the context the agent works
from, it reads back to the human as the record of what the agent built, it states what depends on
what, and it is where checking starts, since asking for one thing names every step behind it — and
then the contrast he named: a pile of scripts does none of this, and only whoever ran it knows the
order. Shorter than what it replaces, as asked, and it says more.

One judgement call, flagged rather than buried: the Makefile connection he asked for in the
previous batch survives, cut from a paragraph to one clause — *a rule says what it produces, what
it needs, and the command between them; a Makefile, with the cluster written in* — because without
it the room does not know what a rule is before meeting a table of nineteen of them. The prose also
moved out of `Machine.tsx` and into `content/index.ts`, where the page's authored language belongs;
it had been written inline when the rules table was built.

## 2026-09-19 00:20 — The archived call is its own section, and carries the questions

*"'One archived image, and both answers'. First of all, this language is too indirect. Secondly,
this is orphaned."* Both true. It was the last thing under a heading about rules, where nobody
could tell what it was for, and it is really where the results begin: the raw input and output
every later number is computed from. It is section 6 now, **Model input and output**, between the
workflow and the results — three bullets and the widget, nothing else, because it is a hinge and
not a stop.

Underneath the two answers, closed, are the two questions that produced them, full text. They are
matched to the record by sha256 rather than by position in the prompt file: each block in
`results/prompts_txt/` is headed with its own hash and each archived reply's manifest carries the
hash of the string that was sent, so what opens beside an answer is the prompt that bought it or
nothing at all. Checked against the data as well as on the page — all 23 manifests in the sample
resolve to a block, and every one of them to the right kind of block.

The section numbers are no longer typed. Each section carried its own number in its heading while
the rail counted the same list independently, so inserting a section meant editing thirteen files
and getting a heading that said 6 over a rail that said 7. The heading now reads its number off
`SECTIONS`, which is also what the rail reads, and the two cannot disagree. Verified: fourteen
bands, eyebrows 1 to 13 under a title that keeps its date, and a rail that agrees line for line.

## 2026-09-19 01:10 — Four lines and a logo; the heading stands alone; what the bands are

Three corrections in quick succession, all in the same direction: less.

*"Way too long and too much jargon."* The workflow section's opening was a lede, three definition
bullets, a paragraph about `make` and a closing line — and he replaced it with four lines. It now
reads *Use a workflow tool to structure the compute*, with Snakemake's own wordmark beside it, and
four bullets: tells the AI what context to pull, shows me what the AI built, maps what depends on
what and re-runs what a change touches, tames the pile of scripts. Gone with it: what a rule is,
what `make` does, and the project's three words for its own parts. *Chunk* is still defined where
it is used, in the `score_qwen3_5_9b` row; *reader* in the caption under the readers ladder; the
write-protected archive is said in the section that shows one of its records. Nothing lost, three
fewer places to say it.

The logo is `biglogo.svg` from the Snakemake repository, MIT, copied into `public/img/` and served
from this site rather than hot-linked. It is greyscale, so dark mode inverts it rather than
carrying a second file.

*"Just remove all this. Not helpful. The title stands alone."* The lede and three bullets written
an hour earlier for **Model input and output** are gone; the heading sits directly above the
widget, which is what the section is.

*"'95% intervals' is not descriptive enough."* True, and it was the kind of number that says
nothing about where it came from. The bullet now reads: the middle 95% over 10,000 bootstrap
resamples of the test images, every arm recomputed on each resample. Both numbers come through the
export from `evaluate.ci` and `evaluate.bootstrap` rather than being typed, so a change to the
config moves the sentence.
