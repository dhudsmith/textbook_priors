import { useTalk } from "../state";
import { Band, Bullets, Header } from "../components/ui";
import { StageStrip } from "../components/diagrams";
import { ArchiveCall } from "../components/ArchiveCall";
import { machine } from "../content";
import { useAsync, useInView } from "../hooks";
import { loadArchive } from "../data";

const BLURBS: Record<string, string> = {
  smoke: "The tests: the bank and its wording, the class names against the fixed release, both " +
    "prompts, the sampler, the classifiers and how AUC is computed. Every rule waits on them, so " +
    "nothing runs on code that fails its tests.",
  sample: "Per dataset: the test images this study scores, drawn once, and the pool of " +
    "labelled images the arms draw from.",
  score: "Per dataset, a rule writes the two prompts from the bank and the class names. Then, " +
    "per model and per chunk of a hundred images, the calls go out and every reply is kept " +
    "where it cannot be overwritten.",
  features: "Per dataset: the ImageNet ResNet-18 features of the sampled images. The network " +
    "is pretrained and is not retrained here.",
  classify: "Per dataset: every arm at every number of labels and every seed, the two " +
    "shuffled controls, and one probe per reader on the same images.",
  evaluate: "Per dataset: an AUC for every arm, a 95% interval for every difference, and how " +
    "many labelled images arm P needed to match arm B. Then, across datasets: the sign tests " +
    "and the comparisons between models and between readers.",
  report: "Every figure and table, two generated appendices, and the technical report PDF.",
};

export function Machine() {
  const { study } = useTalk();
  const { ref, seen } = useInView<HTMLDivElement>();
  const { data: archive, error } = useAsync(
    () => (seen ? loadArchive() : new Promise<never>(() => {})), [seen]);

  return (
    <Band id="machine">
      <Header id="machine" eyebrow="5">{machine.header}</Header>
      <p className="lede">{machine.lede}</p>
      <Bullets items={machine.bullets} />

      <StageStrip blurbs={BLURBS} />
      <p className="note">
        The archive holds {study.archive.chunks.toLocaleString("en-US")} chunks and{" "}
        {study.archive.calls.toLocaleString("en-US")} calls.
      </p>

      <h3>One archived image, and both answers</h3>
      <div ref={ref}>
        {error && <p className="note">Could not load the archive sample: {error}</p>}
        {archive ? <ArchiveCall sample={archive} />
                 : <p className="note">Loading the archived answers…</p>}
      </div>

    </Band>
  );
}
