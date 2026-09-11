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
