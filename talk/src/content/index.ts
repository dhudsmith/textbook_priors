/* The talk's prose. Authored here, drawn from TALK.md, WORKFLOW.md, CHANGELOG.md and
   SESSION_LOG.md - quoted or paraphrased faithfully, with the study's stated limits kept and
   nothing invented. NO NUMBER IS WRITTEN HERE: every figure on the page comes through the export
   in `public/data/`. Where a sentence needs a number it is assembled in the section component
   from the snapshot.

   Callout kinds are talk/PLAN.md section 1: a blue PRINCIPLE states a reproducibility principle as
   the failure it prevents; an amber NEAR MISS says what nearly went wrong and what caught it -
   never the DAG; a violet AGENT NOTE says what the agent did, what the human had to do, and the
   understanding debt it left or repaid. */

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
  principle: "a reproducibility principle the study relied on, stated as the failure it prevents",
  nearmiss: "something that nearly went wrong, and what caught it — a person, one chunk, a probe, a manifest",
  agent: "what the agent did, what the human had to do, and the understanding debt it left or repaid",
};

/* ------------------------------------------------------------------------------------------ */

export const title = {
  question: "Can a vision-language model's textbook knowledge of what pathology looks like stand in for labelled data?",
  standfirst:
    "Twelve MedMNIST 2D benchmarks. A cited bank of diagnostic visual features. Five arms — two " +
    "that use no labels at all — and seven hypotheses whose decision rules were written before " +
    "their numbers existed. The whole study, from the fixed inputs to the technical report, is " +
    "one Snakemake workflow.",
  qr: "Follow along on your own device",
};

