import { Band, Body, Callouts, ChartFrame, Header } from "../components/ui";
import { EffortWaterfall, effortCaveats, effortSummary } from "../charts/EffortWaterfall";
import { premise } from "../content";
import { KIND_BLURB, KIND_LABEL } from "../content";
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

      <h3>Three kinds of callout</h3>
      <div className="controls" role="group" aria-label="Kinds of callout">
        {(["principle", "nearmiss", "agent"] as const).map((kind) => (
          <span key={kind} className={`chip legend kindchip ${kind}`}>
            <span className="swatch" aria-hidden="true" />
            <strong>{KIND_LABEL[kind]}</strong>&nbsp;— {KIND_BLURB[kind]}
          </span>
        ))}
      </div>

      <Callouts items={premise.callouts} />
    </Band>
  );
}
