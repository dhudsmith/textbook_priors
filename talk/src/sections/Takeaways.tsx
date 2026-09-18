import { useTalk } from "../state";
import { Band, Header } from "../components/ui";
import { takeaways as copy, LINKS } from "../content";
import { asset, loadEffort } from "../data";
import { useAsync } from "../hooks";

/* The end of the talk, and the section the speaker speaks from. A numbered list: a short line the
   room reads off the wall, and a sentence or two under it for whoever is reading on their own
   device. The context above it is deliberately quiet - it is what the four days cost, what he got
   wrong about his own study while making this talk, and the questions he has no answer to. */

export function Takeaways() {
  const { study } = useTalk();
  const { data: effort } = useAsync(loadEffort);
  const n = (v: number) => v.toLocaleString("en-US");

  const context = effort
    ? copy.contextShapes.map((shape) => shape
        .replace("{codeTotal}", n(study.code.total))
        .replace("{analysis}", n(study.code.analysis))
        .replace("{tests}", n(study.code.tests))
        .replace("{workflow}", n(study.code.workflow))
        .replace("{site}", n(study.code.site))
        .replace("{runs}", n(study.code.runs))
        .replace("{jobs}", n(effort.counts.jobs))
        .replace("{calls}", n(effort.counts.calls))
        .replace("{machineHours}", n(Math.round(effort.machine.wall_hours))))
    : [];

  return (
    <Band id="takeaways">
      <Header id="takeaways">{copy.header}</Header>

      <div className="context">
        {context.map((p, i) => <p key={i}>{p}</p>)}
      </div>

      <ol className="takelist">
        {copy.items.map((it) => (
          <li key={it.summary}>
            <span className="sum">{it.summary}</span>
            <span className="detail">{it.detail}</span>
          </li>
        ))}
      </ol>

      <div style={{ marginTop: "2rem" }}>
        <h3>Links</h3>
        <ul style={{ fontSize: "0.9rem" }}>
          {LINKS.map((l) => (
            <li key={l.href}><a href={l.href}>{l.label}</a></li>
          ))}
          <li><a href={asset("report.pdf")}>the technical report, as a PDF</a></li>
        </ul>
      </div>
    </Band>
  );
}
