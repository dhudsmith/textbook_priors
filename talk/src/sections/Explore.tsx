import { useState } from "react";
import { useTalk } from "../state";
import { DatasetPicker, Deep, Header } from "../components/ui";
import { ArchiveCall } from "../components/ArchiveCall";
import { LAZY, asset, loadArchive, loadBank, loadPrompt } from "../data";
import { useAsync } from "../hooks";
import { REPO, notClaimed } from "../content";
import { LadderBlock } from "./ExtraResults";
import { fmt3, signed } from "../charts/primitives";

/* Not presented: everything for the audience on their own devices and for questions, including
   the comparisons that left the talk. This module is lazy-loaded, so the scroll does not pay for
   it until somebody reaches it. */

export default function Explore() {
  const { study, dataset, meta } = useTalk();
  const per = study.per_dataset[dataset];
  const { data: bank } = useAsync(() => loadBank(dataset), [dataset]);
  const { data: prompt } = useAsync(() => loadPrompt(dataset), [dataset]);
  const { data: archive } = useAsync(loadArchive);
  const [fig, setFig] = useState<string | null>(null);

  const rows = study.verdicts.map((v) => ({
    v, won: v.per_dataset[dataset], applies: dataset in v.per_dataset,
  }));

  return (
    <>
      <p className="lede">
        Pick a dataset and read every row this study wrote about it.
      </p>
      <DatasetPicker />

      <h3>{dataset}</h3>
      <p className="note">
        {meta.modality}. {meta.n_classes} classes ({meta.classes.join(", ")}).{" "}
        {meta.medmnist_task}. Source: {meta.source_dataset ?? "—"}. Official splits: train{" "}
        {meta.split_sizes.train.toLocaleString("en-US")}, val{" "}
        {meta.split_sizes.val.toLocaleString("en-US")}, test{" "}
        {meta.split_sizes.test.toLocaleString("en-US")}; this study scores {meta.test_n} test
        images and draws a labelled pool of {meta.pool_n.toLocaleString("en-US")}.
      </p>

      <h4>Every hypothesis, for this dataset</h4>
      <table className="data" style={{ maxWidth: "52rem" }}>
        <thead>
          <tr>
            <th>hypothesis</th><th style={{ textAlign: "left" }}>what it asked</th>
            <th style={{ textAlign: "left" }}>this dataset</th>
            <th style={{ textAlign: "left" }}>overall</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ v, won, applies }) => (
            <tr key={v.id}>
              <td><strong>{v.id.toUpperCase()}</strong> {v.title}</td>
              <td style={{ textAlign: "left", fontSize: "0.78rem" }}>{v.question}</td>
              <td style={{ textAlign: "left" }}>
                {applies ? (won ? "won" : "did not win") : "not defined here"}
              </td>
              <td style={{ textAlign: "left" }}>
                {v.wins} of {v.n_datasets} — {v.verdict}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Deep summary="Every AUC the evaluate stage wrote for this dataset">
      <div className="chart-scroll">
        <table className="data" style={{ maxWidth: "46rem" }}>
          <thead>
            <tr><th>key</th><th>AUC</th></tr>
          </thead>
          <tbody>
            {Object.entries(per.auc).filter(([k]) => !k.startsWith("Bperm")).map(([k, v]) => (
              <tr key={k}><td className="mono">{k}</td><td>{fmt3(v)}</td></tr>
            ))}
            {per.curve_n.flatMap((n) =>
              ["C", "P", "CP"].map((arm) => {
                const c = per.curve[`${arm}__n${n}`];
                return c ? (
                  <tr key={`${arm}${n}`}>
                    <td className="mono">{arm} at n = {n}</td>
                    <td>{fmt3(c.point)} <span style={{ color: "var(--ink-muted)" }}>
                      [{fmt3(c.lo)}, {fmt3(c.hi)}]</span></td>
                  </tr>
                ) : null;
              }))}
          </tbody>
        </table>
      </div>
      </Deep>

      <Deep summary="Paired differences and their intervals">
        <table className="data" style={{ maxWidth: "40rem" }}>
          <thead><tr><th>comparison</th><th style={{ textAlign: "left" }}>median, 95%</th></tr></thead>
          <tbody>
            {Object.entries(per.differences).map(([k, d]) => (
              <tr key={k}>
                <td className="mono">{k}</td>
                <td style={{ textAlign: "left" }}>
                  {signed(d.median)} [{fmt3(d.lo)}, {fmt3(d.hi)}]
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Deep>

      <Deep summary="How often the model answered every feature on the checklist">
        <table className="data" style={{ maxWidth: "32rem" }}>
          <thead><tr><th>model</th><th>complete</th></tr></thead>
          <tbody>
            {Object.entries(per.complete_frac).map(([m, f]) => (
              <tr key={m}><td className="mono">{m}</td><td>{(f * 100).toFixed(1)}%</td></tr>
            ))}
          </tbody>
        </table>
        <p className="note">
          A dataset-model cell more than 5% incomplete is flagged in the report and excluded from
          the headline; none of these is.
        </p>
      </Deep>

      <h4>The sampled test images</h4>
      <div className="gallery">
        {meta.samples.map((s) => (
          <figure key={s.file} style={{ margin: 0 }}>
            <div className="imgcard">
              <img src={asset(s.file)} alt={`${dataset}, class ${s.class}`} loading={LAZY}
                   width={224} height={224} />
            </div>
            <figcaption>{s.class}</figcaption>
          </figure>
        ))}
      </div>

      <Deep summary="Both rendered prompts, verbatim">
        <pre className="file" style={{ maxHeight: "40rem" }}>{prompt ?? "Loading the prompts…"}</pre>
      </Deep>

      <Deep summary="The concept bank for this dataset">
        {bank ? (
          <div>
            {bank.concepts.map((c) => (
              <div key={c.id} style={{ marginBottom: "0.8rem" }}>
                <div className="mono" style={{ fontWeight: 700 }}>{c.id}</div>
                <div style={{ fontSize: "0.85rem" }}>{c.question}</div>
                <ol style={{ fontSize: "0.8rem", color: "var(--ink-secondary)" }}>
                  {c.scale.map((level) => (
                    <li key={level}>
                      <span className="mono">{level}</span> — {c.anchors[level]?.text}{" "}
                      <span className="mono" style={{ color: "var(--ink-muted)" }}>
                        ({c.anchors[level]?.sources.join(", ")})
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        ) : "Loading the bank…"}
      </Deep>

      <h4>What the model said about this dataset's images</h4>
      {archive ? <ArchiveCall sample={archive} fixedDataset={dataset} />
               : <p className="note">Loading the archived answers…</p>}

      <LadderBlock />

      <h4>Every figure the report generates</h4>
      <div className="controls">
        {study.figures.map((f) => (
          <button key={f} className="chip" aria-pressed={fig === f}
                  onClick={() => setFig(fig === f ? null : f)}>
            {f.replace("fig_", "").replace(".png", "")}
          </button>
        ))}
      </div>
      {fig && (
        <figure className="chart">
          <img src={asset(`img/figs/${fig}`)} alt={fig} style={{ width: "100%" }} loading={LAZY} />
          <figcaption>
            <span className="file">report/figs/{fig}</span>
          </figcaption>
        </figure>
      )}

      <h4>The seven hypotheses, and the rules fixed before their numbers</h4>
      <p className="note">
        Every rule was written down before the calls that decided it were bought, and the dated
        record shows it. The rules were restated for twelve datasets once six verdicts were
        known; the twelve-dataset threshold reproduces the six-dataset one exactly, so nothing
        already decided moved.
      </p>
      <div className="table-scroll">
        <table className="data">
          <thead>
            <tr>
              <th>id</th>
              <th style={{ textAlign: "left" }}>question</th>
              <th style={{ textAlign: "left" }}>rule</th>
              <th>needs</th>
              <th>written down</th>
              <th>verdict</th>
            </tr>
          </thead>
          <tbody>
            {study.verdicts.map((v) => (
              <tr key={v.id}>
                <td className="mono">{v.id.toUpperCase()}</td>
                <td style={{ textAlign: "left", fontSize: "0.8rem" }}>{v.question}</td>
                <td style={{ textAlign: "left", fontSize: "0.8rem" }}>{v.rule}</td>
                <td>{v.threshold} of {v.n_datasets}</td>
                <td className="mono" style={{ fontSize: "0.72rem" }}>{v.registered.date}</td>
                <td>{v.verdict}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h4>What this study does not claim</h4>
      <ul style={{ maxWidth: "42rem", fontSize: "0.9rem", color: "var(--ink-secondary)" }}>
        {notClaimed.map((c, i) => <li key={i}>{c}</li>)}
      </ul>

      <h4>Files</h4>
      <p style={{ fontSize: "0.9rem" }}>
        Everything on this page is in <a href={REPO}>the code</a>, listed again at the close.
      </p>
      <Deep summary="Every file this page's numbers were read from">
        <ul className="mono" style={{ fontSize: "0.72rem", color: "var(--ink-muted)" }}>
          {study.provenance.source_files.map((f) => <li key={f}>{f}</li>)}
        </ul>
      </Deep>
    </>
  );
}

export function ExploreHeader() {
  return <Header id="explore" eyebrow="11">Extra</Header>;
}
