import { useState } from "react";
import { useTalk } from "../state";
import { Band, Bullets, Callouts, DatasetPicker, Deep, Header } from "../components/ui";
import { question } from "../content";
import { useAsync } from "../hooks";
import { LAZY, asset, loadBank } from "../data";

/* The dataset picker, sample images by class and the concept bank as a checklist: open a concept
   to see its ordered levels, the cited anchor text for each level, and the sources. This is the
   study's prior knowledge, written down before any call was bought. */

export function Question() {
  const { study, meta, dataset } = useTalk();
  const { data: bank, error } = useAsync(() => loadBank(dataset), [dataset]);
  const [open, setOpen] = useState<string | null>(null);

  // Two samples a class, and the class named once under the pair rather than under each image.
  const byClass = meta.samples.reduce<[string, typeof meta.samples][]>((acc, s) => {
    const row = acc.find(([name]) => name === s.class);
    if (row) row[1].push(s); else acc.push([s.class, [s]]);
    return acc;
  }, []);

  // The release's own shape, read off the snapshot rather than typed into the copy.
  const all = study.datasets;
  const fill = (shapes: readonly string[]) => shapes.map((t) => t
    .replace("{datasets}", String(all.length))
    .replace("{minClasses}", String(Math.min(...all.map((d) => d.n_classes))))
    .replace("{maxClasses}", String(Math.max(...all.map((d) => d.n_classes))))
    .replace("{minConcepts}", String(Math.min(...all.map((d) => d.n_concepts))))
    .replace("{maxConcepts}", String(Math.max(...all.map((d) => d.n_concepts)))));

  return (
    <Band id="question">
      <Header id="question" eyebrow="1">{question.header}</Header>
      <p className="lede">{question.lede}</p>
      <Bullets items={fill(question.bulletShapes)} />

      <DatasetPicker />

      <div style={{ display: "grid", gap: "1.6rem", gridTemplateColumns: "minmax(0, 1fr)" }}>
        <div>
          <h3>Sample images</h3>
          <p className="note">
            {meta.modality} · {meta.n_classes} classes, {meta.medmnist_task} · official test
            split{" "}
            {meta.split_sizes.test.toLocaleString("en-US")} images, of which this study scores{" "}
            {meta.test_n} · {meta.n_concepts} concepts in the bank
          </p>
          <div className="classgrid">
            {byClass.map(([name, shots]) => (
              <figure key={name} style={{ margin: 0 }}>
                <div className="classrow">
                  {shots.map((s) => (
                    <div className="imgcard" key={s.file}>
                      <img src={asset(s.file)} alt={`${dataset}, class ${name}`} loading={LAZY}
                           width={224} height={224} />
                    </div>
                  ))}
                </div>
                <figcaption>{name}</figcaption>
              </figure>
            ))}
          </div>
          <p className="note">Every arm was scored on this same sample, drawn once.</p>
        </div>

        <div>
          <h3>{question.bank.header}</h3>
          <p className="lede">{question.bank.lede}</p>
          <Bullets items={fill(question.bank.bulletShapes)} />
          {error && <p className="note">Could not load the bank: {error}</p>}
          {bank && (
            <>
              <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>concept</th>
                    <th style={{ textAlign: "left" }}>question put to the model</th>
                    <th>levels</th>
                  </tr>
                </thead>
                <tbody>
                  {bank.concepts.map((c) => (
                    <tr key={c.id} style={{ cursor: "pointer" }}
                        onClick={() => setOpen(open === c.id ? null : c.id)}>
                      <td className="mono">{c.id}</td>
                      <td style={{ textAlign: "left", fontSize: "0.8rem" }}>{c.question}</td>
                      <td>{c.scale.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              {open && (
                <div className="card" style={{ maxWidth: "44rem", marginTop: "0.8rem",
                                               cursor: "default" }}>
                  <div className="hid">{open}</div>
                  <ol style={{ fontSize: "0.85rem", paddingLeft: "1.2rem" }}>
                    {bank.concepts.find((c) => c.id === open)!.scale.map((level) => {
                      const anchor = bank.concepts.find((c) => c.id === open)!.anchors[level];
                      return (
                        <li key={level} style={{ marginBottom: "0.4rem" }}>
                          <span className="mono">{level}</span> — {anchor?.text}
                          {anchor && (
                            <span className="mono"
                                  style={{ color: "var(--ink-muted)", fontSize: "0.72rem" }}>
                              {" "}({anchor.sources.join(", ")})
                            </span>
                          )}
                        </li>
                      );
                    })}
                  </ol>
                </div>
              )}

              <Deep summary="Class fingerprints — the level the textbook expects for each feature">
                <div className="chart-scroll">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>class</th>
                        {bank.concepts.map((c) => (
                          <th key={c.id} className="mono" style={{ fontSize: "0.66rem" }}>
                            {c.id}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(bank.classes).map(([name, spec]) => (
                        <tr key={name}>
                          <td>{name}</td>
                          {bank.concepts.map((c) => (
                            <td key={c.id} className="mono" style={{ fontSize: "0.7rem",
                                  color: spec.fingerprint[c.id] === "any"
                                    ? "var(--ink-muted)" : "var(--ink)" }}>
                              {spec.fingerprint[c.id] ?? "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="note">
                  <span className="mono">any</span> means the sources rule nothing out on that
                  feature for that class.
                </p>
              </Deep>

            </>
          )}
        </div>
      </div>

      <Callouts items={question.callouts} />
    </Band>
  );
}
