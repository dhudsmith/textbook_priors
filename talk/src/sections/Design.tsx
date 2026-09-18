import { useTalk } from "../state";
import { Band, Bullets, Callouts, Header } from "../components/ui";
import { ArmDiagram } from "../components/diagrams";
import { design } from "../content";

/* The five arms and what feeds each one. The seven hypotheses and their pre-registered rules are
   not presented - they wait in Extra - because the room has twenty-five minutes and the verdicts
   mean the same whether or not the rule was read out beforehand. */

export function Design() {
  const { study } = useTalk();
  const arms = study.style.arms;

  return (
    <Band id="design">
      <Header id="design" eyebrow="2">{design.header}</Header>
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
        A probe is one logistic regression on frozen features.
      </p>

      <h3>Two limits</h3>
      <ul style={{ fontSize: "0.9rem", color: "var(--ink-secondary)" }}>
        {design.limits.map((l, i) => <li key={i}>{l}</li>)}
      </ul>

      <Callouts items={design.callouts} />
    </Band>
  );
}
