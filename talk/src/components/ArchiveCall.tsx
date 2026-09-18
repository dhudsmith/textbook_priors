import { useMemo, useState } from "react";
import type { ArchiveRecord, ArchiveSample } from "../types";
import { useTalk } from "../state";
import { LAZY, asset } from "../data";

/* One archived image, and what both prompts returned for it.

   The study asks the same picture two different questions, in two separate calls, and gets two
   different shapes of answer back: the checklist comes back as a level for each visual feature,
   the other prompt as a number for each class. Showing them together is the point of the panel,
   so they are drawn side by side rather than one at a time. The archived records pair on the
   dataset and the position in the test sample, which is the same image in both.

   Nothing here is live and nothing is re-read: results/score/ is write-protected and this is a
   copy of a few of its records, taken by the export. The reply text is deliberately not shown -
   a reader should see the answer, not the shape it arrived in. */

/** The bank writes a feature and its levels in one word; a reader should not have to. */
const plain = (s: string) => s.replace(/_/g, " ");

interface Pair {
  key: string; dataset: string; position: number;
  concept?: ArchiveRecord; zero?: ArchiveRecord;
}

export function ArchiveCall({ sample, fixedDataset }: {
  sample: ArchiveSample; fixedDataset?: string;
}) {
  const { metaOf, armHue } = useTalk();

  const pairs = useMemo<Pair[]>(() => {
    const by = new Map<string, Pair>();
    for (const r of sample.records) {
      if (fixedDataset && r.dataset !== fixedDataset) continue;
      const key = `${r.dataset}__${r.position}`;
      const pair = by.get(key) ?? { key, dataset: r.dataset, position: r.position };
      if (r.prompt === "concept") pair.concept = r; else pair.zero = r;
      by.set(key, pair);
    }
    const all = [...by.values()].sort((a, b) => a.key.localeCompare(b.key));
    // On the spine both answers have to be there, because the contrast is the whole point. Asked
    // for one dataset in Extra, show what that dataset has: chestmnist is scored on the checklist
    // alone, and saying so is better than dropping the dataset.
    const both = all.filter((p) => p.concept && p.zero);
    return fixedDataset ? (both.length ? both : all) : both;
  }, [sample.records, fixedDataset]);

  const [i, setI] = useState(() => Math.floor(Math.random() * Math.max(1, pairs.length)));
  const here = pairs.length ? i % pairs.length : 0;
  const pair = pairs[here];
  // "Another" means another: the draw skips the image already on screen.
  const drawAnother = () => {
    if (pairs.length < 2) return;
    let k = Math.floor(Math.random() * (pairs.length - 1));
    if (k >= here) k += 1;
    setI(k);
  };

  if (!pair) return <p className="note">No archived answers for this dataset.</p>;

  const rec = pair.concept ?? pair.zero!;
  const meta = metaOf(pair.dataset);
  const manifest = sample.manifests[rec.manifest_key];
  const label = rec.label;
  const trueClass = typeof label === "number" ? meta.classes[label] : null;

  const levels = Object.entries(pair.concept?.answers ?? {});
  const scores = Object.entries(pair.zero?.scores ?? {})
    .filter(([, v]) => v != null)
    .sort((a, b) => (b[1] as number) - (a[1] as number));
  const guess = armHue("A");

  return (
    <div>
      <div className="controls">
        <button className="plain" onClick={drawAnother}>Show another image</button>
        <span className="note" style={{ margin: 0 }}>
          {pairs.length} to choose from{fixedDataset ? `, all ${fixedDataset}` : ""}
        </span>
      </div>

      <div className="answergrid">
        <div>
          <div className="imgcard">
            <img src={asset(rec.image)} alt={`a ${pair.dataset} test image`}
                 width={224} height={224} loading={LAZY} />
          </div>
          <p className="note" style={{ marginTop: "0.4rem", marginBottom: "0.3rem" }}>
            {pair.dataset}, at the size the model was shown.
          </p>
          {trueClass && (
            <p className="note" style={{ marginBottom: "0.3rem" }}>
              It really is <strong>{plain(trueClass)}</strong>.
            </p>
          )}
          {manifest && (
            <p className="note" style={{ marginBottom: 0 }}>
              Answered by <span className="mono">{manifest.served_model}</span>,{" "}
              {manifest.reasoning && manifest.reasoning !== "none"
                ? `thinking at ${manifest.reasoning} effort.`
                : "with no thinking step."}
            </p>
          )}
        </div>

        <div className="answerpair">
          <div>
            <h4>Visual features, and the level picked</h4>
            <p className="note">
              One call: every visual feature the textbook lists for this kind of image, and the
              level the model picked for it.
            </p>
            {levels.length ? (
              <table className="data">
                <thead>
                  <tr><th>visual feature</th><th style={{ textAlign: "left" }}>the model's level</th></tr>
                </thead>
                <tbody>
                  {levels.map(([k, v]) => (
                    <tr key={k}>
                      <td>{plain(k)}</td>
                      <td style={{ textAlign: "left" }}>{plain(String(v))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="note">This image has no checklist answers on file.</p>}
          </div>

          <div>
            <h4>How likely each class</h4>
            <p className="note">
              A second call, on a prompt of its own: how likely is each class? The checklist above
              never sees this answer, and this answer never sees the checklist.
            </p>
            {scores.length ? (
              <table className="data">
                <thead>
                  <tr><th>class</th><th style={{ textAlign: "left" }}>how likely the model said</th></tr>
                </thead>
                <tbody>
                  {scores.map(([name, v]) => (
                    <tr key={name}>
                      <td>
                        {plain(name)}
                        {name === trueClass && (
                          <span className="note" style={{ display: "inline", marginLeft: "0.35rem" }}>
                            — the true class
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: "left" }}>
                        <span className="meter">
                          <span style={{ width: `${Math.max(0, Math.min(1, v as number)) * 100}%`,
                                         background: guess }} />
                        </span>
                        <span className="mono" style={{ fontSize: "0.72rem" }}>
                          {(v as number).toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="note">
                {meta.multi_label
                  ? `${pair.dataset} marks several findings at once rather than one class, so ` +
                    "this question is not asked of it. Only the checklist is."
                  : "This image has no class answer on file."}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
