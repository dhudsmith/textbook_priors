import { Band, Callouts, ChartFrame, Header } from "../components/ui";
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
      {premise.body.map((p, i) => <p key={i}>{p}</p>)}

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

      <h3>Three kinds of aside, and they run the whole way down</h3>
      <div className="callouts">
        {(["principle", "nearmiss", "agent"] as const).map((kind) => (
          <aside key={kind} className={`callout ${kind}`} data-open="true">
            <div className="label">{KIND_LABEL[kind]}</div>
            <div className="body" style={{ marginTop: "0.2rem" }}>{KIND_BLURB[kind]}</div>
          </aside>
        ))}
      </div>

      <Callouts items={premise.callouts} />
    </Band>
  );
}
