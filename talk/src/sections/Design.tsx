import { useState } from "react";
import { useTalk } from "../state";
import { Band, Bullets, Callouts, Header } from "../components/ui";
import { ArmDiagram } from "../components/diagrams";
import { design } from "../content";

/* Seven hypothesis cards. A card flips to its decision rule, the threshold the rule asks for, and
   the date and commit that carried the rule into WORKFLOW.md - which the export read out of git
   and checked against the commit that carried the numbers. */

export function Design() {
  const { study } = useTalk();
  const [flipped, setFlipped] = useState<Set<string>>(new Set());
  const flip = (id: string) => setFlipped((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const arms = study.style.arms;

  return (
    <Band id="design">
      <Header id="design" eyebrow="3">{design.header}</Header>
      <p className="lede">{design.lede}</p>
      <Bullets items={design.bullets} />

      <ArmDiagram />

      <div className="table-scroll" style={{ margin: "1.2rem 0" }}>
      <table className="data" style={{ maxWidth: "52rem" }}>
        <thead>
          <tr>
            <th>arm</th>
            <th>labels</th>
            <th style={{ textAlign: "left" }}>features</th>
          </tr>
        </thead>
        <tbody>
          {arms.map((a) => (
            <tr key={a.id}>
              <td>
                <span className="swatch" style={{ background: a.colour, display: "inline-block",
                      width: 9, height: 9, borderRadius: 2, marginRight: 6 }} />
                {a.label}
              </td>
              <td>{a.id === "A" || a.id === "B" ? "0" : "n"}</td>
              <td style={{ textAlign: "left", fontSize: "0.8rem", color: "var(--ink-secondary)" }}>
                {a.id === "A" ? "— (the class distribution, from its own prompt)"
                  : a.id === "B" ? "concept scores, matched to the bank's class fingerprints"
                  : a.id === "C" ? "concept scores"
                  : a.id === "P" ? "ImageNet ResNet-18 penultimate features"
                  : "both blocks concatenated, standardised together"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <p className="note">
        A probe is one logistic regression on frozen features. Arms C, P and C+P are the same
        probe on different feature blocks.
      </p>

      <h3>Seven questions, each with a rule fixed before its numbers</h3>
      <p className="note">Click a card to turn it over.</p>
      <div className="cards">
        {study.verdicts.map((v) => {
          const back = flipped.has(v.id);
          return (
            <button key={v.id} className="card" onClick={() => flip(v.id)}
                    aria-expanded={back}>
              <div className="hid">{v.id.toUpperCase()} · {v.title}</div>
              {back ? (
                <>
                  <div className="claim">The rule</div>
                  <div className="rule">{v.rule}</div>
                  <div className="flip">
                    registered {v.registered.date} in{" "}
                    <span className="mono">{v.registered.short}</span>
                    {v.rule_precedes_numbers
                      ? " — an ancestor of the commit that carried its numbers"
                      : ""}
                  </div>
                </>
              ) : (
                <>
                  <div className="claim">{v.question}</div>
                  <div className="rule">
                    Decided on {v.metric}. Supported at {v.threshold} of {v.n_datasets} datasets.
                  </div>
                  <div className="flip">turn over for the rule ›</div>
                </>
              )}
            </button>
          );
        })}
      </div>

      <h3>Three limits</h3>
      <ul style={{ fontSize: "0.9rem", color: "var(--ink-secondary)" }}>
        {design.limits.map((l, i) => <li key={i}>{l}</li>)}
      </ul>

      <Callouts items={design.callouts} />
    </Band>
  );
}
