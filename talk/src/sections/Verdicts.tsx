import { useTalk } from "../state";
import { Band, Bullets, Header } from "../components/ui";
import { VerdictBoard } from "../charts/Verdicts";
import { verdicts as copy } from "../content";

export function Verdicts() {
  const { study } = useTalk();
  const supported = study.verdicts.filter((v) => v.supported);
  const not = study.verdicts.filter((v) => !v.supported);

  return (
    <Band id="verdicts">
      <Header id="verdicts" eyebrow="9">{copy.header}</Header>
      <p className="lede">
        {supported.map((v) => v.id.toUpperCase()).join(" and ")} won on as many datasets as they
        needed. The other {not.length} did not.
      </p>

      <p className="note">
        {copy.modelsNote.replace("{primary}", study.study.primary)}
      </p>

      <VerdictBoard />

      <Bullets items={copy.bullets} />
    </Band>
  );
}
