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
