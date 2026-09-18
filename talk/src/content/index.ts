/* The talk's prose. Authored here, drawn from TALK.md, WORKFLOW.md, CHANGELOG.md and
   SESSION_LOG.md - quoted or paraphrased faithfully, with the study's stated limits kept and
   nothing invented. NO NUMBER IS WRITTEN HERE: every figure on the page comes through the export
   in `public/data/`. Where a sentence needs a number it is assembled in the section component
   from the snapshot.

   Callouts carry the observations - the argument, the lesson, the thing worth saying out loud.
   Never a record of who did what. A blue PRINCIPLE is a practice and the failure it avoids; an
   amber NEAR MISS is what nearly went wrong and what caught it, never the DAG; a violet AGENT
   NOTE is what working this way with an agent taught us.

   The division of labour with the bullets matters: bullets carry the facts and the numbers, and
   the speaker supplies the meaning. A bullet that states a conclusion belongs in a callout.

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

/* ------------------------------------------------------------------------------------------ */

export const title = {
  header: "Reproducible Scientific Computing with AI Coding Agents",
  byline: { who: "D. Hudson Smith", where: "School of Mathematical and Statistical Sciences" },
  standfirst:
    "How much of the research process can we give to a coding agent? What do we gain? What do we lose?",
  intro: {
    lede:
      "To make that concrete, we start a new project — one that had been sitting at the back of " +
      "my mind for a while:",
    question: "Can out-of-the-box vision-language models (VLMs) classify medical images?",    
    bullets: [
      "Lots of details but straightforward",
      "Could use a cluster",
      "Interests me",
      "Something that could be done in a week!",
      "Bonus: can use the RCD LLM service ;)"
    ],
  },
  workflow: {
    header: "How the study is put together",
    lede:
      "Trying to get AI to do it the way I want.",
    caption:
      "Solid arrows are data. Dashed arrows are authorship — what the agent wrote, rather than " +
      "what the workflow ran.",
  },
  qr: "Follow along on your own device",
};

