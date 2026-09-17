/* The talk's prose. Authored here, drawn from TALK.md, WORKFLOW.md, CHANGELOG.md and
   SESSION_LOG.md - quoted or paraphrased faithfully, with the study's stated limits kept and
   nothing invented. NO NUMBER IS WRITTEN HERE: every figure on the page comes through the export
   in `public/data/`. Where a sentence needs a number it is assembled in the section component
   from the snapshot.

   Callout kinds are talk/PLAN.md section 1: a blue PRINCIPLE states a reproducibility principle as
   the failure it prevents; an amber NEAR MISS says what nearly went wrong and what caught it -
   never the DAG; a violet AGENT NOTE says what the agent did, what the human had to do, and the
   understanding debt it left or repaid.

   Style: short sentences, a doer as the subject and its action as the verb, one idea each. Say
   what happened; let the reader judge it. */

export type CalloutKind = "principle" | "nearmiss" | "agent";

export interface Callout {
  kind: CalloutKind;
  title: string;
  body: string[];
  source: string;
}

export const REFRAIN =
  "The workflow turns hidden work into inspectable work. It does not inspect it for you.";

export const REPO = "https://github.com/dhudsmith/textbook_priors";

export const LINKS = [
  { label: "the repository", href: REPO },
  { label: "WORKFLOW.md — the plan and the seven hypotheses", href: `${REPO}/blob/main/WORKFLOW.md` },
  { label: "CHANGELOG.md — the owner's dated record of understanding", href: `${REPO}/blob/main/CHANGELOG.md` },
  { label: "SESSION_LOG.md — how the agent was directed, to the minute", href: `${REPO}/blob/main/SESSION_LOG.md` },
  { label: "CONCEPT_BANK.md — how the bank was built", href: `${REPO}/blob/main/CONCEPT_BANK.md` },
  { label: "the Snakefile", href: `${REPO}/blob/main/Snakefile` },
];

export const KIND_LABEL: Record<CalloutKind, string> = {
  principle: "Principle",
  nearmiss: "Near miss",
  agent: "Agent note",
};

export const KIND_BLURB: Record<CalloutKind, string> = {
  principle: "a principle the study relied on, and the failure it prevents",
  nearmiss: "what nearly went wrong, and what caught it",
  agent: "what the agent did, what the human did, and the understanding debt between them",
};

/* ------------------------------------------------------------------------------------------ */

export const title = {
  header: "Reproducible Scientific Computing with AI Coding Agents",
  /* The study's own question. Held out of the title band while the opening is re-cut: the intro
     below poses the project in the room's words, and two questions under one header read as a
     non-sequitur. Still the question the science answers. */
  question: "Can a vision-language model's textbook knowledge of what pathology looks like stand in for labelled data?",
  standfirst:
    "Here is a proposition much of this room will find reckless. Hand the machinery of a " +
    "computational study to a generative AI agent — the code, the job submissions, the analysis, " +
    "the figures, the report — and keep for yourself only the part that makes it science. The " +
    "objection writes itself: how do you trust a result you did not compute yourself? This talk " +
    "answers with a study rather than an opinion.",
  intro: {
    lede:
      "To make that concrete, we start a new project — one that had been sitting at the back of " +
      "my mind for a while.",
    question: "Can out-of-the-box vision-language models (VLMs) classify medical images?",
    body:
      "We largely automated the answering of it. Largely is the honest word, and what the human " +
      "still had to do is most of what this talk is about. Here is what came out.",
  },
  workflow: {
    header: "The shape of the thing",
    lede:
      "Fixed inputs on the left, one workflow in the middle, generated outputs on the right. " +
      "Two different machines wear the word AI here, and keeping them apart is the whole trick: " +
      "the agent wrote the workflow, and the model under study is something the workflow calls.",
    caption:
      "Solid arrows are data. Dashed arrows are authorship — what the agent wrote, rather than " +
      "what the workflow ran.",
  },
  qr: "Follow along on your own device",
};

