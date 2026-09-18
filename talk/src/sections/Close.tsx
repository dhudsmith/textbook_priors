import { useTalk } from "../state";
import { Band, Bullets, Callouts, Header, Tile } from "../components/ui";
import { PageQR } from "./Title";
import { close as copy, LINKS, REFRAIN } from "../content";
import { asset } from "../data";

export function Close() {
  const { study } = useTalk();
  const led = study.ledger;
  // The zero is counted, not asserted: no entry in the ledger names the graph as the catcher.
  const byGraph = led.catches.filter((c) => /dependency graph|dag/i.test(c.caught_by)).length;

  return (
    <Band id="close">
      <Header id="close" eyebrow="9">{copy.header}</Header>

      {/* The counts of prompts, calls and jobs are in the section above; what is only here is
          what went wrong and what found it. */}
      <div className="tiles">
        <Tile value={led.tests} unit="automated tests, run before every result" />
        <Tile value={led.catches.length} unit="mistakes caught" />
        <Tile value={byGraph} unit="caught by the dependency graph" />
      </div>

      <Bullets items={copy.bullets} />

      <h3>What caught each one</h3>
      <ul className="catches">
        {led.catches.map((c, i) => (
          <li key={i}>
            {c.what} — <em>{c.caught_by}</em>
          </li>
        ))}
      </ul>

      <p className="pullquote">{REFRAIN}</p>

      <div style={{ marginTop: "2rem" }}>
        <div>
          <h3>Everything behind this page</h3>
          <ul style={{ fontSize: "0.9rem" }}>
            {LINKS.map((l) => (
              <li key={l.href}><a href={l.href}>{l.label}</a></li>
            ))}
            <li><a href={asset("report.pdf")}>the technical report, as a PDF</a></li>
          </ul>
        </div>
        <div className="qrblock"><PageQR caption="Take the page with you" /></div>
      </div>

      <Callouts items={copy.callouts} />
    </Band>
  );
}
