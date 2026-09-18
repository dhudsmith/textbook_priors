import { useState } from "react";
import { useTalk } from "../state";
import { Band, Body, Callouts, ChartFrame, Dots, Header } from "../components/ui";
import { Forest } from "../charts/Forest";
import { h5 as copy } from "../content";
import { fmt3, signed } from "../charts/primitives";

export function H5() {
  const { study, armHue } = useTalk();
  const h5 = study.across.h5;
  const v = study.verdicts.find((x) => x.id === "h5")!;
  const ns: number[] = study.study.curve.n;
  const [n, setN] = useState(h5.n as number);

  const rows = study.study.datasets
    .map((dataset) => {
      const byN = h5.differences_by_n[dataset]?.[String(n)];
      return byN ? { dataset, ...(byN as { median: number; lo: number; hi: number }) } : null;
    })
    .filter(Boolean) as { dataset: string; median: number; lo: number; hi: number }[];

  const clear = rows.filter((r) => r.lo > 0);
  const registered = n === h5.n;
  const median = (v: number[]) => {
    const s = [...v].sort((a, b) => a - b); const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };

  return (
    <Band id="h5">
      <Header id="h5" eyebrow="9">{copy.header}</Header>
      <p className="lede">{copy.lede}</p>
      <p>
        At n = {h5.n}, the registered comparison, arm C+P beats arm P on {h5.wins} of{" "}
        {h5.n_datasets} against the {h5.min_wins} the rule asks for (p ={" "}
        {h5.sign_test_p.toFixed(4)}): <strong>{v.verdict}</strong>. Median gain{" "}
        {signed(median(Object.values(h5.differences).map((d: any) => d.median)))} AUC, and every
        winning interval clears zero.
      </p>
      <Body paras={copy.body} bullets={copy.bullets} />

      <div className="controls" role="group" aria-label="Labels (n)">
        <span className="group-label">labels (n)</span>
        {ns.map((v2) => (
          <button key={v2} className="chip" aria-pressed={n === v2} onClick={() => setN(v2)}>
            {v2}{v2 === h5.n ? " (registered)" : ""}
          </button>
        ))}
      </div>
      {!registered && (
        <p className="note">
          Every grid point other than n = {h5.n} is reported and decides nothing — the rule names
          one n, and this slider does not move it.
        </p>
      )}

      <ChartFrame
        caption={`Arm C+P minus arm P at n = ${n}: the same classifier, with the concept block ` +
                 "concatenated to the pixel block and nothing else changed."}
        source="public/data/study.json ← results/evaluation.json (H5)"
        summary={
          <table className="data" style={{ maxWidth: "34rem" }}>
            <thead>
              <tr><th>dataset</th><th style={{ textAlign: "left" }}>C+P − P, 95%</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
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
        <Forest rows={rows} colour={armHue("CP")} label={`arm C+P minus arm P at n = ${n}`}
                annotate={["no gain", "gain"]} />
      </ChartFrame>
      <p className="note">
        {clear.length} of {rows.length} gains are clear of zero at n = {n}. Rows whose interval
        spans zero are drawn at half strength.
      </p>

      <p className="tally">
        <Dots per={v.per_dataset} order={study.study.datasets} label="H5 per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          {v.wins} of {v.n_datasets}, against {v.threshold} needed — {v.verdict}.
        </span>
      </p>

      <Callouts items={copy.callouts} />
    </Band>
  );
}
