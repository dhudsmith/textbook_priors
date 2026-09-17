# The talk as a website: plan

*Textbook priors over visual features*, for Clemson HPC Day. Twenty-five minutes plus five for
questions. This file is the structure of the talk and the specification of the website that
delivers it. `TALK.md` §1–§4 still carries the argument about workflows and agents; this plan
inverts §5's spine — the **science is the talk**, and the reproducibility-with-AI commentary rides
on it as on-slide callouts — and replaces the slide table with a scrolling website.

Fixed 2026-09-16 with the owner: a science talk about the medical-imaging-with-LLMs study, with
commentary throughout about reproducible research assisted by AI; a website rather than a deck;
scrolling is the talk; bold headers separate the sections; interactive elements; a QR code at the
top so the room can follow along on their own devices; hosted on GitHub Pages.

## 1. The shape

**Spine**: one scientific question, five arms, seven hypotheses, seven verdicts computed rather
than chosen. The audience leaves knowing what a vision-language model's textbook knowledge is
worth in labelled images, and where it does and does not help.

**Rails**: three kinds of callout, colour-coded and placed beside the result they belong to, never
in a separate section. They are read aloud as asides or left for the audience to read later.

| callout | colour | what it carries | source it links to |
|---|---|---|---|
| **Principle** | blue | one reproducibility principle the study relied on, stated as the failure it prevents | `WORKFLOW.md` §5 |
| **Near miss** | amber | something that nearly went wrong, and *what caught it* — a person, one chunk, a probe, a manifest; never the DAG | `CHANGELOG.md`, dated |
| **Agent note** | violet | what the agent did, what the human had to do, and the understanding debt it left or repaid | `SESSION_LOG.md`, timestamped |

**Bookends**: the opening sets up the premise — this study was built in four days with an AI coding
agent, and the talk is the result — and the close returns to it with the ledger of what that cost
and what caught the mistakes. Everything between is science.

**The refrain**, said at the open and the close and written in one callout in the middle: *the
workflow turns hidden work into inspectable work; it does not inspect it for you.*

**Style**: one idea per section, a figure or an interactive in every section, numbers only where a
number changes what the audience believes, and every number on the page traceable to a file in
`results/` through the export described in §4. No number is typed by hand into the site source.

## 2. The sections

Bold headers on the page; the *presenter* column is what is said, the *screen* column is what is
built. Minutes sum to twenty-five.