export const premise = {
  header: "This talk was built the way it is about",
  lede:
    "A real study: designed on a Tuesday, run on Thursday and Friday, extended on Saturday, " +
    "reported on Sunday. Nearly every line of code was written by an AI coding agent, under a " +
    "workflow whose job was to make that work inspectable.",
  body: [
    "The turnaround is the point, and so is the question it raises. If you did not compute the " +
      "result yourself — if an agent wrote the stage, submitted the jobs and wrote the table — how " +
      "do you come to trust it? Software engineering has its own answers. Science adds an " +
      "asymmetry: the code is not the product, the claim is, and a claim rests on understanding " +
      "what was done.",
    "That is the challenge this project calls understanding debt. An agent can produce a working " +
      "stage faster than its owner can understand it. The numbers exist, the report cites them, " +
      "and the person whose name is on the work cannot say from memory how they were made. " +
      "Technical debt slows the next change; understanding debt undermines the claim itself.",
    REFRAIN,
  ],
  stripCaption:
    "One tick per prompt that materially directed the work, from SESSION_LOG.md. The kind of " +
    "each entry is the one hand-assigned field in the export; the time and the title are the " +
    "file's own.",
  callouts: [
    {
      kind: "agent",
      title: "What the human did, against what the agent did",
      body: [
        "The agent wrote the rules, ran the jobs, measured the resources and recorded the " +
          "manifests. The human asked, read, decided and caught: every near miss on this page " +
          "was found by a person reading a plan, a chunk run deliberately before the rest, a " +
          "probe at the wire, or a manifest field — never by the dependency graph.",
        "What the workflow repays is what was done, in what order, from what, and with which " +
          "code and settings: the DAG, the dry run and the manifest answer those for free. What " +
          "it does not repay is whether the stage computes the right thing. A rule can be " +
          "structurally perfect and scientifically wrong.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const question = {
  header: "The question",
  lede:
    "One chest radiograph at 224 pixels, beside the textbook's checklist of what to look for. A " +
    "vision-language model has read the textbook. How much of the checklist does it see, and is " +
    "what it sees worth labelled images?",
  body: [
    "The concept bank is the study's prior knowledge, committed as an input before any call was " +
      "bought. Each dataset gets a short list of diagnostic visual features, each with an ordered " +
      "scale, each level carrying the anchor text a reader is shown and the citation it came " +
      "from; and each class gets a fingerprint over those same features. The model never sees a " +
      "class name in the concept prompt, and never sees a concept in the zero-shot prompt.",
    "We ask what those scores are worth in the currency a practitioner cares about: labelled " +
      "images.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Inputs are pinned, so no rule can quietly redefine the question",
      body: [
        "The concept bank, the pinned MedMNIST release and the published literature benchmarks " +
          "are fixed inputs, completed before the workflow runs, with recorded checksums. No rule " +
          "refetches, re-derives or re-verifies them.",
        "The failure it prevents: an input that changes underneath a result, so that two numbers " +
          "in the same report were computed against different versions of the same file and " +
          "nothing in the record says so.",
      ],
      source: "WORKFLOW.md §5, principle 3",
    },
    {
      kind: "agent",
      title: "The bank was compiled by an LLM from the literature; no clinician has read it",
      body: [
        "Every feature and every class fingerprint carries a citation, and a schema that the " +
          "smoke tier enforces test by test holds the files to it. But expert review is " +
          "simulated — each bank file says so in its own provenance block, and the report states " +
          "it as a limit.",
        "The understanding debt here is repaid by the citations and by the schema, not by " +
          "authority: a reader can check a level's anchor text against the source it names.",
      ],
      source: "CONCEPT_BANK.md; data/concepts/*.yaml",
    },
  ] as Callout[],
};

export const design = {
  header: "Five arms, seven hypotheses, rules before numbers",
  lede:
    "The currency is labelled images. Two arms use none. Three use n labels with one identical " +
    "classifier on different features, so the features are the only thing that differs.",
  body: [
    "A vision-language model is an enormous pretrained model, so the fair pixel baseline is also " +
      "pretrained: frozen ImageNet ResNet-18 features under the same classifier, the same " +
      "regularisation search and the same nested subsets as the concept arm. Transfer learning " +
      "without the textbook.",
    "Every arm predicts on the same seeded test sample per dataset, so every comparison is " +
      "paired, and each carries a 95% interval from a paired bootstrap over the test images. " +
      "Across datasets we use a one-sided sign test rather than pooling incommensurable AUCs, " +
      "and every rule is held to one level.",
  ],
  limits: [
    "organa/organc/organsmnist are the same LiTS volumes in three planes, so twelve datasets are " +
      "at most ten independent units. The per-dataset differences are on the page so a reader can " +
      "recount with the organ triple as one vote.",
    "chestmnist is multi-label — fourteen findings that co-occur — so a nearest fingerprint and a " +
      "distribution over class names are not defined for it. It runs in the two labelled arms only.",
    "The rules were restated at the twelve-dataset level on 2026-09-13, when six of the twelve " +
      "verdicts were already known. The level reproduces the six-dataset rule exactly, so nothing " +
      "already decided moves, but the twelve-dataset thresholds are pre-registered only with " +
      "respect to the six new datasets.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "The unfair baseline — a claim that would have been true by construction",
      body: [
        "The first plan compared a ResNet-18 trained from scratch on fifty images against a model " +
          "with billions of parameters of pretraining. Every decision rule could have been " +
          "correct and the headline claim still worthless.",
        "It was caught by a person reading the plan before any rule existed — no computation had " +
          "run, so nothing in the record could have flagged it. The from-scratch network became " +
          "the fully supervised ceiling, and the label-matched baseline became a linear probe on " +
          "ImageNet features that shares the classifier, the regularisation search and the nested " +
          "subsets with the concept arm.",
      ],
      source: "CHANGELOG.md 2026-09-09",
    },
    {
      kind: "principle",
      title: "Pre-registration lives in git",
      body: [
        "A decision rule is only a decision rule if it precedes its numbers, and here that is " +
          "checkable rather than asserted: the commit that carried each hypothesis's rule into " +
          "WORKFLOW.md is an ancestor of the commit that carried its numbers. The export reads " +
          "both out of the history and the cards below show them.",
        "The failure it prevents: an arm designed after seeing the results, which can decide " +
          "nothing and has to be labelled post-hoc in every table it touches.",
      ],
      source: "WORKFLOW.md §2 and §10",
    },
  ] as Callout[],
};

export const machine = {
  header: "The machine",
  lede:
    "Seven stages, one file, every number with a rule. Every raw model response is archived with " +
    "the served model name and the prompt hash, and everything downstream is a deterministic " +
    "function of that archive.",
  body: [
    "The archive under results/score/ is write-protected from the moment it is written, so " +
      "re-querying the service is a deliberate act and not something a stale timestamp can cause. " +
      "Below is one real archived call, drawn at random from the exported sample: the image, the " +
      "rendered prompt, the raw reply, the parsed answer, and the manifest fields that make it " +
      "checkable.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "One chunk before 270 — a rule that printed one command and ran another",
      body: [
        "The scoring fan-out's four rules were generated in a loop. Snakemake printed the command " +
          "it did not run: each generated rule kept its own output path, but all four shared the " +
          "last iteration's shell string. The first real chunk — one job, a hundred calls, run " +
          "deliberately before the other 269 — came back with the primary model in its file name " +
          "and a different model's name in its argv and in served_model.",
        "Had the whole fan-out gone out, every model's archive would have been written by one " +
          "model, and the scale hypothesis would have compared four copies of it and found no " +
          "effect, with a perfectly consistent archive underneath. The only trace was " +
          "served_model disagreeing with the file name. Rules generated by a loop are not worth " +
          "what they cost here; the four are written out explicitly now, and the stage refuses a " +
          "mismatch before its first call.",
      ],
      source: "CHANGELOG.md 2026-09-11",
    },
    {
      kind: "principle",
      title: "The LLM boundary is explicit",
      body: [
        "Every response is archived raw with the served model name and the prompt hash; " +
          "everything downstream of the model is a deterministic function of the archive; the " +
          "archive is write-protected, so re-querying is a decision.",
        "The failure it prevents: a result that cannot be recomputed because the model behind it " +
          "has moved, and nothing on disk says which model answered.",
      ],
      source: "WORKFLOW.md §5, principle 7",
    },
  ] as Callout[],
};

