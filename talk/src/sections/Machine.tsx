import { useCallback, useState } from "react";
import { useTalk } from "../state";
import { Band, Bullets, ChartFrame, Header } from "../components/ui";
import { RuleGraph, RuleTable, useWorkflow } from "../components/rules";
import { machine } from "../content";
import { asset } from "../data";

/* How the project runs: the rules, one per row, and the shape they make.

   The unit here is the rule, not the stage. A stage is a name for a group of rules and the room
   can read the grouping off the table; a rule is the thing that actually declares what it needs,
   what it produces and what it costs, and it is the thing the talk is about. Every number in the
   table - jobs, processors, hours, how many of a rule's jobs may talk to the model service at
   once - comes from the snapshot, and the rule source behind each row is cut out of the Snakefile
   by the export, so it cannot drift from the file it claims to quote. */

/** One line per rule, collapsed: enough to know what it is for. */
const BLURBS: Record<string, string> = {
  smoke: "Runs the tests. Nothing else starts until they pass.",
  fetch: "Downloads one dataset and checks it against its published fingerprint.",
  sample_dataset: "Draws one dataset's test images, and its pool of labelled images.",
  render_prompts: "Writes the two questions we put to the model about one dataset.",
  score_qwen3_5_9b: "A hundred images to qwen3.5-9b, one question, every reply filed.",
  score_gemma_4_12b: "The same, for gemma-4-12b.",
  score_qwen3_8_27b_fp8: "The same, for the model every arm is built on — most of the archive.",
  score_gemma_4_31b: "The same, for gemma-4-31b.",
  score_reader: "The same questions again, with the main model thinking.",
  score_reader_gateway: "The same, for the closed-weight models, thinking on.",
  collect_scores: "Gathers one dataset's chunks into the single table the arms read.",
  pixel_features: "Turns one dataset's images into image features, with a pretrained network.",
  classify_dataset: "Fits every arm for one dataset, at every number of labels and every seed.",
  evaluate_dataset: "Turns one dataset's arm scores into AUCs and intervals.",
  evaluate_across: "Compares the twelve datasets and applies the seven decision rules.",
  tables: "Writes every table, and every number the report quotes.",
  figures: "Draws every figure.",
  technical_report: "Builds the report out of the tables and figures.",
  all: "The one thing anybody asks for. Everything above follows from it.",
};

