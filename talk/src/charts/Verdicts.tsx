import { useState } from "react";
import { useTalk } from "../state";
import { Dots } from "../components/ui";
import { verdicts as copy } from "../content";

/* The verdict board: seven rows, each saying in plain words what it asked, its count against the
   count the rule asks for, a dot per dataset, and the verdict. Nothing here decides anything -
   every field is copied from results/evaluation.json.

   Three of the seven were argued on the results figure and two in the thinking section; model
   size and the price ladder left the talk entirely, so their rows link to Extra, where the
   comparison is drawn in full. */

const SECTION_OF: Record<string, string> = {
  h1: "results", h2: "results", h5: "results",
  h4: "thinking", h6: "thinking",
  h3: "explore", h7: "explore",
};

export function VerdictBoard() {
  const { study } = useTalk();
  const [open, setOpen] = useState<string | null>(null);
  const order = study.study.datasets;

  return (
    <div>
      <div className="table-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>hypothesis</th>
            <th style={{ textAlign: "left" }}>what it asked</th>
            <th>count</th>
            <th className="nowrap">needed</th>
            <th>p</th>
            <th style={{ textAlign: "left" }}>per dataset</th>
            <th style={{ textAlign: "left" }}>verdict</th>
          </tr>
        </thead>
        <tbody>
          {study.verdicts.map((v) => (
            <tr key={v.id}>
              <td>
                <a href={`#${SECTION_OF[v.id] ?? v.section}`}
                   onClick={() => setOpen(open === v.id ? null : v.id)}>
                  <strong>{v.id.toUpperCase()}</strong> {v.title}
                </a>
              </td>
              <td style={{ textAlign: "left", fontSize: "0.82rem", color: "var(--ink-secondary)" }}>
                {copy.asks[v.id] ?? v.question}
              </td>
              <td>{v.wins}</td>
              <td className="nowrap">{v.threshold} of {v.n_datasets}</td>
              <td>{v.p.toFixed(4)}</td>
              <td style={{ textAlign: "left" }}>
                <Dots per={v.per_dataset} order={order} label={`${v.id} per dataset`} />
              </td>
              <td className="nowrap"
                  style={{ textAlign: "left",
                           color: v.supported ? "var(--good)" : "var(--ink-muted)",
                           fontWeight: 700 }}>
                {v.supported ? "✓ supported" : "✕ not supported"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <p className="note">
        A filled dot is a dataset the comparison won on; a cross is one it did not.
      </p>
    </div>
  );
}