export const premise = {
  header: "This talk was built the way it is about",
  lede:
    "The study was planned on one day and built, run, extended and reported over the next three. " +
    "An AI coding agent wrote most of the code. A workflow made its work inspectable.",
  body: [
    "Speed raises a question. If an agent wrote the stage, submitted the jobs and filled the " +
      "table, how do you come to trust the result? In science the code is not the product. The " +
      "claim is, and a claim rests on knowing what was done.",
    "Call it understanding debt: an agent can build a working stage faster than its owner can " +
      "understand it. Technical debt slows the next change. Understanding debt undermines the " +
      "claim.",
    REFRAIN,
  ],
  stripCaption: "The last tick is this page.",
  callouts: [
    {
      kind: "agent",
      title: "Who did what",
      body: [
        "The agent wrote the rules, ran the jobs, measured the resources and recorded the " +
          "manifests. The human asked, read, decided and caught.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const question = {
  header: "The question",
  lede:
    "A chest radiograph at 224 pixels, and the textbook's checklist of what to look for. The " +
    "model has read the textbook. How much of the checklist does it see?",
  body: [
    "The concept bank is the study's prior knowledge, committed before any call was bought. Each " +
      "dataset gets a short list of visual features on ordered scales; each level carries the " +
      "anchor text the model is shown, and its citation; each class gets a fingerprint over " +
      "the same features.",
    "The concept prompt never names a class. The zero-shot prompt never mentions a concept. We " +
      "ask what the model's answers are worth in the currency a practitioner cares about: " +
      "labelled images.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Pinned inputs",
      body: [
        "The bank, the MedMNIST release and the published benchmarks are fixed before the " +
          "workflow runs, with recorded checksums. No rule refetches or re-derives them.",
        "Prevents: an input that changes under a result while nothing in the record says so.",
      ],
      source: "WORKFLOW.md §5, principle 3",
    },
    {
      kind: "agent",
      title: "A bank no clinician has read",
      body: [
        "Every feature and fingerprint carries a citation, and the smoke tests hold each file to " +
          "a schema. Expert review is simulated, and each file says so.",
        "The debt is repaid by citations, not authority: a reader can check any anchor text " +
          "against its source.",
      ],
      source: "CONCEPT_BANK.md; data/concepts/*.yaml",
    },
  ] as Callout[],
};

export const design = {
  header: "Five arms, seven hypotheses, rules before numbers",
  lede:
    "Two arms use no labels. Three use n labels and the same classifier, and differ only in the " +
    "features that reach it.",
  body: [
    "A vision-language model is a large pretrained model, so the pixel baseline is pretrained " +
      "too: frozen ImageNet features under the same classifier, the same regularisation search " +
      "and the same nested subsets as the concept arm.",
    "Every arm predicts on the same seeded test sample, so every comparison is paired and " +
      "carries a bootstrap interval — 95% of resampled test sets. Across datasets, a one-sided " +
      "sign test — count the datasets the arm won — decides each rule. AUC is the metric " +
      "throughout: 1.0 ranks every case correctly, 0.5 is chance.",
  ],
  limits: [
    "The three organ datasets are one set of CT volumes in three planes, so twelve datasets are " +
      "at most ten independent units. The per-dataset differences are shown so a reader can " +
      "recount.",
    "chestmnist is multi-label, so a nearest fingerprint and a class distribution are undefined " +
      "for it. It runs in arms C, P and C+P only.",
    "The rules were restated for twelve datasets when six verdicts were already known. The " +
      "twelve-dataset threshold reproduces the six-dataset rule exactly, so nothing already " +
      "decided moved; only the six new datasets are pre-registered at it.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "The unfair baseline",
      body: [
        "The first plan set a ResNet trained from scratch on fifty images against a model with " +
          "billions of pretrained parameters. Every rule could have been correct and the headline " +
          "claim still true by construction.",
        "A person reading the plan caught it before any rule existed. The from-scratch network " +
          "became the ceiling; the baseline became a linear probe on ImageNet features.",
      ],
      source: "CHANGELOG.md 2026-09-09",
    },
    {
      kind: "principle",
      title: "Pre-registration in git",
      body: [
        "A rule counts only if it precedes its numbers. Here that is checkable: the commit " +
          "carrying each rule is an ancestor of the commit carrying its numbers. Turn a card " +
          "over and it names both.",
        "Prevents: an arm designed after the results, which decides nothing.",
      ],
      source: "WORKFLOW.md §2 and §10",
    },
  ] as Callout[],
};

export const machine = {
  header: "The machine",
  lede:
    "Seven stages, one file, every number with a rule. Every raw model response is archived with " +
    "the served model name and the prompt hash, and everything downstream is a function of that " +
    "archive.",
  body: [
    "A chunk is one job's hundred images. A reader is a model plus a reasoning effort, so the " +
      "same model asked to think harder counts as a second reader.",
    "The archive is write-protected once written, so re-querying the service is a decision, not " +
      "something a stale timestamp can trigger. The call below is drawn at random, so no two " +
      "people in the room see the same one.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "One chunk before 270",
      body: [
        "Four scoring rules were generated in a loop, and all four inherited the last iteration's " +
          "command. The first chunk, run alone on purpose, came back with the primary model in its " +
          "file name and another model in served_model.",
        "Had the fan-out gone out, one model would have written every archive, and the scale " +
          "hypothesis would have compared four copies of it. The rules are now written out by " +
          "hand, and the stage refuses a mismatch before its first call.",
      ],
      source: "CHANGELOG.md 2026-09-11",
    },
    {
      kind: "principle",
      title: "An explicit model boundary",
      body: [
        "Responses are archived raw, with the served model and the prompt hash. The archive is " +
          "write-protected. Everything downstream is deterministic given it.",
        "Prevents: a result that cannot be recomputed because the model behind it moved.",
      ],
      source: "WORKFLOW.md §5, principle 7",
    },
  ] as Callout[],
};