| # | min | header | presenter | screen | callouts |
|---|---|---|---|---|---|
| 0 | — | **Textbook priors** | (title, no speech) | Title, one-line question, the QR code to this page, the four-day / 58,186-call / 12-dataset / 378-test stat tiles counting up, a progress rail on the left that stays for the whole scroll. | — |
| 1 | 2 | **This talk was built the way it is about** | The premise: a real study, designed on a Tuesday, run on Thursday and Friday, extended on Saturday, reported on Sunday; nearly every line of code written by an AI coding agent under a workflow that made its work inspectable. The turnaround is the point, and so is the question it raises: how do you trust a result you did not compute yourself? The refrain, first time. | A four-day strip from `SESSION_LOG.md` timestamps (one tick per prompt, coloured by the kind of work), hoverable. The three callout kinds introduced as a legend. | **Agent note**: what the human did (asked, read, decided, caught) against what the agent did (wrote, ran, measured, recorded). |
| 2 | 3 | **The question** | One chest X-ray at 224 pixels beside the textbook's checklist of what to look for. A vision-language model has read the textbook. How much of the checklist does it *see*, and is what it sees worth labelled images? | Dataset picker across the twelve MedMNIST tasks: sample images by class on the left, the concept bank for that dataset on the right as a checklist — hover a concept to see its ordered levels, the cited anchor text for each level, and the citation. Default: pneumoniamnist. | **Principle**: inputs are pinned — the bank is a committed, cited input built before any call; expert review simulated and stated. **Agent note**: the bank was compiled by an LLM from literature with a schema 110 tests enforce; no clinician has read it. |
| 3 | 3 | **Five arms, seven hypotheses, rules before numbers** | The currency is labelled images. Two arms use none (A: ask for the diagnosis; B: match the checklist answers to the textbook's class fingerprints). Three use n labels with one identical classifier on different features (C: concept answers; P: frozen ImageNet pixels; C+P: both). Then the seven questions, each with a decision rule fixed before its numbers existed. | An arm diagram (image → VLM → concept vector → B / C; image → ResNet → P; both → C+P). Seven hypothesis cards; click flips to the decision rule, its threshold (10 of 12 or 9 of 11 at p < 0.05), and the date and commit it was registered. | **Near miss**: the unfair baseline — a ResNet trained from scratch on fifty images against a model with billions of pretrained parameters; every rule would have been correct and the claim worthless; caught by a person reading the plan (`CHANGELOG.md` 2026-09-09). **Principle**: pre-registration lives in git — the commit carrying a rule precedes the commit carrying its numbers (H5, H6, H7). |
| 4 | 2 | **The machine** | Briefly: seven stages, one file, every number has a rule; 58,186 raw model responses archived write-protected with the served model name and prompt hash; everything downstream is a deterministic function of the archive. | A stage strip (Smoke → Sample → Score → Features → Classify → Evaluate → Report) with job counts; click a stage for what it does. Below, *one real archived call*: the image, the rendered prompt (collapsible), the raw reply, the parsed answer, and the manifest fields — `served_model`, `prompt_sha256`, `git_commit`, `slurm_job`. A button draws another at random from the exported sample. | **Near miss**: one chunk before 270 — rules generated in a loop all ran the last model's command; the first chunk came back with gemma's answers under qwen's file name; the only trace was `served_model` disagreeing with the filename (2026-09-11). **Principle**: the LLM boundary is explicit; re-querying is a deliberate act. |
| 5 | 4 | **H1 — Is the textbook worth labelled images?** | The learning curve. Arm B's zero-label line; how many labels the pixel probe needs to reach it is n_B. Answer: fewer than fifty on nine of eleven tasks; 500 on OCT, 200 on breast ultrasound. The concept regression beats pixels at fifty labels on those same two alone. Not supported — and a negative result you can stand behind is what the recipe is for. | The interactive learning curve: choose a dataset (or all twelve as small multiples), toggle arms A / B / C / P / C+P and the published fully-supervised ceiling, hover a point for its value and 95% interval, n_B marked where the pixel curve crosses arm B. A verdict strip under it: 12 dots, filled where C beat P at n = 50. | **Near miss**: the wave that wrote nothing — 48 jobs, two hours, zero output; a call that takes 1.5 s alone takes 43 s under our own load and 134 s under eleven thinking chunks; concurrency buys no throughput on a saturated endpoint, and the time limit decides whether anything is saved. Shown as an interactive contention chart (seconds per call and aggregate calls per second against jobs in flight) from the measurements in `CHANGELOG.md` 2026-09-12. |
| 6 | 3 | **H2 — The bank, or just the model?** | Asking for the diagnosis beat the textbook readout on eight of eleven. But permuting the fingerprints or the concept columns destroys both arms everywhere, so the concept answers carry real class information — the checklist readout is simply lossy. The twist: on kidney cell types the model's own guess is at chance and the checklist still ranks; where it can name the class, asking for the name wins; where it cannot, the checklist does. | A dumbbell chart per dataset: AUC(A) against AUC(B), with the B − A interval; a second panel of permutation drops as bars. Hover for numbers. tissuemnist highlighted. | **Near miss**: the field we did not read — one model filed 3,000 good answers under a third response field and a reader that knew two names recorded them missing; the archive held the extracted text, not the message, so the calls had to be bought again. Now the whole message object is archived (2026-09-11). |
| 7 | 3 | **H3 and H7 — Does a bigger model read better?** | Open weights, two families, 9B→27B and 12B→31B: no trend at all, Friedman p = 0.90. A closed family ordered only by price, luna→terra→sol: the top beats the bottom on 9 of 11. Whatever separates them is not what parameter count captured. | A ladder chart: one line per dataset across the four open models, then a toggle to the three closed models at effort low; the win counts beside each step. Hover a dataset to isolate it. | **Principle**: name the model, never the alias — `cub` and `tiger` point at whatever the service considers best today, which makes an archive unreproducible by design (`docs/rcd_llm_service.md`). **Agent note**: the service's own `/v1/models?full=true` metadata was read instead of probing, and it corrected the study's belief about which models could see images. |
| 8 | 4 | **H4 and H6 — What if the model thinks?** | One day, told by the clock. 15:20 a test overturns a standing claim: thinking never worked here, and the cause was our own 512-token budget. 16:05 a decision rule is written before a call is bought. 16:12 one chunk runs first; the gateway model refuses temperature zero. 17:35 eleven chunks at once and a timed call says 134 seconds — cancelled, capped at four. Result: thinking is conditional — it rescues the tasks the model read badly and costs the ones it read well — and a frontier model reads no better than a 27B open model. The coda: the archive showed the frontier model collapsing one dermoscopy concept to a single answer; a hypothesis was registered that lowering its effort would fix exactly that; it did, +0.13 on dermamnist and nothing else. A prediction named before the calls and confirmed only where it was aimed is the strongest thing in the study. | The one-day timeline, ticks from `SESSION_LOG.md`, clickable. The reader-chain chart (probe AUC per reader, one line per dataset). The scatter of thinking's effect against the baseline probe AUC, sloping down, hoverable. H6's eleven intervals with dermamnist alone clear of zero. | **Agent note**: an arm added after seeing the numbers (arm D) was removed the same day because it could decide nothing; H5, H6 and H7 were kept because their rules were committed before their numbers. **Principle**: a decision rule before the calls. **Near miss**: the runtime that was wrong in the way that costs everything — a chunk that overruns its limit writes nothing. |
| 9 | 2 | **H5 — Does the textbook add anything?** | The first supported hypothesis, and the one that changes what the others mean. Concept answers concatenated to the pixel features under the same classifier: a small, consistent gain at fifty labels on eleven of twelve, every winning interval clear of zero, median +0.007 AUC. The textbook cannot replace labels; it adds something the pixels do not carry. | The forest plot, interactive: hover for intervals, a slider to read the gain at every n on the curve (decides nothing; says so). | **Near miss**: two sessions on one checkout — a second agent switched the shared checkout onto its branch mid-run; five results were written by the wrong code; the manifests' `git_commit` named the culprit before any theory did (2026-09-13 12:25). *Read the manifest before forming a theory.* |
| 10 | 2 | **Seven verdicts** | Five not supported, two supported, none chosen. Against the published fully-supervised ceiling: the pixel probe at 2,000 labels sits a median 0.009 AUC below it; the best zero-label arm sits 0.115 below. Labels close the gap; the textbook does not — and still adds a small increment on top of them. | The verdict board: seven rows, each with its rule, its count (e.g. 2 of 12 against 10 needed), a row of twelve per-dataset dots, and the verdict. Click a row to jump back to its section. Below, the ceiling comparison as a compact dot plot. | **Principle**: every result carries a manifest — commit, seeds, versions, host, wall time — and the report is generated, so the site's numbers and the PDF's are the same files. |
| 11 | 2 | **What the four days cost, and what caught the mistakes** | The close. The ledger: calls bought, dollars at the gateway, tests written, hypotheses registered, mistakes caught — and by what: a person reading the plan, one chunk run before 270, a probe at the wire, a manifest field; the DAG caught none of them. The workflow turns hidden work into inspectable work. It does not inspect it for you. The Snakefile beside the session log: what was done, and why; you need both, and the workflow gives you the first for free. | The ledger as stat tiles; the "caught by" tally as a small bar chart; the Snakefile header and `SESSION_LOG.md` side by side in the same monospace; the QR code again with links to the repository and the report snapshot. | **Agent note**: understanding debt — every stage the agent wrote faster than its owner could read it is a loan; the practices that repaid it here (read every rule before it runs at scale; one cell first; make the agent explain the stage and judge the explanation; keep the CHANGELOG as the owner's record). |
| 12 | — | **Explore** | (not presented; for the audience on their own devices and for questions) | A full explorer: choose a dataset → every table row H1–H7 for it, the sample images by class, both rendered prompts verbatim, the concept bank, and a browser over the exported archived responses. Every figure the report generates, at full size. Links to the repository, `WORKFLOW.md`, `CHANGELOG.md`, `SESSION_LOG.md`. | — |

## 3. Interactivity, and what it is for

Each interactive element earns its place by letting a listener check a claim the speaker just made.

- **Progress rail**: sections as dots with their headers; the current section highlighted; click to
  jump. Keyboard: arrow keys and space move one section; `p` toggles *presenter mode*, which hides
  the explorer, the deep-dive panels and the callout bodies (titles stay) so the projected page is
  clean, while the QR audience sees everything.
- **Dataset picker** (sections 2, 5, 12): shared state, remembered across sections, so the
  audience member who chose dermamnist at the top sees dermamnist all the way down.
- **Charts**: hover for the value and the interval; click a legend entry to toggle a series; every
  chart carries a one-line caption saying which file its numbers come from.
- **Hypothesis cards** flip to the rule; **verdict board** rows expand to per-dataset differences.
- **Archived call**: a random draw from the exported sample, so no two audience members see the
  same one and the speaker can draw live without a queue or a sleeping model.
- **Timelines** (sections 1 and 8): hover a tick for the session-log entry title; click to expand
  the first paragraph.
- **Callouts** collapse to their title line in presenter mode and expand on click or on the
  audience's phones.
- **QR code**: rendered client-side from the page's own URL, so it is right wherever the site is
  deployed and needs no image file.

## 4. Data: exported once, from `results/`, with its provenance

The site has no compute of its own and hand-types no number. A one-shot export,
`talk/scripts/export_talk_data.py`, reads the run's outputs and writes a snapshot into
`talk/public/data/` and `talk/public/img/`, which are **committed** — the one deliberate exception
to "results are never committed", because the site is built on GitHub's runners where `results/`
does not exist, and because a talk is a snapshot of one run by design. Every exported file carries
the `git_commit` of the run it was read from (from the manifests) and the export date.

What is exported:

| file | from | content |
|---|---|---|
| `data/study.json` | `results/evaluation.json`, `results/evaluate/*.json`, `config/config.yaml`, `config/medmnist.yaml`, `data/literature/benchmarks.yaml` | dataset metadata (modality, task, classes, sample sizes); the seven verdicts with rule, threshold, wins, p; per dataset: A, B (every model), the curve for C / P / C+P at every n (point, lo, hi), the differences and intervals, n_B and its interval, permutation controls, the H4 probe AUC for all nine readers and the H4a/H4b/H6/H7 steps, the H5 differences at every n, the published ceiling |
| `data/bank/<dataset>.json` | `data/concepts/*.yaml` | concepts, ordered levels, anchor text, class fingerprints, citations |
| `data/prompts/<dataset>.txt` | `results/prompts_txt/*.txt` | both rendered prompts, verbatim |
| `data/archive_sample.json` | `results/score/*__qwen3.8-27b-fp8__test__concept__chunk00.json` and the matching zero-shot chunk | for each dataset, four archived records (raw reply text, parsed answer, `served_model`, usage, elapsed) plus the chunk manifest's `prompt_sha256`, `bank_sha256`, `git_commit`, `slurm_job`, `host`, `written`; the record's image goes to `img/archive/` |
| `data/timeline.json` | `SESSION_LOG.md` headings | every timestamped entry: time, title, first paragraph, a hand-assigned kind (direct / build / run / decide / catch / rewind) — the kinds are the one hand-authored field, kept in the export script as a table |
| `data/contention.json` | `CHANGELOG.md` 2026-09-12 measurements, transcribed in the export script with the entry cited | seconds per call and jobs in flight for the primary model, thinking off and on |
| `img/samples/<dataset>/<class>_<k>.png` | `data/cache/sample/*.npz` | two test images per class, 224 px PNG (capped at 16 per dataset) |
| `img/figs/*.png` | `report/figs/` | every figure the report generates, for the explorer and as a fallback |
| `report.pdf` | `report/report.pdf` | the report snapshot, labelled with its commit |

The export is also a Snakemake rule, `talk_data`, **outside `rule all`** and local (no LLM calls,
seconds of JSON), in the style of `prompts_txt`, so that "every computation is a rule" holds and the
inputs it depends on are declared. The script lives under `talk/`, not `priors/`, so it is not a
code input of any result and adding it reruns nothing. It runs with the base Python (numpy, Pillow,
PyYAML) and needs no model call.

## 5. The site

- **Stack**: Vite + React 18 + TypeScript; D3 (scales, shapes, axes) drawn inside React components
  for every chart, so hover, toggles and animation are ours; `qrcode.react` for the QR code. No
  UI framework: one stylesheet with design tokens, light and dark by `prefers-color-scheme`.
  Dependencies are pinned and few.
- **Layout**: a single scrolling page. `<section>` per row of §2 with an `id` (`premise`,
  `question`, `design`, `machine`, `h1`, `h2`, `h3`, `h4`, `h5`, `verdicts`, `close`, `explore`),
  so the URL hash names the section and the QR audience can be sent to the one on screen. An
  IntersectionObserver sets the active section for the rail. Sections animate in on first entry
  and never again.
- **Design**: the dataset colours are the report's own (one stable colour per dataset,
  `CHANGELOG.md` 2026-09-14) so a listener who has seen the PDF recognises them; arms keep the
  report's colours too (C blue, P red, C+P purple, B green dashed, A grey dotted, ceiling brown).
  Callouts are cards with a left rule in their kind's colour, a small-caps label, a title and a
  body, and a footer link to the source entry. Type: a humanist sans for prose, a monospace for
  anything that came from a file (model names, hashes, log lines). Charts follow the `dataviz`
  skill's rules: direct labels over legends where there is room, intervals as bands or whiskers,
  one accent at a time.
- **Performance**: `study.json` is a few hundred kilobytes; images are lazy-loaded; the explorer
  and the archive browser load their data on first scroll into view. Everything works offline once
  loaded, because a conference network is not to be trusted.
- **Accessibility**: every chart has a text summary; colour never carries meaning alone (verdict
  dots are also shaped); keyboard navigation for the rail and the cards.

## 6. Hosting

GitHub Pages on this repository, deployed by GitHub Actions from `main` (`.github/workflows/pages.yml`:
checkout, Node 22, `npm ci` and `npm run build` in `talk/`, `actions/upload-pages-artifact`,
`actions/deploy-pages`; also runnable by hand with `workflow_dispatch`). Vite's `base` is
`/textbook_priors/`, so the site lives at **https://dhudsmith.github.io/textbook_priors/**. The
repository was made public on 2026-09-16 for this, so the site, the code and the prose behind it
are all reachable from the QR code; nothing in the export is private — no key, no credentials, only
public benchmark images, the study's own numbers and the project's own prose.

## 7. Order of work

1. Export script and the `talk_data` rule; run it; check the JSON against three numbers in
   `report/tables/*.tex` by eye (H1 pneumoniamnist C − P at n = 50; H5 wins; H7 sol − luna on
   retinamnist).
2. Vite scaffold, tokens, the rail, the title and QR code, the premise section.
3. Sections 2–4 (question, design, machine) with their interactives.
4. The five result sections, one chart each first, then interactivity.
5. Verdicts, close, explore.
6. The Pages workflow; build locally; deploy; open the URL; walk the page top to bottom in
   presenter mode at projector width and on a phone width.
7. `SESSION_LOG.md` entry; `TALK.md` pointer; `README.md` layout line for `talk/`.

## 8. What is deliberately not here

No live demo and no live model call; the archived-call draw stands in for it. No hypothesis-by-
hypothesis walk through every table on the main scroll — that is the explorer's job. No number in
the site source; every one comes through the export. No claims the study does not make: the concept
scores are not clinically validated, the simulated review is not a clinician, no arm is state of the
art, and "the model carries textbook knowledge" cannot be separated from "the model has seen this
public benchmark".