export const h1 = {
  header: "H1 — Is the textbook worth labelled images?",
  lede:
    "The learning curve. Arm B draws a horizontal line with no labels at all; how many labels the " +
    "pixel probe needs to reach that line is n_B — this many labels is what the textbook was worth.",
  body: [
    "A negative result you can stand behind is what the recipe is for. The rule was fixed before " +
      "the numbers existed and it is not met: the pixel probe is already above the textbook arm at " +
      "the first grid point on most tasks, and the concept regression beats pixels at fifty labels " +
      "on only a couple of them.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "The wave that wrote nothing",
      body: [
        "Forty-eight scoring jobs ran their full two hours and produced no chunks at all. Every " +
          "job was killed at its time limit mid-chunk, and a chunk that times out writes nothing: " +
          "the hundred calls it made are spent and unrecorded. That is the single most expensive " +
          "shape of failure in this workflow.",
        "The cause was measured rather than guessed: a call that costs a second and a half alone " +
          "costs forty-three seconds under our own load, and over two minutes under eleven " +
          "thinking chunks. Latency scales almost exactly with our own concurrency, so aggregate " +
          "throughput is flat — concurrency buys no throughput on a saturated endpoint, and the " +
          "runtime request is what decides whether anything is saved.",
      ],
      source: "CHANGELOG.md 2026-09-12",
    },
  ] as Callout[],
};

