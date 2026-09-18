/* The talk's prose. Authored here, drawn from TALK.md, WORKFLOW.md, CHANGELOG.md and
   SESSION_LOG.md - quoted or paraphrased faithfully, with the study's stated limits kept and
   nothing invented. NO NUMBER IS WRITTEN HERE: every figure on the page comes through the export
   in `public/data/`. Where a sentence needs a number it is assembled in the section component
   from the snapshot.

   Twenty-five minutes, twelve sections: two and a half minutes each. The spine is short and the
   depth is one level down - a collapsed panel beside the thing it belongs to, or Extra.

   There is one kind of callout and it is labelled Note. A note earns its place only if it says
   something genuinely different about doing science with an AI coding agent, or something
   genuinely surprising. Ordinary good practice does not qualify, and a section with nothing that
   clears the bar has no note.

   The division of labour with the bullets matters: bullets carry the facts and the numbers, and
   the speaker supplies the meaning. A bullet that states a conclusion belongs in a callout.

   Plain words. No version-control or developer vocabulary - no commits, branches, checkouts,
   repositories or schemas - except the terms the page itself teaches and is about: Snakemake,
   arm, probe, AUC, chunk, reader, concept bank.

   One name per thing, and it names the thing rather than its shape. The visual features and the
   levels expected for each class were compiled from the published literature - the scholarly
   record - and not from a textbook, so the page says "the literature" and never "the textbook".
   The literature's list is "visual features"; what the model returns for them is "feature scores"
   or "scored visual features"; what arms C, P and C+P each fit is a "classifier". Not
   "checklist", which says a list is being checked without ever saying of what.

   Style: short sentences, a doer as the subject and its action as the verb, one idea each. Say
   what happened; let the reader judge it. */

export interface Callout {
  title: string;
  body: string[];
  source: string;
}

/** One kind of callout, one label. A reader should not have to keep a taxonomy in their head. */
export const NOTE_LABEL = "Note";

export const REPO = "https://github.com/dhudsmith/textbook_priors";

export const LINKS = [
  { label: "the code, and everything behind this page", href: REPO },
  { label: "WORKFLOW.md — the plan and the seven hypotheses", href: `${REPO}/blob/main/WORKFLOW.md` },
  { label: "CHANGELOG.md — my dated record of what I understood, and when", href: `${REPO}/blob/main/CHANGELOG.md` },
  { label: "SESSION_LOG.md — how the agent was directed, to the minute", href: `${REPO}/blob/main/SESSION_LOG.md` },
  { label: "CONCEPT_BANK.md — how the bank was built", href: `${REPO}/blob/main/CONCEPT_BANK.md` },
  { label: "the Snakefile", href: `${REPO}/blob/main/Snakefile` },
];

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
    header: "How the project is structured",
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
  /* The second half of the section: what the published literature says these images contain.
     The number of sources is filled from the bank files themselves in Question.tsx. */
  bank: {
    header: "What the literature says to look for",
    lede:
      "For each task, a short list of visual features a clinician is taught to check, taken " +
      "from the published papers. The model may have read the same papers.",
    bulletShapes: [
      "{minConcepts} to {maxConcepts} features per task, each on an ordered scale",
      "Every level carries the wording the model is shown, and a citation for it",
      "{sources} sources from the literature, cited across the {datasets} tasks",
      "For each class, the level the literature expects for every feature",
      "Written down before any call went out",
    ],
  },
  callouts: [
        {
      title: "No clinician has read this bank",
      body: [
        "The bank was compiled by a model — Claude Opus 5 — from the published papers, and " +
          "every feature and every level it expects carries a citation. No clinician has read " +
          "them. The review is simulated too, and each file says so.",
        "A citation lets a reader check the claim. A credential only lets them defer to it.",
      ],
      source: "CONCEPT_BANK.md; data/concepts/*.yaml",
    },
  ] as Callout[],
};

export const design = {
  headerShape: "{arms} classification arms",
  lede: "What is the literature worth in labelled images? Two arms use none. Three use n.",
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
  header: "The compute workflow",
  /* Four short lines and a logo. The long version - what a rule is, what make does, the three
     words the project uses for its own parts - was cut on 2026-09-19: too long and too much
     jargon for a slide the room reads in ten seconds. The table and the graph below say the
     rest, for anyone who wants it. */
  lede: "Use a workflow manager (Snakemake in this case) to structure the compute:",
  bullets: [
    "Tells the AI what context to pull",
    "Shows me what the AI built",
    "Maps what depends on what, and re-runs what a change touches",
    "Tames the pile of scripts",
  ],
};

/* The one image every later number is made of. The heading stands alone: the widget under it
   shows what it is, and a lede saying so in words was noise in front of it. */
export const sample = {
  header: "Model input and output",
};

/* The headline results figure, and the three questions it answers. The per-question detail sits
   in panels beside it, closed; model size and the price comparison moved out to Extra. */
