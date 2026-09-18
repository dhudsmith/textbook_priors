import { useTalk } from "../state";
import { Band, Body, Callouts, ChartFrame, Header } from "../components/ui";
import { CeilingDots, VerdictBoard } from "../charts/Verdicts";
import { verdicts as copy, notClaimed } from "../content";
import { fmt3 } from "../charts/primitives";

export function Verdicts() {
  const { study } = useTalk();
  const gap = study.ceiling.median_gap;
  const supported = study.verdicts.filter((v) => v.supported);
  const not = study.verdicts.filter((v) => !v.supported);

  return (
    <Band id="verdicts">
      <Header id="verdicts" eyebrow="10">{copy.header}</Header>
      <p className="lede">
        Computed, not chosen: {not.length} not supported, {supported.length} supported.{" "}
        {supported.map((v) => v.id.toUpperCase()).join(" and ")} met their rules; the rest did
        not.
      </p>
      <Body paras={copy.body} bullets={copy.bullets} />

      <VerdictBoard />

      <p className="takeaway">
        The pixel arm is within two AUC points of the ceiling on{" "}
        {study.ceiling.pixel_within_two_points} of {study.ceiling.rows.length} tasks and at or
        above it on {study.ceiling.pixel_at_or_above}; the best zero-label arm is within five
        points on {study.ceiling.zero_within_five_points}.
      </p>
      <ChartFrame
        caption={`Each arm against the published ceiling. The pixel arm at n = ` +
                 `${study.ceiling.largest_n} sits a median ${fmt3(gap.pixel)} AUC below it; the ` +
                 `best zero-label arm ${fmt3(gap.zero)} below.`}
        source="public/data/study.json ← results/evaluate/*.json and data/literature/benchmarks.yaml"
        summary={
          <table className="data">
            <thead>
              <tr><th>dataset</th><th>best zero-label</th><th>arm C, largest n</th>
                  <th>arm P, largest n</th><th>published ceiling</th></tr>
            </thead>
            <tbody>
              {study.ceiling.rows.map((r) => (
                <tr key={r.dataset}>
                  <td>{r.dataset}</td>
                  <td>{r.zero != null ? fmt3(r.zero) : "—"}</td>
                  <td>{fmt3(r.concept)}</td>
                  <td>{fmt3(r.pixel)}</td>
                  <td>{fmt3(r.ceiling)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        }>
        <CeilingDots />
      </ChartFrame>
      <p className="note">
        Ceiling source: {study.study.literature.title} ({study.study.literature.table}).
      </p>

      <h3>What this study does not claim</h3>
      <ul style={{ fontSize: "0.9rem", color: "var(--ink-secondary)" }}>
        {notClaimed.map((c, i) => <li key={i}>{c}</li>)}
      </ul>

      <Callouts items={copy.callouts} />
    </Band>
  );
}
