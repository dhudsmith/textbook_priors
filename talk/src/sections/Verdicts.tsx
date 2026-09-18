import { useTalk } from "../state";
import { Band, Bullets, Callouts, Header } from "../components/ui";
import { VerdictBoard } from "../charts/Verdicts";
import { verdicts as copy } from "../content";

export function Verdicts() {
  const { study } = useTalk();
  const supported = study.verdicts.filter((v) => v.supported);
  const not = study.verdicts.filter((v) => !v.supported);

  return (
    <Band id="verdicts">
      <Header id="verdicts" eyebrow="8">{copy.header}</Header>
      <p className="lede">
        {supported.map((v) => v.id.toUpperCase()).join(" and ")} met their rules. The other{" "}
        {not.length} did not.
      </p>

      <VerdictBoard />

      <Bullets items={copy.bullets} />
      <Callouts items={copy.callouts} />
    </Band>
  );
}