export const results = {
  header: "Test AUC for each arm",
  ledeShape:
    "Every arm on the same chart: how well it separates the classes, against how many " +
    "labelled images it was given. One model read every image here — {primary}. Arm P uses " +
    "no model at all. Pick a question and the figure draws the arms that answer it.",
  bulletShapes: [
    "Arms given no labels are flat lines; arms given labels climb",
    /* "95% intervals" said nothing about where they came from. The numbers are the run's own. */
    "Shaded bands are the middle {ci}% over {boot} bootstrap resamples of the test images, " +
      "every arm recomputed on each resample — hover a point to read one",
  ],
  /* One chip each. `hidden` is the preset: the series the figure starts without. */
  choices: [
    {
      id: "h1",
      chip: "Can the literature replace labels?",
      asks:
        "Three arms: the feature scores read against what the literature expects, with no " +
        "labels; a classifier fitted on pretrained image features; and a second classifier " +
        "fitted the same way on the feature scores.",
      hidden: ["CP", "A", "lit"],
    },
    {
      id: "h2",
      chip: "Score the features, or just ask for the diagnosis?",
      asks:
        "Two prompts on the same image, neither using a label: name the diagnosis, or score " +
        "the visual features and match those scores to the literature's description of each " +
        "class.",
      hidden: ["C", "P", "CP", "lit"],
    },
    {
      id: "h5",
      chip: "Does the literature add to the image features?",
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
  /* "and then {frontier} in its place" was too compressed to read: it was not clear what took
     whose place, or that the effort was held fixed so that the swap is the only change. */
  ledeShape:
    "Two steps, one change each. First {primary} with no thinking step, then the same model " +
    "told to think before it answers. Then {frontier} in place of it, thinking just as hard, so " +
    "the second step changes the model and nothing else. Every reader is compared on the same " +
    "images, by the same procedure.",
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
    "The literature cannot replace labelled images",
    "Added to them, it adds a small but consistent gain",
  ],
  /* The plain-language reading of each question, for the one column a listener actually reads.
     H3 and H7 are presented nowhere else, so their sentences name the comparison outright. */
  asks: {
    h1: "With no labels at all, do the feature scores read against what the literature expects " +
      "beat pretrained image features given the smallest labelled set?",
    h2: "Does scoring the visual features the literature names beat simply asking the model for " +
      "the diagnosis?",
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

/* The last section of the talk, and the one the speaker speaks from. These are his words,
   lightly edited for the page; they stay bullets rather than becoming paragraphs. The three
   under `added` were written by the agent and are kept apart so he can see which are his. */
export const takeaways = {
  header: "Takeaways",
  /* Arrowed through one at a time rather than read as a list: these are the speaker's own
     points, and a room that can read ahead has stopped listening. Ten as they were first
     written, combined here where two were the same point twice. */
  cards: [
    "It feels like magic: whatever I can imagine adding to this study, I can speak into my " +
      "phone and it goes. With great power comes great responsibility.",
    "But this was too fast. My understanding has not caught up with the work that was done, and " +
      "I had big surprises, while making this talk, about how the workflow actually worked. " +
      "That is not a good situation.",
    "There is a big gap between this and what I would need, as a scientist, before publishing " +
      "it.",
    "A workflow manager like Snakemake is useful twice: as context for the AI, and as a way for " +
      "me to see what the AI built. It documents the design instead of leaving a pile of " +
      "scripts.",
    "Moving toward AI-generated work means being more prescriptive about your standards, " +
      "because they will not be enforced implicitly. Keep the distance between what you want " +
      "and what the AI produces as small as possible.",
    "Generating this talk was the bottleneck: it took far more of my input than the scientific " +
      "work did. Presentation is still hard for AI. I have a model of the audience, the AI's is " +
      "very different, and closing that gap is not finished.",
  ],
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
  "Every source dataset is public and labelled, so “the model carries knowledge from the " +
    "literature” and “the model has seen this benchmark” cannot be told apart with these data.",
];

/* The model comparison, back on the spine right after the results figure and out of Extra. One
   chart with two views and one sentence of what it found: it was cut for length once, so it
   stays under two minutes and carries nothing else. */
export const modelSize = {
  header: "Model size and price",
  toggle: { open: "open models, by size", closed: "closed models, by price" },
  captions: {
    open: "One line per dataset across the four open models, in size order within family. " +
      "Hover a line to isolate it.",
    closed: "One line per dataset across the three closed models, in price order. Hover a line " +
      "to isolate it.",
  },
  notes: {
    /* Why four lines out of twelve carry a colour and a name: the ladder names the widest
       spreads and greys the rest, which the chart cannot say for itself. */
    open: "The divider separates the two families, and the comparison is within a family only. " +
      "Only the datasets with the widest spread between their highest and lowest point are named and coloured; the rest stay grey, and hovering any line isolates it.",
    closed: "One classifier per model, all fitted the same way. Price is the vendor's ranking, " +
      "not a parameter count. Only the datasets with the widest spread between their highest and lowest point are named and coloured; the rest stay grey, and hovering any line isolates it.",
  },
};