export const h2 = {
  header: "H2 — The bank, or just the model?",
  lede:
    "Asking the model for the diagnosis outright beats the textbook readout on most tasks. But " +
    "permuting the fingerprints or the concept columns destroys both arms everywhere, so the " +
    "concept answers do carry real class information — the checklist readout is simply lossy.",
  body: [
    "The twist is worth the whole section. On the kidney-tissue task the model's own guess is at " +
      "chance and the checklist still ranks: where the model can name the class, asking for the " +
      "name wins; where it cannot, the checklist does.",
    "The two arms are separate calls on separate prompts — the concept prompt never names a " +
      "class, the zero-shot prompt never mentions a concept — so the comparison cannot be " +
      "circular. That separation was a correction: the original design returned both from one " +
      "call, which would have let the concept answers rationalise a class the model had already " +
      "committed to.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "The field we did not read",
      body: [
        "One ladder model returned nothing readable on all three thousand of its calls: every " +
          "chunk zero percent complete, finish_reason stop, and an empty string where the answer " +
          "should be. One diagnostic call settled it — the model files its answer under a third " +
          "message field, beside the two the reader knew, and with thinking off that field holds " +
          "finished JSON.",
        "The archive could not repair it, which is the real finding. The plan said every raw " +
          "response is archived; what was archived was the text this code extracted from the " +
          "response, which is not the same thing. Extraction is a guess about another system's " +
          "API, and when the guess was wrong the only way back was to buy the calls again. The " +
          "whole message object is archived now, so the next wrong guess costs a re-parse.",
      ],
      source: "CHANGELOG.md 2026-09-11",
    },
  ] as Callout[],
};

export const h3 = {
  header: "H3 and H7 — Does a bigger model read better?",
  lede:
    "Open weights, two families, 9B→27B and 12B→31B: no trend at all. A closed family ordered " +
    "only by price, luna→terra→sol: the top beats the bottom on nine of eleven. Whatever separates " +
    "them is not what parameter count captured.",
  body: [
    "Read within family, since size and training data are confounded across them. Both size steps " +
      "also change quantisation, and the qwen step changes generation, so larger moves together " +
      "with newer and quantised. Stated as a limit, not analysed away.",
    "Nothing public orders the closed models by size, so the price ladder is the vendor's own " +
      "ranking used as a proxy for capability — not a parameter count. Its rule was registered " +
      "before a single one of its calls was bought, and the calls were costed and approved first.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Name the model, never the alias",
      body: [
        "The service publishes aliases that point at whatever it considers best today. An archive " +
          "bought against an alias is unreproducible by design: the same name will answer " +
          "differently next month and nothing on disk will say so. Every model in this study is " +
          "named exactly, and the served model name comes back in every chunk manifest as the " +
          "check.",
        "The failure it prevents: a result whose model silently changed under it.",
      ],
      source: "docs/rcd_llm_service.md",
    },
    {
      kind: "agent",
      title: "Read the service's own metadata instead of probing it",
      body: [
        "Asked which models could see images and how hard each could be asked to think, the agent " +
          "read the service's own model metadata rather than buying probe calls to find out. It " +
          "corrected the study's belief about which models could take an image at all, and it is " +
          "why the frontier reader is compared at matched effort rather than against no reasoning: " +
          "the gateway rejects the lowest setting.",
      ],
      source: "SESSION_LOG.md 2026-09-12 15:20; docs/rcd_llm_service.md",
    },
  ] as Callout[],
};

