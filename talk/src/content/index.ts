/* The talk's prose. Authored here, drawn from TALK.md, WORKFLOW.md, CHANGELOG.md and
   SESSION_LOG.md - quoted or paraphrased faithfully, with the study's stated limits kept and
   nothing invented. NO NUMBER IS WRITTEN HERE: every figure on the page comes through the export
   in `public/data/`. Where a sentence needs a number it is assembled in the section component
   from the snapshot.

   Twenty-five minutes, ten sections: two and a half minutes each. The spine is short and the
   depth is one level down - a collapsed panel beside the thing it belongs to, or Extra.

   A callout earns its place only if it is a principle about what is genuinely different about
   doing science with an AI coding agent, or an observation that is genuinely surprising. Ordinary
   good practice does not qualify, and a section with nothing that clears the bar has no callout.

   The division of labour with the bullets matters: bullets carry the facts and the numbers, and
   the speaker supplies the meaning. A bullet that states a conclusion belongs in a callout.

   Plain words. No version-control or developer vocabulary - no commits, branches, checkouts,
   repositories or schemas - except the terms the page itself teaches and is about: Snakemake,
   arm, probe, AUC, chunk, reader, concept bank.

   One name per thing, and it names the thing rather than its shape. The textbook's list is
   "visual features"; what the model returns for them is "feature scores" or "scored visual
   features"; what arms C, P and C+P each fit is a "classifier". Not "checklist", which says a
   list is being checked without ever saying of what.

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
  { label: "the code, and everything behind this page", href: REPO },
  { label: "WORKFLOW.md — the plan and the seven hypotheses", href: `${REPO}/blob/main/WORKFLOW.md` },
  { label: "CHANGELOG.md — my dated record of what I understood, and when", href: `${REPO}/blob/main/CHANGELOG.md` },
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
  eyebrow: "Clemson HPC Day · 18 September 2026",
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
  effortCaptionShape:
    "Prompts, code, jobs and calls over {days} days.",
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
  header: "Medical images and associated visual features",
  lede:
    "To answer that I need medical images with labels. MedMNIST v2 is a standard benchmark " +
    "suite: every 2D task in the release, one preprocessing, one set of splits.",
  /* The counts are filled in from the snapshot in Question.tsx. */
  bulletShapes: [
    "{datasets} 2D tasks: chest X-ray, dermoscopy, OCT, ultrasound, blood and tissue cells, " +
      "pathology slides, retinal photographs, and abdominal CT in three planes",
    "Binary, multi-class, ordinal and one multi-label problem, from {minClasses} to " +
      "{maxClasses} classes",
    "Official splits, untouched, at 224 pixels",
    "Published, so there is a fully supervised number to compare against",
  ],
  /* The second half of the section: what a textbook says these images contain. */
  bank: {
    header: "What the textbook says to look for",
    lede:
      "For each task, a short list of visual features a clinician is taught to check. The " +
      "model may have read the same textbooks.",
    bulletShapes: [
      "{minConcepts} to {maxConcepts} features per task, each on an ordered scale",
      "Every level carries the wording the model is shown, and a citation for it",
      "For each class, the level the textbook expects for every feature",
      "Written down before any call went out",
    ],
  },
  callouts: [
        {
      kind: "agent",
      title: "No clinician has read this bank",
      body: [
        "The bank was compiled by a model — Claude Opus 5 — from the literature, and every " +
          "feature and every level it expects carries a citation. No clinician has read them. " +
          "The review is simulated too, and each file says so.",
        "A citation lets a reader check the claim. A credential only lets them defer to it.",
      ],
      source: "CONCEPT_BANK.md; data/concepts/*.yaml",
    },
  ] as Callout[],
};

export const design = {
  headerShape: "{arms} classification arms",
  lede: "What is the textbook worth in labelled images? Two arms use none. Three use n.",
  bullets: [
    "Three arms each fit their own classifier — fitted the same way, on different features",
    "Every comparison is paired: the same test images for every arm",
    "AUC throughout: 1.0 perfect, 0.5 chance",
  ],
  limits: [
    "The three organ datasets are one set of CT volumes in three planes, so twelve datasets are " +
      "at most ten independent units. Every per-dataset difference is shown, so anyone can count " +
      "them again.",
    "chestmnist marks several findings at once rather than one class, so arms A and B cannot " +
      "be defined for it. It runs in C, P and C+P only.",
  ],
};

/* The models, between the arms and how the study is built. Short by design: the room needs to
   know what was asked before the results start naming families, efforts and open weights. Every
   column earns its place by answering a question asked later, and the bullets say which. */
export const models = {
  header: "Models tested",
  lede:
    "Every number in this talk starts with a model looking at an image. These are the models " +
    "that did.",
  bullets: [
    "Family and size — one question asks whether a bigger model in the same family reads better",
    "Thinking — a later section asks what happens when the model is allowed to think",
    "Open or closed weights — nobody outside the vendor can rerun a closed model's answers",
    "Calls — where the work went",
  ],
  sizeNote:
    "The closed family publishes neither its size nor its thinking settings. Price is the only " +
    "thing that ranks it, and the settings shown are the ones this study could use; none of them " +
    "turns thinking off.",
};

export const machine = {
  header: "How the study runs",
  lede: "Seven stages, one file, every number with a rule.",
  bullets: [
    "A chunk is one job's hundred images",
    "A reader is a model plus a reasoning effort",
    "Once a reply is written it stays written: buying the calls again has to be deliberate",
  ],
};

