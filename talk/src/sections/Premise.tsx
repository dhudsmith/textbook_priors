import { Band, Bullets, Callouts, ChartFrame, Header } from "../components/ui";
import { EffortWaterfall, effortSummary } from "../charts/EffortWaterfall";
import { premise } from "../content";
import { useAsync } from "../hooks";
import { loadEffort } from "../data";

export function Premise() {
  const { data: effort, error } = useAsync(loadEffort);
  return (
    <Band id="premise">
      <Header id="premise" eyebrow="1">{premise.header}</Header>
      <p className="lede">{premise.lede}</p>
      <Bullets items={premise.bullets} />

      {error && <p className="note">Could not load the effort breakdown: {error}</p>}
      {effort && (
        <ChartFrame
          caption={premise.effortCaption}
          source="public/data/effort.json ← results/**/*.json manifests, benchmarks/, SESSION_LOG.md and git"
          summary={effortSummary(effort)}>
          <EffortWaterfall data={effort} />
        </ChartFrame>
      )}

      <Callouts items={premise.callouts} />
    </Band>
  );
}
