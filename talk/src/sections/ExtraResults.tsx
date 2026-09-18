import { useState } from "react";
import { useTalk } from "../state";
import { Bullets, ChartFrame, Dots } from "../components/ui";
import { Ladder } from "../charts/Ladder";
import { ladderExtra as copy } from "../content";
import { signed, widestSpread } from "../charts/primitives";

/* Model size and the price ladder left the talk: twenty-five minutes did not have room for them
   and the verdict table is where the room meets them now. The whole comparison lives here. */

export function LadderBlock() {
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

  // The family sizes come from the snapshot, never from the copy.
  const sizes = (family: string) => openOrder.filter((m) => models[m].family === family)
    .map((m) => models[m].params_b);
  const lede = copy.ledeShape
    .replace("{qLo}", String(Math.min(...sizes(families[0]))))
    .replace("{qHi}", String(Math.max(...sizes(families[0]))))
    .replace("{gLo}", String(Math.min(...sizes(families[1]))))
    .replace("{gHi}", String(Math.max(...sizes(families[1]))));

  return (
    <div>
      <h4>{copy.header}</h4>
      <p className="lede">{lede}</p>
      <p>
        Within the qwen family the larger model wins on {qwen.wins} of{" "}
        {study.study.arm_b_datasets.length} (p = {qwen.sign_test_p.toFixed(4)}); within gemma,{" "}
        {gemma.wins} (p = {gemma.sign_test_p.toFixed(4)}). The rule asks for {v3.threshold} in both
        families: {v3.verdict}. A Friedman test over the four models gives{" "}
        p = {Number(h3.friedman.p).toFixed(2)}. The closed family, ranked by price alone, is the
        contrast: the top of the ladder beats the bottom on {h7.wins} of {h7.n_datasets}{" "}
        (p = {h7.sign_test_p.toFixed(4)}), which is {v7.verdict}.
      </p>
      <Bullets items={copy.bullets} />

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
          : "One line per dataset across the closed family at effort low, in price order. Hover a line to isolate it."}>
        <Ladder
          order={order}
          values={values}
          named={widestSpread(values, order)}
          yLabel={which === "open"
            ? "arm B test AUC"
            : "probe AUC (one head per model, all fitted the same way)"}
          label={which === "open"
            ? "Arm B AUC per dataset across the four open models"
            : "Probe AUC per dataset across the closed price ladder"}
          divideAfter={which === "open" && familyDivide >= 0 ? familyDivide : undefined}
          note={which === "open"
            ? "The divider separates the two families."
            : "Price is the vendor's ranking, not a parameter count."}
        />
      </ChartFrame>

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
          {signed(median(Object.values(h7.differences).map((d) => (d as { median: number }).median)))}{" "}
          AUC.
        </span>
      </p>
    </div>
  );
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
