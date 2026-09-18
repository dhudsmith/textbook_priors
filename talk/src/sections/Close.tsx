import { useTalk } from "../state";
import { Band, Body, Callouts, Header, Slide, Tile } from "../components/ui";
import { PageQR } from "./Title";
import { close as copy, LINKS, REFRAIN } from "../content";
import { asset } from "../data";
import { useAsync } from "../hooks";
import { loadTimeline } from "../data";

export function Close() {
  const { study } = useTalk();
  const led = study.ledger;
  const { data: timeline } = useAsync(loadTimeline);
  // The zero is counted, not asserted: no entry in the ledger names the graph as the catcher.
  const byGraph = led.catches.filter((c) => /dependency graph|dag/i.test(c.caught_by)).length;

  return (
    <Band id="close">
      <Slide
        title={<Header id="close" eyebrow="11">{copy.header}</Header>}
        figure={
      <div className="tiles">
        <Tile value={led.calls.toLocaleString("en-US")} unit="model responses bought and archived" />
        <Tile value={led.chunks} unit="chunk jobs, each one file with a manifest" />
        <Tile value={`${led.supported} of ${led.hypotheses}`}
              unit="hypotheses supported, every rule in git before its numbers" />
        <Tile value={timeline?.entries.length ?? led.session_log_entries}
              unit="prompts that materially directed the work" />
        <Tile value={led.catches.length} unit="mistakes caught" />
        <Tile value={byGraph} unit="caught by the dependency graph" />
      </div>
        }>
        <Body paras={copy.body} bullets={copy.bullets} />
      </Slide>

      <Slide cont title={<div className="conthead">{copy.header}</div>}>
      <h3>What caught each one</h3>
      <ul className="catches">
        {led.catches.map((c, i) => (
          <li key={i}>
            {c.what} — <em>{c.caught_by}</em>{" "}
            <span className="mono file">({c.source})</span>
          </li>
        ))}
      </ul>
      <p className="note">
        From <span className="file">public/data/study.json ← CHANGELOG.md and SESSION_LOG.md</span>.
      </p>

      <p className="pullquote">{REFRAIN}</p>
      </Slide>

      <Slide cont title={<div className="conthead">{copy.header}</div>}>
      <div style={{ marginTop: "2rem" }}>
        <div>
          <h3>Everything behind this page</h3>
          <ul style={{ fontSize: "0.9rem" }}>
            {LINKS.map((l) => (
              <li key={l.href}><a href={l.href}>{l.label}</a></li>
            ))}
            <li>
              <a href={asset("report.pdf")}>
                the technical report, as a PDF, from commit{" "}
                <span className="mono">{study.provenance.run_git_commit.slice(0, 10)}</span>
              </a>
            </li>
          </ul>
          <p className="note">
            Run on {study.run.host}, written {study.run.written.replace("T", " ")}. Exported{" "}
            {study.provenance.exported.replace("T", " ").replace("Z", " UTC")}.
          </p>
        </div>
        <div className="qrblock"><PageQR caption="Take the page with you" /></div>
      </div>

      <Callouts items={copy.callouts} />
      </Slide>
    </Band>
  );
}
