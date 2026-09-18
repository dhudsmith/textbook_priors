import { useState } from "react";
import { useTalk } from "../state";
import { Band, Body, Callouts, ChartFrame, Dots, Header, Slide } from "../components/ui";
import { Ladder } from "../charts/Ladder";
import { h3 as copy } from "../content";
import { fmt3, signed, widestSpread } from "../charts/primitives";

export function H3() {
  const { study } = useTalk();
  const h3 = study.across.h3;
  const h7 = study.across.h7;
  const v3 = study.verdicts.find((x) => x.id === "h3")!;
  const v7 = study.verdicts.find((x) => x.id === "h7")!;
  const [which, setWhich] = useState<"open" | "closed">("open");

  /* The axis is ordered family first, then size within it, so the dashed divider falls on the
     real family boundary - which is the one the note says not to read across. The order the
     snapshot ships interleaves the families, and drawn that way three of every four segments
     joined a qwen model to a gemma one. Families keep the order they first appear in. */
  const models = study.study.models;
  const families: string[] = [];
  for (const m of h3.model_order as string[]) {
    const f = models[m].family;
    if (!families.includes(f)) families.push(f);
  }
  const openOrder: string[] = [...(h3.model_order as string[])].sort((a, b) => {
    const fa = families.indexOf(models[a].family);
    const fb = families.indexOf(models[b].family);
    return fa !== fb ? fa - fb : models[a].params_b - models[b].params_b;
  });
  const familyDivide = openOrder.findIndex(
    (m, i) => i < openOrder.length - 1
      && models[m].family !== models[openOrder[i + 1]].family);
  const openValues = h3.arm_b_auc as Record<string, Record<string, number>>;
  const closedOrder: string[] = h7.ladder;
  const closedValues = h7.probe_auc as Record<string, Record<string, number>>;

  const order = which === "open" ? openOrder : closedOrder;
  const values = which === "open" ? openValues : closedValues;
  const qwen = h3.ladder.qwen;
  const gemma = h3.ladder.gemma;

  return (
    <Band id="h3">
      <Slide title={<Header id="h3" eyebrow="7">{copy.header}</Header>}>
      <p className="lede">{copy.lede}</p>
      <p>
        Within the qwen family the larger model wins on {qwen.wins} of{" "}
        {study.study.arm_b_datasets.length} (p = {qwen.sign_test_p.toFixed(4)}); within gemma,{" "}
        {gemma.wins} (p = {gemma.sign_test_p.toFixed(4)}). The rule asks for {v3.threshold} in both
        families: {v3.verdict}. A Friedman test over the four models gives{" "}
        p = {Number(h3.friedman.p).toFixed(2)}.
      </p>
      <p>
        The closed family, ordered by price alone, is the contrast: the top of the ladder beats the
        bottom on {h7.wins} of {h7.n_datasets} (p = {h7.sign_test_p.toFixed(4)}), which is{" "}
        {v7.verdict}.
      </p>
      <Body paras={copy.body.slice(1)} bullets={copy.bullets} />

      </Slide>

      <Slide cont title={<div className="conthead">{copy.header}</div>}
        figure={<div>
  <div className="controls" role="group" aria-label="Ladder">
          <span className="group-label">ladder</span>
          <button className="chip" aria-pressed={which === "open"} onClick={() => setWhich("open")}>
            open models, by size
          </button>
          <button className="chip" aria-pressed={which === "closed"}
                  onClick={() => setWhich("closed")}>
            closed models, by price
          </button>
        </div>

        <ChartFrame
          caption={which === "open"
            ? "One line per dataset across the four open models, in size order within family. Hover a line to isolate it."
            : "One line per dataset across the closed family at effort low, in price order. Hover a line to isolate it."}
          source="public/data/study.json ← results/evaluation.json"
          summary={
            <table className="data" style={{ maxWidth: "44rem" }}>
              <thead>
                <tr><th>dataset</th>{order.map((m) => <th key={m}>{m}</th>)}</tr>
              </thead>
              <tbody>
                {Object.keys(values).map((d) => (
                  <tr key={d}>
                    <td>{d}</td>
                    {order.map((m) => <td key={m}>{values[d][m] != null ? fmt3(values[d][m]) : "—"}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          }>
          <Ladder
            order={order}
            values={values}
            named={widestSpread(values, order)}
            yLabel={which === "open"
              ? "arm B test AUC"
              : "probe AUC (one classifier reads every model's answers)"}
            label={which === "open"
              ? "Arm B AUC per dataset across the four open models"
              : "Probe AUC per dataset across the closed price ladder"}
            divideAfter={which === "open" && familyDivide >= 0 ? familyDivide : undefined}
            note={(which === "open"
              ? "The dashed divider separates the two families: size and training data are " +
                "confounded across them, so the comparison is read within family only. "
              : "Price is the vendor's own ranking, used as a proxy for capability, not a " +
                "parameter count — nothing public orders these models by size. ") +
              "The four datasets that move most across the ladder are drawn in their own colours " +
              "and labelled; the rest are grey. Hover any line to isolate it."}
          />
        </ChartFrame>
        </div>}>
      {/* The paragraph that explains the divider now sits under the divider. */}
      <p className="presenter-hide">{copy.body[0]}</p>

      <p className="tally">
        <Dots per={v3.per_dataset} order={study.study.arm_b_datasets} label="H3 per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          H3, larger wins in both families: {v3.wins} of {v3.n_datasets} — {v3.verdict}.
        </span>
      </p>
      <p className="tally">
        <Dots per={v7.per_dataset} order={study.study.arm_b_datasets} label="H7 per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          H7, the top of the price ladder over the bottom: {v7.wins} of {v7.n_datasets},{" "}
          against {v7.threshold} needed — {v7.verdict}. Median step{" "}
          {signed(median(Object.values(h7.differences).map((d: any) => d.median)))} AUC.
        </span>
      </p>

      <Callouts items={copy.callouts} />
      </Slide>
    </Band>
  );
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