export const h1 = {
  header: "H1 — Is the textbook worth labelled images?",
  lede:
    "Arm B, the textbook readout, is a horizontal line drawn with no labels. n_B is how many " +
    "labels the pixel arm needs to reach it: what the textbook was worth.",
  body: [
    "The rule was fixed before the numbers existed, and the numbers do not meet it. A negative " +
      "result you can stand behind is what the recipe is for.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "The wave that wrote nothing",
      body: [
        "Forty-eight jobs ran for two hours and wrote no chunks. Each was killed at its time " +
          "limit, and a chunk that times out loses every call it made.",
        "A call that takes a second and a half alone took forty-three seconds under our own " +
          "load. Latency grew almost in step with concurrency: forty-eight jobs bought about two " +
          "and a half times the throughput of one. On an endpoint this close to saturation the " +
          "cap is politeness, and the runtime request decides whether a chunk saves anything.",
      ],
      source: "CHANGELOG.md 2026-09-12",
    },
  ] as Callout[],
};

export const h2 = {
  header: "H2 — The bank, or just the model?",
  lede:
    "Asking the model for the diagnosis beats the textbook readout on most tasks. Yet permuting " +
    "the fingerprints or the concept columns destroys both arms, so the concept answers carry " +
    "real class information. The readout loses it.",
  body: [
    "Where the model can name the class, asking for the name wins; where it cannot, the " +
      "checklist does.",
    "The two arms are separate calls on separate prompts, so the comparison cannot be circular. " +
      "The first design returned both from one call, which would have let the concept answers " +
      "rationalise a class the model had already chosen.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "The field we did not read",
      body: [
        "One model returned nothing readable on three thousand calls. A single diagnostic call " +
          "found its answers, as finished JSON, under a third message field the reader did not " +
          "know.",
        "The archive could not repair it. It held the text our code had extracted, not the " +
          "message, and when the extraction was wrong the calls had to be bought again. The whole " +
          "message object is archived now.",
      ],
      source: "CHANGELOG.md 2026-09-11",
    },
  ] as Callout[],
};

export const h3 = {
  header: "H3 and H7 — Does a bigger model read better?",
  lede:
    "Two open families, 9B to 27B and 12B to 31B: no trend. One closed family ordered only by " +
    "price — gpt-5.6-luna, then terra, then sol: the top beats the bottom.",
  body: [
    "Read within family. Size and training data are confounded across families, both size steps " +
      "also change quantisation, and the qwen step changes generation. Larger travels with newer.",
    "Nothing public orders the closed models by size, so price stands in for capability. " +
      "Whatever separates luna from sol is not what parameter count captured.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "The exact model name, never an alias",
      body: [
        "The service's aliases point at whatever it considers best today. An archive bought " +
          "against an alias will answer differently next month, and nothing on disk will say so. " +
          "Every model here is named exactly, and the served name comes back in every manifest.",
        "Prevents: an archive whose model quietly changed underneath it.",
      ],
      source: "docs/rcd_llm_service.md",
    },
    {
      kind: "agent",
      title: "The service's metadata, not a probe call",
      body: [
        "Asked which models could see images and how hard each could think, the agent read the " +
          "service's model metadata rather than buying probe calls. That corrected the study's " +
          "belief about which models take an image, and it is why the frontier reader is compared " +
          "at matched effort: the gateway rejects the lowest setting.",
      ],
      source: "SESSION_LOG.md 2026-09-12 15:20; docs/rcd_llm_service.md",
    },
  ] as Callout[],
};

