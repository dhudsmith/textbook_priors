import { useState } from "react";
import { useTalk } from "../state";
import { Band, ChartFrame, Header } from "../components/ui";
import { Ladder } from "../charts/Ladder";
import { modelSize as copy } from "../content";
import { widestSpread } from "../charts/primitives";

/* Model size and price, back on the spine directly after the results figure. It was cut once for
   length, so it is one chart with two views and one sentence of what it found, and nothing else:
   the per-dataset dots, the bullets and the second verdict paragraph stay in the verdict board
   and in Extra. */

export function ModelSize() {
  const { study } = useTalk();
  const h3 = study.across.h3;
  const h7 = study.across.h7;
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
  // Every size in the sentence comes from the snapshot, never from the copy.
  const sizes = (family: string) => openOrder.filter((m) => models[m].family === family)
    .map((m) => models[m].params_b);
  const span = (family: string) =>
    `${Math.min(...sizes(family))}B to ${Math.max(...sizes(family))}B`;

  return (
    <Band id="size">
      <Header id="size">{copy.header}</Header>
      <p className="lede">
        Across two open families, {span(families[0])} and {span(families[1])}, the bigger model
        wins on {qwen.wins} and {gemma.wins} of {study.study.arm_b_datasets.length} datasets —
        no trend either way (Friedman p = {Number(h3.friedman.p).toFixed(2)}). Among the closed
        models, which nothing public ranks but price, the most expensive beats the cheapest
        on {h7.wins} of {h7.n_datasets}.
      </p>

      <div className="controls" role="group" aria-label="Which models">
        <span className="group-label">models</span>
        <button className="chip" aria-pressed={which === "open"} onClick={() => setWhich("open")}>
          {copy.toggle.open}
        </button>
        <button className="chip" aria-pressed={which === "closed"}
                onClick={() => setWhich("closed")}>
          {copy.toggle.closed}
        </button>
      </div>

      <ChartFrame caption={which === "open" ? copy.captions.open : copy.captions.closed}>
        <Ladder
          order={order}
          values={values}
          named={widestSpread(values, order)}
          yLabel={which === "open" ? "arm B test AUC" : "probe AUC"}
          label={which === "open"
            ? "Arm B test AUC for each dataset across the four open models, smallest first "
              + "within each family"
            : "Probe AUC for each dataset across the three closed models, cheapest first"}
          divideAfter={which === "open" && familyDivide >= 0 ? familyDivide : undefined}
          note={which === "open" ? copy.notes.open : copy.notes.closed}
        />
      </ChartFrame>
    </Band>
  );
}