export const h4 = {
  header: "H4 and H6 — What if the model thinks?",
  lede:
    "One day, told by the clock. A standing claim overturned at 15:20, a decision rule written at " +
    "16:05 before a call was bought, one chunk run first at 16:12, and a wave capped at 17:35 " +
    "after a timed call said it would not finish.",
  body: [
    "The result: thinking is conditional. It rescues the tasks the model read badly and costs the " +
      "ones it read well, and a frontier model reads no better than a 27B open model at matched " +
      "effort. A null here is a result, not a failure: if thinking does not move the concept " +
      "answers, the model's reading of the features is not attention-limited, which is a sharper " +
      "statement than a rise would be.",
    "The coda is the strongest thing in the study. The archive showed the frontier model " +
      "collapsing one dermoscopy concept to a single answer on most images — what a confidently " +
      "wrong prior looks like. A hypothesis was registered that lowering its effort would fix " +
      "exactly that. It did, on that one dataset and nothing else. A prediction named before the " +
      "calls and confirmed only where it was aimed.",
    "Two limits, both stated rather than analysed away. The frontier model is closed and of " +
      "unknown size, so the step is capability and not parameters. And it refuses temperature " +
      "zero — only its served default is allowed — so it is the one reader in this study whose " +
      "answers are sampled rather than deterministic. Some of any difference is sampling noise " +
      "the paired bootstrap cannot see.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "A decision rule before the calls",
      body: [
        "An arm worth adding is worth pre-registering, and anything that cannot be is a separate " +
          "study. The thinking step, the effort step and the price ladder each had their rule " +
          "committed before a single one of their own calls was bought.",
        "The failure it prevents: a comparison whose threshold is chosen once its numbers are " +
          "visible.",
      ],
      source: "WORKFLOW.md §10",
    },
    {
      kind: "agent",
      title: "An arm added after seeing the numbers, and removed the same day",
      body: [
        "A fifth arm was added on the owner's request after the first results: hand the model the " +
          "whole bank and then ask the zero-shot question. It cost three thousand calls and it " +
          "measured something real — the nearest-fingerprint readout is lossy, and the bank is not " +
          "information the model lacked.",
        "It was removed the same day because it was designed after seeing the numbers and so " +
          "could decide nothing, and an arm that decides nothing has to be labelled post-hoc in " +
          "every table, figure and paragraph it touches. What it measured is kept in the change " +
          "log. The later hypotheses were kept because their rules were committed before their " +
          "numbers.",
      ],
      source: "CHANGELOG.md 2026-09-12; WORKFLOW.md §10",
    },
    {
      kind: "nearmiss",
      title: "The runtime that was wrong in the way that costs everything",
      body: [
        "Eleven thinking chunks went out at once and a timed call came back at over two minutes. " +
          "The wave was cancelled and capped at four in flight — not as a throughput knob, since " +
          "aggregate throughput on this endpoint is flat, but so that each chunk finishes inside " +
          "its time limit and whole datasets land as they go.",
        "A chunk that overruns its limit writes nothing. The calls are spent and unrecorded, and " +
          "the archive does not say how far the job got, because the stage writes its JSON at the " +
          "end.",
      ],
      source: "CHANGELOG.md 2026-09-12",
    },
  ] as Callout[],
};

export const h5 = {
  header: "H5 — Does the textbook add anything?",
  lede:
    "The first supported hypothesis, and the one that changes what the others mean. The concept " +
    "answers concatenated to the pixel features under the same classifier: a small, consistent " +
    "gain at fifty labels, with every winning interval clear of zero.",
  body: [
    "H1 asks whether concept scores can stand in for pixel features at equal labels, and answers " +
      "no. That is not the same question as whether they carry anything pixels lack: two feature " +
      "blocks can be individually unequal and still complementary. Only the features differ from " +
      "the pixel arm, so the difference is what the textbook adds.",
    "The textbook cannot replace labels. It adds something the pixels do not carry.",
    "One limit, stated rather than tuned away: a dozen concept columns join 512 pixel columns " +
      "under a single L2 penalty, so a real but small contribution can be regularised away. A per-" +
      "block penalty would test a different, unregistered model. Every grid point other than the " +
      "registered one is reported and decides nothing.",
  ],
  callouts: [
    {
      kind: "nearmiss",
      title: "Two sessions on one checkout — read the manifest before forming a theory",
      body: [
        "A second agent session was given a related task and, not knowing the first existed, " +
          "switched the shared checkout onto its own branch mid-run. SLURM jobs read the working " +
          "tree when they start, so five of the twelve classify outputs were written by the wrong " +
          "code and their evaluate jobs failed with a missing key.",
        "The manifests' git_commit field named the culprit in each file before any theory did — " +
          "which is what that field is for. The five outputs were deleted so the next run " +
          "recomputed them. A corollary the shared storage makes sharp: a --touch in any checkout " +
          "is a --touch of the shared cache for all of them.",
      ],
      source: "SESSION_LOG.md 2026-09-13 12:25",
    },
  ] as Callout[],
};

