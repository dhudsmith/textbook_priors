import { useTalk } from "../state";
import { Band, Callouts, ChartFrame, Dots, Header } from "../components/ui";
import { Ladder } from "../charts/Ladder";
import { ThinkingScatter } from "../charts/ThinkingScatter";
import { Forest } from "../charts/Forest";
import { TimelineStrip } from "../charts/TimelineStrip";
import { h4 as copy } from "../content";
import { useAsync } from "../hooks";
import { loadTimeline } from "../data";
import { fmt3, signed } from "../charts/primitives";

export function H4() {
  const { study, armHue } = useTalk();
  const h4 = study.across.h4;
  const h6 = study.across.h6;
  const v4 = study.verdicts.find((x) => x.id === "h4")!;
  const v6 = study.verdicts.find((x) => x.id === "h6")!;
  const { data: timeline } = useAsync(loadTimeline);

  // The reader chain, in the order the study built it: the four thinking-off models, then the
  // thinking primary, then the gateway readers. Both lists come from the config in the snapshot.
  const chain = [...Object.keys(study.study.models), ...Object.keys(study.study.readers)]
    .filter((r) => h4.readers.includes(r));

  const h6rows = Object.entries(h6.differences).map(([dataset, d]) => ({
    dataset, ...(d as { median: number; lo: number; hi: number }),
  }));
  const h6clear = h6rows.filter((r) => r.lo > 0 || r.hi < 0);

  return (
    <Band id="h4">
      <Header id="h4" eyebrow="8">{copy.header}</Header>
      <p className="lede">{copy.lede}</p>
      {timeline && (
        <ChartFrame
          caption="The day H4 was designed, run and decided. Click a tick for the entry."
          source="public/data/timeline.json ← SESSION_LOG.md"
          summary={
            <ul>
              {timeline.entries.filter((e) => e.date === "2026-09-12").map((e) => (
                <li key={e.time}>{e.time} — {e.title}</li>
              ))}
            </ul>
          }>
          <TimelineStrip timeline={timeline} days={["2026-09-12"]} height={110} />
        </ChartFrame>
      )}
      <p>
        The thinking step wins on {h4.h4a.wins} of {h4.n_datasets}{" "}
        (p = {h4.h4a.sign_test_p.toFixed(4)}) and the capability step on {h4.h4b.wins}{" "}
        (p = {h4.h4b.sign_test_p.toFixed(4)}), against the {h4.min_wins} the rule asks for:{" "}
        {v4.verdict}. One cross-validated probe reads all {h4.readers.length} readers on the same{" "}
        {h4.subsample}-image prefix, so every difference is paired.
      </p>
      {copy.body.map((p, i) => <p key={i}>{p}</p>)}


      <ChartFrame
        caption={`The reader chain: cross-validated probe AUC on the same ${h4.subsample}-image ` +
                 "prefix, one line per dataset. Hover a line to isolate it."}
        source="public/data/study.json ← results/evaluation.json"
        summary={
          <table className="data">
            <thead>
              <tr><th>dataset</th>{chain.map((m) => <th key={m}>{m}</th>)}</tr>
            </thead>
            <tbody>
              {Object.keys(h4.probe_auc).map((d) => (
                <tr key={d}>
                  <td>{d}</td>
                  {chain.map((m) => (
                    <td key={m}>{h4.probe_auc[d][m] != null ? fmt3(h4.probe_auc[d][m]) : "—"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        }>
        <Ladder order={chain} values={h4.probe_auc} yLabel="cross-validated probe AUC"
                label="Probe AUC per dataset across the nine readers" height={420}
                note={"A reader is a model plus a reasoning effort. The first four are the same " +
                      "four models with thinking off."} />
      </ChartFrame>

      <ChartFrame
        caption="Thinking's effect against how well the same model read the concepts without it."
        source="public/data/study.json ← results/evaluation.json (H4a)"
        summary={
          <p>
            The step is negative on the datasets the model already read well and positive on the
            ones it read badly: {h4.h4a.wins} of {h4.n_datasets} gains, and the losses are
            concentrated where the baseline probe was highest. That is what "conditional" means
            here, and why a single sign test says {v4.verdict}.
          </p>
        }>
        <ThinkingScatter />
      </ChartFrame>

      <h3>H6 — was medium simply the wrong operating point?</h3>
      <p>
        Lowering the frontier model's effort wins on {h6.wins} of {h6.n_datasets} and the higher
        effort wins on {h6.wins_for_more}, against the {h6.min_wins} either direction would need:{" "}
        {v6.verdict}. Exactly {h6clear.length} interval of the {h6rows.length} clears zero, and it
        is {h6clear.map((r) => r.dataset).join(", ")} — the dataset the prediction was aimed at.
      </p>
      <ChartFrame
        caption="gpt-5.6-terra at low minus the same model at medium, by the same probe."
        source="public/data/study.json ← results/evaluation.json (H6)"
        summary={
          <table className="data" style={{ maxWidth: "34rem" }}>
            <thead><tr><th>dataset</th><th style={{ textAlign: "left" }}>low − medium, 95%</th></tr></thead>
            <tbody>
              {h6rows.map((r) => (
                <tr key={r.dataset}>
                  <td>{r.dataset}</td>
                  <td style={{ textAlign: "left" }}>
                    {signed(r.median)} [{fmt3(r.lo)}, {fmt3(r.hi)}]
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        }>
        <Forest rows={h6rows} colour={armHue("C")}
                label="gpt-5.6-terra: low minus medium, probe AUC" />
      </ChartFrame>

      <p>
        <Dots per={v4.per_dataset} order={study.study.arm_b_datasets} label="H4a per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          H4a, thinking over no thinking: {h4.h4a.wins} of {h4.n_datasets} — {v4.verdict}.
        </span>
      </p>
      <p>
        <Dots per={v6.per_dataset} order={study.study.arm_b_datasets} label="H6 per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          H6, low over medium: {v6.wins} of {v6.n_datasets} — {v6.verdict}.
        </span>
      </p>

      <Callouts items={copy.callouts} />
    </Band>
  );
}