/* The headline results figure, and the three questions it answers. The per-question detail sits
   in panels beside it, closed; model size and the price comparison moved out to Extra. */
export const results = {
  header: "Test AUC for each arm",
  ledeShape:
    "Every arm on the same chart: how well it separates the classes, against how many " +
    "labelled images it was given. One model read every image here — {primary}. Arm P uses " +
    "no model at all. Pick a question and the figure draws the arms that answer it.",
  bullets: [
    "Arms given no labels are flat lines; arms given labels climb",
    "Shaded bands are 95% intervals — hover a point to read one",
  ],
  /* One chip each. `hidden` is the preset: the series the figure starts without. */
  choices: [
    {
      id: "h1",
      chip: "Can the textbook replace labels?",
      asks:
        "Three arms: the feature scores read against the textbook with no labels, a classifier " +
        "fitted on pretrained image features, and a second classifier fitted the same way on " +
        "the feature scores.",
      hidden: ["CP", "A", "lit"],
    },
    {
      id: "h2",
      chip: "Score the features, or just ask for the diagnosis?",
      asks:
        "Two prompts on the same image, neither using a label: name the diagnosis, or score " +
        "the visual features and match those scores to the textbook's description of each class.",
      hidden: ["C", "P", "CP", "lit"],
    },
    {
      id: "h5",
      chip: "Does the textbook add to the image features?",
      asks:
        "A classifier fitted on pretrained image features, then a second one, fitted the same " +
        "way, on those features with the feature scores alongside them. Nothing else changes.",
      hidden: ["A", "B", "C", "lit"],
    },
  ],
  /* Kept for the panel that answers the obvious objection to the second question. */
  circular: [
    "The two arms are separate calls on separate prompts, so the comparison cannot be circular. The first design returned both from one call, which would have let the feature scores be written to fit a class the model had already chosen.",
  ],
};

export const thinking = {
  header: "What if the model thinks?",
  ledeShape:
    "{primary}, told to think before it answers — and then {frontier} in its place. Every reader " +
    "is compared on the same images, by the same procedure.",
  bullets: [
    "Thinking helps where the model read badly and hurts where it read well",
    "The frontier model reads no better than the open one it replaced",
    "More thinking is not what the model lacked",
  ],
  /* Kept for the collapsed panel of limits. */
  limits: [
    "The frontier model is closed and its size is not published, so this step changes capability rather than parameter count. It also refuses to answer deterministically, so it is the one reader whose answers vary between calls, and some of any difference is noise the intervals cannot see.",
  ],
};

export const verdicts = {
  header: "Seven verdicts",
  /* Filled in Verdicts.tsx: which model each row rests on. */
  modelsNote:
    "Five of these rest on one model, {primary}. The other two compare models: one across the " +
    "open families, one across the closed models ranked by price.",
  bullets: [
    "The textbook cannot replace labelled images",
    "Added to them, it adds a small but consistent gain",
  ],
  /* The plain-language reading of each question, for the one column a listener actually reads.
     H3 and H7 are presented nowhere else, so their sentences name the comparison outright. */
  asks: {
    h1: "With no labels at all, do the feature scores read against the textbook beat " +
      "pretrained image features given the smallest labelled set?",
    h2: "Does scoring the textbook's visual features beat simply asking the model for the " +
      "diagnosis?",
    h3: "Within each open model family, does the bigger model read the images better than the " +
      "smaller one?",
    h4: "Does a better reader — told to think, or a stronger model — get more out of the same " +
      "images?",
    h5: "Added to pretrained image features, do the feature scores carry anything those " +
      "features do not already have?",
    h6: "Was the frontier model asked to think too hard? Lower its effort and see.",
    h7: "Among closed models ranked only by price, does the most expensive score the visual " +
      "features better than the cheapest?",
  } as Record<string, string>,
};

export const close = {
  header: "What four days cost",
  bullets: [
    "The graph shows a stage exists, not that it computes the right thing",
    "The workflow gives you what was done, for free",
    "The session log is the other half: why it was done. You need both.",
  ],
  callouts: [
    {
      kind: "agent",
      title: "Understanding debt",
      body: [
        "Every stage the agent wrote faster than I could read it is a loan.",
        "Four things repaid it. Read every rule before it runs at scale. Run one chunk before the rest. Make the agent explain the stage, then judge the explanation. Keep the change log yourself.",
        "The agent produces the evidence. The claim stays yours.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const explore = {
  header: "Extra",
};

/* What the study does not claim. Off the main scroll: it is what a room asks about rather than
   something twenty-five minutes has time to walk through. */
export const notClaimed = [
  "The feature scores are not clinically validated.",
  "A simulated expert review is not a clinician's review.",
  "No arm here is state of the art.",
  "Every source dataset is public and labelled, so “the model carries textbook knowledge” " +
    "and “the model has seen this benchmark” cannot be told apart with these data.",
];

/* H3 and H7 left the talk: the detail is in Extra and the verdict table is where the room meets
   them. This is the prose that went with the model comparison. */
export const ladderExtra = {
  header: "Does a bigger model read better?",
  ledeShape:
    "Two open families, {qLo}B to {qHi}B and {gLo}B to {gHi}B, then a closed family ranked only " +
    "by price — gpt-5.6-luna, then terra, then sol.",
  bullets: [
    "Read within family only: the larger models are also the newer ones",
    "Both size steps also change the numerical precision the model runs at",
    "Nothing public ranks the closed models, so price is the only order there is",
    "Whatever separates them, parameter count did not capture it",
  ],
};
