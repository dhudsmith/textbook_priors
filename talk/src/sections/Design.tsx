import { useTalk } from "../state";
import { Band, Bullets, Header } from "../components/ui";
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
      <Header id="design" eyebrow="2">
        {design.headerShape.replace("{arms}", String(arms.length))}
      </Header>
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
                {/* the arm's own name says what is done with the features, so this column
                    says only what they are: B and C read the same scores, and differ in
                    whether a classifier is fitted on them. */}
                {a.id === "A" ? "— none; the model names the class itself"
                  : a.id === "B" || a.id === "C" ? "feature scores"
                  : a.id === "P" ? "ImageNet ResNet-18 features"
                  : "both, joined and put on one scale"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <p className="note">
        A probe is a classifier fitted on features that are already fixed: nothing above it is
        retrained. Arms C, P and C+P each fit their own, the same way, on the same labels.
      </p>

      <h3>Two limits</h3>
      <ul style={{ fontSize: "0.9rem", color: "var(--ink-secondary)" }}>
        {design.limits.map((l, i) => <li key={i}>{l}</li>)}
      </ul>

    </Band>
  );
}
