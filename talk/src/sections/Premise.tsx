import { Band, Body, Callouts, ChartFrame, Header } from "../components/ui";
import { TimelineStrip } from "../charts/TimelineStrip";
import { premise } from "../content";
import { KIND_BLURB, KIND_LABEL } from "../content";
import { useAsync } from "../hooks";
import { loadTimeline } from "../data";

export function Premise() {
  const { data: timeline, error } = useAsync(loadTimeline);
  return (
    <Band id="premise">
      <Header id="premise" eyebrow="1">{premise.header}</Header>
      <p className="lede">{premise.lede}</p>
      <Body paras={premise.body} bullets={premise.bullets} />

      {error && <p className="note">Could not load the timeline: {error}</p>}
      {timeline && (
        <ChartFrame
          caption="One tick per prompt that materially directed the work."
          source="public/data/timeline.json ← SESSION_LOG.md"
          summary={
            <p>
              {timeline.entries.length} timestamped entries across {timeline.days.length} days,
              from {timeline.days[0]} to {timeline.days[timeline.days.length - 1]}. Counted by
              kind:{" "}
              {timeline.kinds
                .map((k) => `${k.id} ${timeline.entries.filter((e) => e.kind === k.id).length}`)
                .join(", ")}. {timeline.kind_note}
            </p>
          }>
          <TimelineStrip timeline={timeline} />
        </ChartFrame>
      )}
      <p className="note">{premise.stripCaption}</p>

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
