import { useTalk } from "../state";
import { Band, Callouts, ChartFrame, Header, Tile } from "../components/ui";
import { CaughtBy } from "../charts/Verdicts";
import { PageQR } from "./Title";
import { close as copy, LINKS, REFRAIN } from "../content";
import { asset } from "../data";
import { useAsync } from "../hooks";
import { loadTimeline } from "../data";

export function Close() {
  const { study } = useTalk();
  const led = study.ledger;
  const { data: timeline } = useAsync(loadTimeline);

  return (
    <Band id="close">
      <Header id="close" eyebrow="11">{copy.header}</Header>
      <p className="lede">{copy.lede}</p>

      <div className="tiles">
        <Tile value={led.calls.toLocaleString("en-US")} unit="model responses bought and archived" />
        <Tile value={led.chunks} unit="chunk jobs, each one file with a manifest" />
        <Tile value={led.tests ?? "—"} unit="tests, run before anything else" />
        <Tile value={led.hypotheses} unit="hypotheses registered, each with its rule in git" />
        <Tile value={led.supported} unit="supported" />
        <Tile value={timeline?.entries.length ?? led.session_log_entries}
              unit="prompts that materially directed the work" />
      </div>

      {copy.body.map((p, i) => <p key={i}>{p}</p>)}

      <ChartFrame
        caption="What actually caught each mistake. The dependency graph's bar is the point."
        source="public/data/study.json ← CHANGELOG.md and SESSION_LOG.md"
        summary={
          <ul>
            {led.catches.map((c, i) => (
              <li key={i}>{c.what} — caught by {c.caught_by} ({c.source})</li>
            ))}
          </ul>
        }>
        <CaughtBy />
      </ChartFrame>

      <p style={{ fontSize: "1.2rem", fontWeight: 700, maxWidth: "36rem" }}>{REFRAIN}</p>

      <div className="title-grid" style={{ marginTop: "2rem" }}>
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
            {study.provenance.exported}.
          </p>
        </div>
        <PageQR caption="This page" />
      </div>

      <Callouts items={copy.callouts} />
    </Band>
  );
}
