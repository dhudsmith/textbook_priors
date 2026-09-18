import { useTalk } from "../state";
import { Band, Bullets, Header } from "../components/ui";
import { models } from "../content";

/* Which models were asked, in one table. It comes straight after the arms because the arms are
   built on what a model said, and it comes before the results because the results start naming
   families, sizes and thinking efforts and the room should already know what those are. Every
   column answers a question the talk asks later; nothing here is a specification for its own
   sake, and the row order is the order the two ladders climb. */

/** The efforts the service accepts, said the way the talk says them. */
function thinking(levels: string[]): string {
  const said = levels.map((l) => (l === "none" ? "off" : l)).join(", ");
  return levels.includes("none") ? said : `${said} — never off`;
}

export function Models() {
  const { study } = useTalk();
  const rows = study.study.model_table;
  const primary = rows.find((r) => r.primary);

  return (
    <Band id="models">
      <Header id="models" eyebrow="3">{models.header}</Header>
      <p className="lede">{models.lede}</p>
      <Bullets items={models.bullets} />

      <div className="table-scroll" style={{ margin: "1.2rem 0 0.6rem" }}>
        <table className="data" style={{ maxWidth: "52rem" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>model</th>
              <th style={{ textAlign: "left" }}>family</th>
              <th>size</th>
              <th style={{ textAlign: "left" }}>thinking</th>
              <th style={{ textAlign: "left" }}>weights</th>
              <th>calls in this study</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name}>
                <td className="mono">{r.name}</td>
                <td style={{ textAlign: "left" }}>{r.family}</td>
                <td>{r.params_b != null ? `${r.params_b}B` : "not published"}</td>
                <td style={{ textAlign: "left" }}>{thinking(r.reasoning)}</td>
                <td style={{ textAlign: "left" }}>{r.weights}</td>
                <td>{r.calls.toLocaleString("en-US")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {primary && (
        <p className="note">
          Every arm is built on <span className="mono">{primary.name}</span>, which answered both
          prompts on every image. The others were asked the checklist alone, each to settle one
          question. {models.sizeNote}
        </p>
      )}
    </Band>
  );
}
