import { useTalk } from "../state";
import { Band, Callouts, Deep, Header } from "../components/ui";
import { StageStrip } from "../components/diagrams";
import { ArchiveCall } from "../components/ArchiveCall";
import { machine } from "../content";
import { useAsync, useInView } from "../hooks";
import { loadArchive } from "../data";

const BLURBS: Record<string, string> = {
  smoke: "The tests: the bank schema and its anchors, the label maps against the pinned release, " +
    "both prompts, the sampler, the estimators and the metric conventions. Every rule takes the " +
    "smoke marker as an input, so nothing is computed on code that fails its tests.",
  sample: "Per dataset: the seeded test sample and the labelled pool, capped at the official " +
    "split, streamed out of the compressed release without loading it.",
  score: "Per dataset, the two prompts are rendered by their own rule from the bank and the label " +
    "map. Then, per model, split, prompt and chunk of a hundred images, the calls go out and " +
    "every raw response is archived and write-protected.",
  features: "Per dataset: the frozen ImageNet ResNet-18 penultimate features of the sampled " +
    "images, with preprocessing that does not resize.",
  classify: "Per dataset: every arm at every n and seed, the two permutation controls, and each " +
    "reader's cross-validated probe on the shared prefix.",
  evaluate: "AUC per arm, the paired bootstrap, n_B, and a second bootstrap over the prefix for " +
    "the readers; then the sign tests, the ladder and the reader chain across datasets.",
  report: "Every figure and table, the number macros, two generated appendices and the technical " +
    "report PDF. No number in it is typed by hand.",
};

export function Machine() {
  const { study } = useTalk();
  const { ref, seen } = useInView<HTMLDivElement>();
  const { data: archive, error } = useAsync(
    () => (seen ? loadArchive() : new Promise<never>(() => {})), [seen]);

  return (
    <Band id="machine">
      <Header id="machine" eyebrow="4">{machine.header}</Header>
      <p className="lede">{machine.lede}</p>
      {machine.body.map((p, i) => <p key={i}>{p}</p>)}

      <StageStrip blurbs={BLURBS} />
      <p className="note">
        Job counts are this run's own: the archive holds {study.archive.chunks.toLocaleString("en-US")}{" "}
        chunks and {study.archive.calls.toLocaleString("en-US")} calls, written between{" "}
        {study.archive.first_written.replace("T", " ")} and{" "}
        {study.archive.last_written.replace("T", " ")}.
      </p>

      <h3>One real archived call</h3>
      <div ref={ref}>
        {error && <p className="note">Could not load the archive sample: {error}</p>}
        {archive ? <ArchiveCall sample={archive} />
                 : <p className="note">Loading one archived call…</p>}
      </div>

      <Deep summary="What the archive holds, by model">
        <table className="data" style={{ maxWidth: "44rem" }}>
          <thead>
            <tr><th>model or reader</th><th>chunks</th><th>calls</th>
                <th style={{ textAlign: "left" }}>served model name</th></tr>
          </thead>
          <tbody>
            {Object.entries(study.archive.by_model).map(([m, v]) => (
              <tr key={m}>
                <td className="mono">{m}</td>
                <td>{v.chunks}</td>
                <td>{v.calls.toLocaleString("en-US")}</td>
                <td style={{ textAlign: "left" }} className="mono">{v.served.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note">
          The served model name is what the service said answered. This field caught a
          rule running the wrong model's command.
        </p>
      </Deep>

      <Callouts items={machine.callouts} />
    </Band>
  );
}
