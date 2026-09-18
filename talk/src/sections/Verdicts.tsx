import { useTalk } from "../state";
import { Band, Header, Points } from "../components/ui";
import { VerdictBoard } from "../charts/Verdicts";
import { verdicts as copy } from "../content";

/** The copy carries {placeholders} and no digits; the snapshot carries the digits. */
const fill = (shape: string, values: Record<string, string | number>) =>
  Object.entries(values).reduce(
    (out, [k, v]) => out.split(`{${k}}`).join(String(v)), shape);

export function Verdicts() {
  const { study } = useTalk();
  const head = study.headline;
  // The closed models are listed cheapest first, so the summary's two ends are the list's.
  const h7ladder = study.across.h7.ladder as string[];
  const modelOf = (reader: string) => study.study.readers[reader]?.model ?? reader;
  // H3 is one comparison per family, not one across all four models, so the summary gives both.
  const h3Wins = Object.values(study.across.h3.ladder)
    .map((l) => (l as { wins: number }).wins).sort((a, b) => a - b);

  /* Every count the summary quotes, in one place: the page types none of them. */
  const counts = {
    n: head.n_datasets,
    smallestN: head.smallest_n,
    aOverChance: head.a_over_chance,
    pixelOverA: head.pixel_over_a,
    bOverA: head.b_over_a,
    cOverA: head.c_over_a,
    cOverB: head.c_over_b,
    h5Wins: study.across.h5.wins, h5N: study.across.h5.n_datasets,
    h3Best: h3Wins[h3Wins.length - 1], h3Worst: h3Wins[0],
    h3N: study.across.h3.n_datasets,
    minWins: study.across.h3.min_wins,
    h7Wins: study.across.h7.wins, h7N: study.across.h7.n_datasets,
    dearest: modelOf(h7ladder[h7ladder.length - 1]),
    cheapest: modelOf(h7ladder[0]),
  };
  const supported = study.verdicts.filter((v) => v.supported);
  const not = study.verdicts.filter((v) => !v.supported);

  return (
    <Band id="verdicts">
      <Header id="verdicts">{copy.header}</Header>
      <p className="lede">
        {supported.map((v) => v.id.toUpperCase()).join(" and ")} won on as many datasets as they
        needed. The other {not.length} did not.
      </p>

      <p className="note">
        {copy.modelsNote.replace("{primary}", study.study.primary)}
      </p>

      <VerdictBoard />

      <h3>{copy.soWhat.header}</h3>
      <Points items={copy.soWhat.items.map((it) => ({
        summary: fill(it.summary, counts), detail: fill(it.detail, counts),
      }))} />
    </Band>
  );
}