/** Expanded: what it is for, and the thing about it worth knowing. */
const DETAILS: Record<string, string> = {
  smoke: "The textbook lists against the shape they have to keep, the class names against the " +
    "pinned data release, both questions as properties of the strings actually sent, and the " +
    "way AUC is computed. Every rule below waits on it, so nothing runs on code that failed.",
  fetch: "The twelve releases are somebody else's published data, so they are a fixed input " +
    "rather than something this study makes: a file already here is never fetched again, and " +
    "one that is fetched is checked against its byte count and its fingerprint before anything " +
    "reads it.",
  sample_dataset: "One seeded draw per dataset: the 500 test images every arm is scored on, and " +
    "the 2,000 labelled images the arms take their labels from. Drawn once, so that every " +
    "comparison in the study is made on the same pictures.",
  render_prompts: "One question asks for a level on each visual feature and never names a " +
    "class; the other asks how likely each class is and never mentions a feature. Written once " +
    "and recorded, so the question in the call, in the archive and on this page is one string.",
  score_qwen3_5_9b: "One job is one chunk: a hundred images, one question, one model. A chunk " +
    "that fails costs a hundred answers rather than thirty thousand.",
  score_gemma_4_12b: "The scoring rules are written out in full rather than generated in a " +
    "loop, and the repetition is deliberate: the loop version once ran the last model's command " +
    "under every model's file name. The model a rule names is now visible in the rule you are " +
    "looking at.",
  score_qwen3_8_27b_fp8: "This model answered both questions on every image, on the test sample " +
    "and on the labelled pool, which is why it accounts for most of the jobs and most of the " +
    "archive. Every arm in the study is built on what it said.",
  score_gemma_4_31b: "Each model has a limit of its own on how many of its jobs may be in " +
    "flight, because the service is shared and answering is the slow part, not computing.",
  score_reader: "Thinking is asked for here and nowhere else. A thinking chunk takes an order " +
    "of magnitude longer than one with thinking off, so it is held back harder — a job that " +
    "overruns its time limit writes nothing at all.",
  score_reader_gateway: "The closed-weight models are somebody else's capacity, metered in " +
    "money rather than in how many may run at once, so they get a limit of their own: a mistake " +
    "costs twelve answers in flight, not twelve hundred.",
  collect_scores: "Nothing is measured here. The chunks are read, checked for how much came " +
    "back missing, and written out as one table per dataset, which is the file the arms are " +
    "fitted on.",
  pixel_features: "The network is pretrained and is not retrained here: the weights are a fixed " +
    "input like the images, so nothing in this rule is random and every run uses the same bytes.",
  classify_dataset: "Every arm, at every number of labels, at every seed, plus the two shuffled " +
    "controls and one probe per reader. It writes scores and measures nothing, because the " +
    "intervals have to redraw the test images once for all the arms together.",
  evaluate_dataset: "One resampling per dataset, shared by every arm: a replicate redraws the " +
    "500 test images once and every arm is recomputed on that same redraw, so an interval on a " +
    "difference carries only the noise that does not cancel.",
  evaluate_across: "The seven decision rules, as they were written before the numbers existed, " +
    "applied across the twelve datasets. This is the rule that says supported or not supported.",
  tables: "Every table, and the numbers the report's own sentences quote, so a sentence cannot " +
    "state something the run did not produce. It reads finished results and computes nothing.",
  figures: "Every figure in the report and on this page, drawn from the same files the tables " +
    "are written from.",
  technical_report: "Four passes of the typesetter, and then a check that it really finished: " +
    "one that dies part-way still leaves a readable file behind, which is how a truncated " +
    "report gets mistaken for a whole one.",
  all: "It computes nothing itself. Asking for the report is the whole instruction, and " +
    "everything above is worked out from it.",
};

export function Machine() {
  const { study } = useTalk();
  const workflow = useWorkflow();

  const [open, setOpen] = useState<string | null>(null);
  /* The drawing and the table are one control: picking a rule in the drawing opens its row, and
     brings the row to the reader rather than leaving them to hunt for it. */
  const fromGraph = useCallback((name: string | null) => {
    setOpen(name);
    if (name) {
      requestAnimationFrame(
        () => document.getElementById(`rule-${name}`)
                     ?.scrollIntoView({ block: "center", behavior: "smooth" }));
    }
  }, []);

  return (
    <Band id="machine">
      <Header id="machine">{machine.header}</Header>
      {/* Snakemake's own wordmark, which is where the tool is named: the sentence says what it
          is for, the mark says which one. MIT-licensed, taken from the project's repository and
          served from this site rather than hot-linked. */}
      <p className="lede withlogo">
        <span>{machine.lede}</span>
        <img src={asset("img/snakemake-logo.svg")} alt="Snakemake" width={158} height={21}
             className="toollogo" />
      </p>
      <Bullets items={machine.bullets} />

      <RuleTable blurbs={BLURBS} details={DETAILS} open={open} setOpen={setOpen} />
      <p className="note">
        {workflow.rules.length} rules, {workflow.jobs.toLocaleString("en-US")} jobs in a full
        pass — of which {study.archive.chunks.toLocaleString("en-US")} are the hundred-image jobs
        that bought the {study.archive.calls.toLocaleString("en-US")} archived answers. The table
        is read out of the workflow itself by the export ({workflow.how}, on Snakemake{" "}
        {workflow.snakemake}), and the rule text is the file's own.
      </p>

      <h3>What waits for what</h3>
      <ChartFrame caption={
        "One box per rule, and an arrow to everything that waits on it. Choose a box to open " +
        "its row above. Drawn from the workflow's own dependency graph, which the export asks " +
        "Snakemake for with a dry run that plans everything and does nothing."}>
        <RuleGraph open={open} setOpen={fromGraph} />
      </ChartFrame>
      <p className="note">
        Nobody drew that shape. It is worked out from what each rule says it needs, which is the
        whole argument for writing it down that way.
      </p>

    </Band>
  );
}