export const h4 = {
  header: "H4 and H6 — What if the model thinks?",
  lede:
    "One day, by the clock. A standing claim overturned at 15:20; a decision rule written at " +
    "16:05, before a call was bought; one chunk run first at 16:12; a wave capped at 17:35 after " +
    "a timed call said it would not finish.",
  body: [
    "Thinking is conditional. It rescues the tasks the model read badly and costs the ones it " +
      "read well, and a frontier model reads no better than a 27B open model at matched effort. A " +
      "null here is a result: if thinking does not move the answers, the model's reading is not " +
      "attention-limited.",
    "The coda. The archive showed the frontier model collapsing one dermoscopy concept to a " +
      "single answer on most images. A hypothesis was registered that lowering its effort would " +
      "fix that dataset. It did, and nothing else moved.",
    "Two limits. The frontier model is closed and of unknown size, so the step is capability, " +
      "not parameters. It also refuses temperature zero, so it is the one reader whose answers " +
      "are sampled, and some of any difference is noise the bootstrap cannot see.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "A decision rule before the calls",
      body: [
        "An arm worth adding is worth pre-registering; anything that cannot be is a separate " +
          "study. The thinking step, the effort step and the price ladder each had a rule " +
          "committed before their calls were bought.",
        "Prevents: an arm that can only be reported, never decided.",
      ],
      source: "WORKFLOW.md §10",
    },
    {
      kind: "agent",
      title: "An arm added after the numbers, removed the same day",
      body: [
        "At the owner's request a fifth arm handed the model the whole bank and asked the " +
          "zero-shot question. It cost three thousand calls and measured something real: the " +
          "fingerprint readout is lossy, and the bank is not news to the model.",
        "It was removed because it was designed after the results and so could decide nothing, " +
          "and an arm that decides nothing needs a warning label in every table it touches. The " +
          "change log keeps what it measured.",
      ],
      source: "CHANGELOG.md 2026-09-12; WORKFLOW.md §10",
    },
    {
      kind: "nearmiss",
      title: "A runtime request that costs everything",
      body: [
        "Eleven thinking chunks went out at once, and a timed call came back at over two " +
          "minutes. The wave was cancelled and capped at four in flight: not for throughput, which " +
          "is flat for the thinking reader, but so that each chunk finishes inside its limit.",
        "A chunk that overruns writes nothing, and the archive cannot say how far it got.",
      ],
      source: "CHANGELOG.md 2026-09-12",
    },
  ] as Callout[],
};

export const h5 = {
  header: "H5 — Does the textbook add anything?",
  lede:
    "The first supported hypothesis, and the one that changes what the others mean. Concept " +
    "answers concatenated to pixel features, under the same classifier, gain a little at fifty " +
    "labels on nearly every task.",
  body: [
    "H1 asked whether concept scores can replace pixel features and answered no. H5 asks whether " +
      "they carry anything pixels lack. Two blocks can be unequal and still complementary.",
    "The textbook cannot replace labels. It adds something the pixels do not carry.",
    "One limit: a dozen concept columns join 512 pixel columns under one L2 penalty, so a small " +
      "real contribution can be regularised away. A per-block penalty would be a different, " +
      "unregistered model.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "Two sessions, one checkout",
      body: [
        "A second agent session, unaware of the first, switched the shared checkout onto its own " +
          "branch mid-run. Jobs read the working tree when they start, so five of twelve classify " +
          "outputs were written by the wrong code.",
        "Each manifest's git_commit named the culprit before any theory did. Read the manifest " +
          "first.",
      ],
      source: "SESSION_LOG.md 2026-09-13 12:25",
    },
  ] as Callout[],
};

export const verdicts = {
  header: "Seven verdicts",
  body: [
    "Against the published fully supervised ceiling, the pixel arm at its largest labelled " +
      "subset sits just below; the best zero-label arm sits far below. Labels close the gap. The " +
      "textbook does not, though it adds a little on top of them.",
    "The published numbers are a ceiling, not an arm: each was trained on a dataset's whole " +
      "training split, not this study's pool.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "A manifest with every result",
      body: [
        "Parameters, seeds, commit, versions, host and wall time travel with every result file.",
        "Prevents: a number nobody can trace to the run that made it.",
      ],
      source: "WORKFLOW.md §5, principle 5",
    },
  ] as Callout[],
};

export const close = {
  header: "What four days cost",
  body: [
    "None was caught by the dependency graph. A person reading the plan; one chunk run before " +
      "the rest; a probe at the wire; a timed call; a manifest field. The graph shows that a stage " +
      "exists and what it depends on, not whether it computes the right thing.",
    "The workflow gives you half the record for free: what was done, in what order, from what, " +
      "with which code. The session log is the other half: why. You need both.",
  ],
  callouts: [
    {
      kind: "agent",
      title: "Understanding debt, and what repaid it",
      body: [
        "Every stage the agent wrote faster than its owner could read it is a loan. Four " +
          "practices repaid it. Read every rule before it runs at scale. Run one cell first. " +
          "Make the agent explain the stage, then judge the explanation — a wrong explanation " +
          "shows where a wrong line does not. Keep the change log as the owner's record, not " +
          "the agent's.",
        "The agent produces the evidence. The claim remains the author's.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const explore = {
  header: "Explore",
};

/* Two lists, because two of these are what a room asks about and two are not. The first is on
   the main scroll at #verdicts; the second waits in the explorer. */
export const notClaimed = [
  "The concept scores are not clinically validated.",
  "Every source dataset is public and labelled, so “the model carries textbook knowledge” " +
    "and “the model has seen this benchmark” cannot be told apart with these data.",
];

export const notClaimedMore = [
  "Simulated expert review is not a clinician's.",
  "No arm here is state of the art.",
];
