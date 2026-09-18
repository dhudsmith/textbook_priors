import { useTalk } from "../state";
import { Band, Bullets, Callouts, ChartFrame, Deep, Header } from "../components/ui";
import { EffortWaterfall } from "../charts/EffortWaterfall";
import { Contention } from "../charts/Contention";
import { premise } from "../content";
import { useAsync } from "../hooks";
import { loadContention, loadEffort } from "../data";

export function Premise() {
  const { study } = useTalk();
  const { data: effort, error } = useAsync(loadEffort);
  const { data: contention } = useAsync(loadContention);

  // The bullets are the owner's wording with this run's own numbers dropped in, so a re-export
  // moves them rather than leaving a stale count on the wall.
  const n = (v: number) => v.toLocaleString("en-US");
  const bullets = effort
    ? premise.bulletShapes.map((shape) =>
        shape
          .replace("{prompts}", n(effort.counts.prompts))
          .replace("{jobs}", n(effort.counts.jobs))
          .replace("{calls}", n(effort.counts.calls))
          .replace("{machineHours}", n(Math.round(effort.machine.wall_hours)))
          .replace("{hypotheses}", n(study.ledger.hypotheses))
          .replace("{datasets}", n(study.ledger.datasets)))
    : [];

  return (
    <Band id="premise">
      <Header id="premise" eyebrow="9">{premise.header}</Header>
      <p className="lede">{premise.lede}</p>
      <Bullets items={bullets} />

      {error && <p className="note">Could not load the effort breakdown: {error}</p>}
      {effort && (
        <ChartFrame
          caption={premise.effortCaptionShape.replace("{days}", String(effort.days.length))}>
          <EffortWaterfall data={effort} />
        </ChartFrame>
      )}

      <Callouts items={premise.callouts} />
      {contention && (
        <Deep summary="What our own load did to a single call">
          <ChartFrame
            caption="One job on its own against many at once, per prompt.">
            <Contention data={contention} />
          </ChartFrame>
        </Deep>
      )}
    </Band>
  );
}