export const verdicts = {
  header: "Seven verdicts",
  lede: "Computed, not chosen. Each row carries its rule, its count against the count the rule " +
    "asks for, and a dot per dataset.",
  body: [
    "Against the published fully supervised ceiling — the best of five methods Yang et al. report " +
      "for these same tasks at the same resolution — the pixel probe at the largest labelled " +
      "subset sits a small median gap below it, and the best zero-label arm sits far further " +
      "below. Labels close the gap; the textbook does not, and still adds a small increment on top " +
      "of them.",
    "The published numbers are a ceiling for the task, not a same-conditions arm: every value is " +
      "trained on a dataset's whole official training split, not this study's pool.",
  ],
  callouts: [
    {
      kind: "principle",
      title: "Every result carries a manifest, and the report is generated",
      body: [
        "Parameters, seeds, commit, package versions, host and wall time travel with every result " +
          "file. No number in the technical report is typed by hand, and no number on this page " +
          "is either: the site and the PDF are built from the same files, and the export checks " +
          "three of its numbers against the report's own generated tables before it will finish.",
        "The failure it prevents: a figure in a talk and a figure in a paper that came from " +
          "different runs, with nothing to say which.",
      ],
      source: "WORKFLOW.md §5, principle 5",
    },
  ] as Callout[],
};

export const close = {
  header: "What the four days cost, and what caught the mistakes",
  lede: "The ledger, and the tally of what actually caught each mistake.",
  body: [
    "Not one of them was caught by the dependency graph. A person reading the plan; one chunk run " +
      "before two hundred and seventy; a probe at the wire; a timed call; a manifest field. The " +
      "DAG shows that a stage exists and what it depends on. It does not show that the stage " +
      "computes the right thing.",
    "What the workflow gives you for free is the first half of the record: what was done, in what " +
      "order, from what, with which code and settings. The session log is the other half: why. " +
      "You need both, and only one of them is free.",
    REFRAIN,
  ],
  callouts: [
    {
      kind: "agent",
      title: "Understanding debt, and what repaid it here",
      body: [
        "Every stage the agent wrote faster than its owner could read it is a loan against future " +
          "comprehension. Four practices repaid it on this project: read every rule before it runs " +
          "at scale; run one cell first; make the agent explain the stage and then judge the " +
          "explanation, because a wrong explanation is visible in a way a wrong line of code is " +
          "not; and keep the change log as the owner's own record of understanding rather than a " +
          "log of agent activity.",
        "What the agent produces is the evidence base. The interpretation and the claim remain the " +
          "author's work, written from a record that is complete.",
      ],
      source: "TALK.md §3; SESSION_LOG.md",
    },
  ] as Callout[],
};

export const explore = {
  header: "Explore",
  lede:
    "Not presented. For the audience on their own devices, and for questions: every hypothesis's " +
    "row for one dataset, the sampled images, both rendered prompts verbatim, the concept bank, a " +
    "browser over the exported archive, and every figure the report generates at full size.",
};

export const notClaimed = [
  "The concept scores are not clinically validated.",
  "The simulated expert review does not substitute for a clinician.",
  "No arm here is state of the art.",
  "Every source dataset is public and labelled, so “the model carries textbook knowledge” " +
    "and “the model has seen this benchmark” are not distinguishable with these data.",
];
