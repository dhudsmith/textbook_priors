import { Band, Body, Callouts, ChartFrame, Header } from "../components/ui";
import { EffortWaterfall, effortCaveats, effortSummary } from "../charts/EffortWaterfall";
import { premise } from "../content";
import { useAsync } from "../hooks";
import { loadEffort } from "../data";

export function Premise() {
  const { data: effort, error } = useAsync(loadEffort);
  return (
    <Band id="premise">
      <Header id="premise" eyebrow="1">{premise.header}</Header>
      <p className="lede">{premise.lede}</p>
      <Body paras={premise.body} bullets={premise.bullets} />

      {error && <p className="note">Could not load the effort breakdown: {error}</p>}
      {effort && (
        <ChartFrame
          caption={premise.effortCaption}
          source="public/data/effort.json ← results/**/*.json manifests, benchmarks/, SESSION_LOG.md and git"
          summary={effortSummary(effort)}>
          <EffortWaterfall data={effort} />
        </ChartFrame>
      )}
      {effort && <p className="note">{effortCaveats(effort)}</p>}

      <Callouts items={premise.callouts} />
    </Band>
  );
}