export const premise = {
  header: "How the work unfolded.",
  lede:
    "Planned in a day. Built, run and reported in three more. An agent wrote most of the code.",
  /* The numbers are assembled in Premise.tsx from the export, per this file's own rule: the
     prompt count alone moved twice in a day. The wording is the owner's. */
  bulletShapes: [
    "{prompts} prompts set off {jobs} Palmetto jobs.",
    "{calls} calls to the RCD LLM service.",
    "{machineHours} hours of machine time.",
    "Tested {hypotheses} distinct hypotheses on {datasets} medical image datasets.",
  ],
  effortCaption:
    "Prompts and commits are moments. Jobs are the periods they ran. The calls are a rate.",
  callouts: [
    {
      kind: "agent",
      title: "The outputs are not the product",
      body: [
        "The model's outputs are not the product of science. The claims are.",
        "So what evidence do we have, and how far can we trust it? Understanding debt accrues very fast if you are not careful.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const question = {
  header: "What we asked the model",
  lede:
    "A chest radiograph at 224 pixels, and the textbook's checklist of what to look for. How " +
    "much of that checklist does the model see?",
  bullets: [
    "The concept bank is committed before any call goes out",
    "Visual features on ordered scales, every level cited",
    "The concept prompt never names a class",
    "The zero-shot prompt never mentions a concept",
    "Everything is measured in labelled images",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Pin the inputs",
      body: [
        "The bank, the MedMNIST release and the published benchmarks are fixed before the workflow runs, with checksums. No rule refetches or re-derives them.",
        "Otherwise an input changes under a result and nothing in the record says so.",
      ],
      source: "WORKFLOW.md §5, principle 3",
    },
    {
      kind: "agent",
      title: "No clinician has read this bank",
      body: [
        "Every feature and every fingerprint carries a citation. No clinician has read them. Expert review is simulated, and each file says so.",
        "Citations let a reader check the thing. Authority would only let them defer to it.",
      ],
      source: "CONCEPT_BANK.md; data/concepts/*.yaml",
    },
  ] as Callout[],
};

export const design = {
  header: "Five arms, one classifier",
  lede:
    "Two arms use no labels. Three use n labels and the same classifier, and differ only in the " +
    "features that reach it.",
  bullets: [
    "A pretrained model needs a pretrained baseline",
    "One classifier, three arms — only the features differ",
    "Every comparison paired on one seeded test sample",
    "Across datasets, a sign test decides each comparison",
    "AUC throughout: 1.0 perfect, 0.5 chance",
  ],
  limits: [
    "The three organ datasets are one set of CT volumes in three planes, so twelve datasets are " +
      "at most ten independent units. The per-dataset differences are shown so a reader can " +
      "recount.",
    "chestmnist is multi-label, so a nearest fingerprint and a class distribution are undefined " +
      "for it. It runs in arms C, P and C+P only.",
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
      title: "Pre-registration you can check",
      body: [
        "A rule counts only if it precedes its numbers, and here you can check that: the commit carrying each rule is an ancestor of the commit carrying its numbers.",
        "An arm designed after the results decides nothing.",
      ],
      source: "WORKFLOW.md §2 and §10",
    },
  ] as Callout[],
};

export const machine = {
  header: "How the study runs",
  lede:
    "Seven stages, one file, every number with a rule. Every response archived; everything " +
    "downstream a function of that archive.",
  bullets: [
    "A chunk is one job's hundred images",
    "A reader is a model plus a reasoning effort",
    "Write-protected, so re-running the calls has to be deliberate",
    "The call below is drawn at random — yours differs from mine",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "One chunk run before the other 270",
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
      title: "Draw a line where the model is",
      body: [
        "Responses are archived raw, with the served model and the prompt hash, and the archive is write-protected. Everything downstream is a deterministic function of it.",
        "Without that line a result cannot be recomputed once the model moves — and it will move.",
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
  bullets: [
    "The rule was fixed before the numbers existed",
    "The numbers do not meet it",
    "A negative result you can stand behind is worth having",
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
  /* Kept for the collapsed panel that answers the obvious objection. */
  circular: [
    "The two arms are separate calls on separate prompts, so the comparison cannot be circular. The first design returned both from one call, which would have let the concept answers rationalise a class the model had already chosen.",
  ],
  header: "H2 — The bank, or just the model?",
  lede:
    "Asking for the diagnosis beats the textbook readout. But permuting either destroys both " +
    "arms — so the concept answers do carry class information. The readout loses it.",
  bullets: [
    "Where the model can name the class, asking for the name wins",
    "Where it cannot, the checklist does",
    "Permute either one and both arms collapse — the answers carry real information",
    "Separate prompts, separate calls: the comparison cannot be circular",
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
  bullets: [
    "Read within family only: the larger models are also the newer ones",
    "Both size steps also change quantisation",
    "Nothing public ranks the closed models, so price is the proxy",
    "Whatever separates them, parameter count did not capture it",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Name the model, never the alias",
      body: [
        "The service's aliases point at whatever it considers best today. An archive bought against an alias answers differently next month, and nothing on disk says so.",
        "Every model here is named exactly, and the served name comes back in every manifest.",
      ],
      source: "docs/rcd_llm_service.md",
    },
    {
      kind: "agent",
      title: "Read the docs before buying calls",
      body: [
        "Asked which models could see an image, the agent read the service's own metadata instead of spending calls to find out. It corrected what the study believed.",
        "The cheapest experiment is usually the one someone already ran.",
      ],
      source: "SESSION_LOG.md 2026-09-12 15:20; docs/rcd_llm_service.md",
    },
  ] as Callout[],
};

export const h4 = {
  /* Kept for the collapsed panel of limits. */
  limits: [
    "The frontier model is closed and of unknown size, so the step is capability, not parameters. It also refuses temperature zero, so it is the one reader whose answers are sampled, and some of any difference is noise the bootstrap cannot see.",
  ],
  header: "H4 and H6 — What if the model thinks?",
  lede:
    "One day, by the clock. A claim overturned at 15:20. A rule written at 16:05, before a call " +
    "was bought. A wave capped at 17:35.",
  bullets: [
    "Thinking helps where the model read badly and hurts where it read well",
    "A frontier model reads no better than a 27B open model",
    "A null is a result: more thinking is not what the model lacked",
    "Then a prediction, named before the calls: one concept had collapsed, and less effort " +
      "fixed that dataset and nothing else",
    "Limits: closed model, unknown size, and it refuses temperature zero",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Write the rule before you buy the calls",
      body: [
        "An arm worth adding is worth pre-registering. Anything that cannot be is a separate study.",
        "The thinking step, the effort step and the price ladder each had a rule committed before a call was bought.",
      ],
      source: "WORKFLOW.md §10",
    },
    {
      kind: "agent",
      title: "An arm that could decide nothing",
      body: [
        "A fifth arm was added after seeing the numbers. It cost three thousand calls and it measured something real.",
        "It was removed the same day. Designed after the results, it could decide nothing — and an arm that decides nothing needs a warning label in every table it touches.",
      ],
      source: "CHANGELOG.md 2026-09-12; WORKFLOW.md §10",
    },
    {
      kind: "nearmiss",
      title: "A time limit that loses the whole chunk",
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
  bullets: [
    "H1 asked: can concepts replace pixels? No.",
    "H5 asks: do they carry anything pixels lack? Yes.",
    "Unequal and complementary are not the same thing",
    "The textbook cannot replace labels. It adds.",
    "Limit: a dozen concept columns share one penalty with 512 pixel columns",
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
  bullets: [
    "Five not supported, two supported, none chosen",
    "Pixels at the most labels sit just below the published ceiling",
    "The best zero-label arm sits far below it",
    "Labels close the gap; the textbook adds a little on top",
    "The ceiling is not an arm — it trained on the whole split",
  ],
  callouts: [
    {
      kind: "principle",
      title: "A manifest with every result",
      body: [
        "Parameters, seeds, commit, versions, host and wall time travel with every result file.",
        "A number you cannot trace to the run that made it is not evidence.",
      ],
      source: "WORKFLOW.md §5, principle 5",
    },
  ] as Callout[],
};

export const close = {
  header: "What four days cost",
  bullets: [
    "The dependency graph caught none of them",
    "A person reading the plan. One chunk run first. A probe. A manifest field.",
    "The graph shows a stage exists, not that it computes the right thing",
    "The workflow gives you what was done, for free",
    "The session log is the other half: why. You need both.",
  ],
  callouts: [
    {
      kind: "agent",
      title: "Understanding debt",
      body: [
        "Every stage the agent wrote faster than I could read it is a loan.",
        "Four things repaid it. Read every rule before it runs at scale. Run one cell first. Make the agent explain the stage, then judge the explanation. Keep the change log yourself.",
        "The agent produces the evidence. The claim stays yours.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const explore = {
  header: "Extra",
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
