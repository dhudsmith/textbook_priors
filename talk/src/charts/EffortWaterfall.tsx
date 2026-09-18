import { useMemo } from "react";
import { scaleLinear } from "d3-scale";
import { useWidth } from "../hooks";
import { plotBox, useHover, spreadLabels } from "./primitives";

/* Where the recorded work went, split two ways over the same hours.

   Two bands, one axis. The upper band cuts the project's hours by lifecycle activity; the lower
   band cuts the same hours by who or what spent them. They are the same total and the same scale,
   so the eye reads them against each other: everything a person and an agent did fits inside the
   first sixth of the bar, and the rest is a model answering.

   The axis is hours, not a percentage, because the magnitude is the argument. It is linear, not
   logarithmic, for the same reason - a log axis would flatter the small end and hide the point.
   The cost is that three activities are thinner than their own labels, so every segment is direct
   labelled off the bar with a leader, and hue is never the only encoding: the two bands share one
   divider, the band-2 labels name the actor in words, and each segment carries its hours.

   The one thing the sources cannot do is split the attended window into human time and agent
   time. The band says "a person and the agent" because that is what the timestamps support; the
   caption has to say so too, and `data.caveats` carries the sentence. */

export interface EffortActivity {
  id: string; label: string; short: string; hours: number;
  machine_hours: number; attended_hours: number; actor: "machine" | "attended";
}
export interface EffortActor {
  id: string; label: string; short: string; hours: number; detail: string;
}
export interface Effort {
  total_hours: number;
  activities: EffortActivity[];
  actors: EffortActor[];
  counts: {
    prompts: number; commits: number; lines_changed: number; jobs: number; calls: number;
    days: number; uncommitted_intervals: number;
  };
  machine: {
    wall_hours: number; cpu_hours: number; busy_wall_hours: number; mean_concurrency: number;
    first_job: string; last_job: string;
  };
  attended: { hours: number; days: { date: string; hours: number; prompts: number }[] };
  per_prompt: { machine_hours: number; calls: number; jobs: number; lines_changed: number };
  method: string[];
  caveats: string[];
}

/* Two hues, one per actor, used in both bands so the bands are read together: the keyboard end is
   the page's principle blue, the machine end its neutral ink. Within a band the segments alternate
   full and washed tone of their actor's hue, which separates neighbours without inventing a third
   meaning for a third colour. */
const HUE: Record<string, string> = {
  attended: "var(--principle)",
  machine: "var(--ink-secondary)",
};

const hours = (h: number) => (h >= 10 ? h.toFixed(0) : h >= 1 ? h.toFixed(1) : h.toFixed(2));
const hoursLabel = (h: number) => `${hours(h)} h`;

type Seg = {
  id: string; label: string; short: string; hours: number; actor: string;
  x0: number; x1: number; tone: number; tip: React.ReactNode;
};

/* A segment wide enough to hold its own name keeps it inside the bar, on the fill; a thinner one
   sends it out on a leader. The threshold is the widest short label at the chart's own text size,
   which is why it is measured in characters rather than guessed in pixels. */
const CH = 6.2;
const fits = (px: number, text: string) => px >= text.length * CH + 18;

export function EffortWaterfall({ data, height = 300 }: { data: Effort; height?: number }) {
  const { ref, width: measured } = useWidth<HTMLDivElement>(820);
  const { show, hide, tip } = useHover();
  const margin = useMemo(() => ({ top: 118, right: 16, bottom: 52, left: 16 }), []);
  const { width } = plotBox(measured, margin);
  const innerW = Math.max(220, width - margin.left - margin.right);

  const total = data.total_hours;
  const x = scaleLinear().domain([0, total]).range([margin.left, margin.left + innerW]);

  /* Band 1 is ordered by how much of each activity the machine did, least first, so the band's
     own hue change lands at the same place as band 2's divider and the two bands line up. */
  const bands = useMemo(() => {
    const ordered = [...data.activities].sort((a, b) => {
      const share = (s: EffortActivity) => (s.hours ? s.machine_hours / s.hours : 0);
      return share(a) - share(b) || a.hours - b.hours;
    });
    const walk = (items: { id: string; label: string; short: string; hours: number;
                           actor: string; tip: React.ReactNode }[]): Seg[] => {
      let at = 0;
      return items.map((it, i) => {
        const seg = { ...it, x0: at, x1: at + it.hours, tone: i % 2 };
        at += it.hours;
        return seg;
      });
    };
    const activity = walk(ordered.map((a) => ({
      id: a.id, label: a.label, short: a.short, hours: a.hours, actor: a.actor,
      tip: (
        <>
          <div className="k">{a.label}</div>
          <strong>{hoursLabel(a.hours)}</strong>{" "}
          — {((100 * a.hours) / total).toFixed(1)}% of {hours(total)} h
          <div className="k mono">
            {hoursLabel(a.machine_hours)} machine · {hoursLabel(a.attended_hours)} at the keyboard
          </div>
        </>
      ),
    })));
    const actor = walk(data.actors.map((a) => ({
      id: a.id, label: a.label, short: a.short, hours: a.hours, actor: a.id,
      tip: (
        <>
          <div className="k">{a.label}</div>
          <strong>{hoursLabel(a.hours)}</strong>{" "}
          — {((100 * a.hours) / total).toFixed(1)}% of {hours(total)} h
          <div className="k mono">{a.detail}</div>
        </>
      ),
    })));
    return { activity, actor };
  }, [data, total]);

  const rowH = 46;
  const yAct = margin.top;
  const yWho = margin.top + rowH + 58;
  const divider = data.actors.find((a) => a.id === "attended")?.hours ?? 0;

  /* Direct labels. A segment that can hold its name wears it inside, on the fill; the rest go
     above the band on leaders, alternating between two tiers so that neighbours a few pixels
     apart do not have to share one line. Within a tier they are pushed apart, and the two nearest
     each edge are anchored to it so nothing runs off the plot. */
  const outside = (segs: Seg[]) => {
    const thin = segs.filter((s2) => !fits(x(s2.x1) - x(s2.x0), s2.short));
    const tiers = [0, 1].map((t) => thin.filter((_, i) => i % 2 === t));
    return tiers.flatMap((tier, t) => {
      const spread = spreadLabels(
        tier.map((s2) => ({ id: s2.id, y: x((s2.x0 + s2.x1) / 2) })),
        (Math.max(...tier.map((s2) => s2.short.length), 1) + 2) * CH,
        x(0), x(total));
      return tier.map((s2) => {
        const half = (s2.short.length * CH) / 2;
        const put = spread.find((q) => q.id === s2.id)!.y;
        return {
          seg: s2, tier: t,
          anchor: x((s2.x0 + s2.x1) / 2),
          at: Math.min(Math.max(put, x(0) + half), x(total) - half),
        };
      });
    });
  };
  /* Band 1 hangs its leaders above the bar and band 2 below, so neither band's labels can ever
     land in the other's row however narrow the frame gets. The drawn height follows from that
     rather than being asserted: `height` is a floor, not the answer. */
  const actOutside = outside(bands.activity);
  const whoOutside = outside(bands.actor);
  const whoTiers = whoOutside.length ? Math.max(...whoOutside.map((o) => o.tier)) + 1 : 0;
  const bracketY = yWho + rowH + 14 + whoTiers * 30;
  const drawn = Math.max(height, bracketY + 34);

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={drawn} role="img"
           aria-label={`${hours(total)} hours of recorded work, split by activity and by who did ` +
                       `it: ${hours(divider)} hours at a keyboard against ` +
                       `${hours(data.machine.wall_hours)} hours of machine time`}>
        {/* one divider through both bands: where the keyboard ends and the machine begins */}
        <line x1={x(divider)} x2={x(divider)} y1={yAct - 6} y2={yWho + rowH + 6}
              stroke="var(--rule-strong)" strokeWidth={1} strokeDasharray="3 3" />

        {[{ segs: bands.activity, y: yAct, out: actOutside, below: false,
            title: "the kind of work" },
          { segs: bands.actor, y: yWho, out: whoOutside, below: true,
            title: "who or what did it" }]
          .map((band) => (
            <g key={band.title}>
              <text x={margin.left} y={band.y - (band.below ? 14 : 92)} className="axis"
                    style={{ fontSize: "var(--chart-row)", fontWeight: 700, fill: "var(--ink)" }}>
                {band.title}
              </text>
              {band.segs.map((s) => {
                const w = x(s.x1) - x(s.x0);
                const inside = fits(w, s.short);
                return (
                  <g key={s.id} onMouseEnter={(e) => show(e, s.tip)} onMouseLeave={hide}>
                    <rect x={x(s.x0)} y={band.y} width={Math.max(1.2, w)} height={rowH}
                          fill={HUE[s.actor] ?? "var(--ink-muted)"}
                          fillOpacity={s.tone ? 0.58 : 1}
                          stroke="var(--surface)" strokeWidth={0.75} />
                    {inside && (
                      <>
                        <text x={x(s.x0) + w / 2} y={band.y + rowH / 2 - 2} textAnchor="middle"
                              style={{ fontSize: "var(--chart-text)", fill: "var(--surface)",
                                       fontWeight: 600 }}>
                          {s.short}
                        </text>
                        <text x={x(s.x0) + w / 2} y={band.y + rowH / 2 + 13} textAnchor="middle"
                              style={{ fontSize: "var(--chart-tick)", fill: "var(--surface)",
                                       fillOpacity: 0.85 }}>
                          {hoursLabel(s.hours)}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}
              {band.out.map(({ seg, anchor, at, tier }) => {
                const edge = band.below
                  ? band.y + rowH + 16 + tier * 30
                  : band.y - 16 - tier * 30;
                const from = band.below ? band.y + rowH + 2 : band.y - 2;
                const name = band.below ? edge + 12 : edge - 14;
                const value = band.below ? edge + 23 : edge - 3;
                return (
                  <g key={seg.id} onMouseEnter={(e) => show(e, seg.tip)} onMouseLeave={hide}>
                    <path d={`M${anchor} ${from} V${edge} H${at}`} fill="none"
                          stroke="var(--rule-strong)" strokeWidth={0.9} />
                    <text x={at} y={name} textAnchor="middle" className="axis"
                          style={{ fontSize: "var(--chart-tick)", fill: "var(--ink-muted)" }}>
                      {seg.short}
                    </text>
                    <text x={at} y={value} textAnchor="middle" className="axis"
                          style={{ fontSize: "var(--chart-text)", fontWeight: 600,
                                   fill: "var(--ink)" }}>
                      {hoursLabel(seg.hours)}
                    </text>
                  </g>
                );
              })}
            </g>
          ))}

        {/* the wall clock the machine hours actually occupied, drawn on the same scale under the
            machine segment: 290 h of job time went past in 13 h because 22 jobs ran at once */}
        <g>
          <path d={`M${x(divider)} ${bracketY} v8 H${x(divider + data.machine.busy_wall_hours)} v-8`}
                fill="none" stroke="var(--good)" strokeWidth={1.5} />
          <text x={x(divider + data.machine.busy_wall_hours) + 9} y={bracketY + 12}
                className="axis" style={{ fontSize: "var(--chart-tick)", fill: "var(--good)" }}>
            …and it all went past in {hours(data.machine.busy_wall_hours)} h of wall clock:{" "}
            {data.machine.mean_concurrency.toFixed(1)} jobs in flight at once
          </text>
        </g>
      </svg>
      {tip}

      <div className="controls" aria-label="What each hour was spent on">
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="12" height="12" aria-hidden="true">
            <rect width="12" height="12" rx="2" fill={HUE.attended} />
          </svg>
          at the keyboard — {hoursLabel(divider)}, {data.counts.prompts} prompts
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="12" height="12" aria-hidden="true">
            <rect width="12" height="12" rx="2" fill={HUE.machine} />
          </svg>
          machine — {hoursLabel(data.machine.wall_hours)}, {data.counts.jobs.toLocaleString()} jobs
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          one prompt bought {data.per_prompt.machine_hours} machine-hours and{" "}
          {data.per_prompt.calls.toLocaleString()} model calls
        </span>
      </div>

    </div>
  );
}

/** The chart read as text, for `<ChartFrame summary>`. Built from the same object the bars are,
    so the spoken reading cannot drift from the picture. */
export function effortSummary(data: Effort) {
  return (
    <>
      <p>
        {hours(data.total_hours)} hours of recorded work, cut two ways. By activity:{" "}
        {data.activities.map((a) => `${a.label}, ${hoursLabel(a.hours)}`).join("; ")}. By actor:{" "}
        {data.actors.map((a) => `${a.label}, ${hoursLabel(a.hours)} — ${a.detail}`).join("; ")}.
      </p>
      <p>
        The machine's {hours(data.machine.wall_hours)} hours of job time elapsed in only{" "}
        {hours(data.machine.busy_wall_hours)} hours of wall clock, a mean of{" "}
        {data.machine.mean_concurrency.toFixed(1)} jobs in flight. One prompt bought, on average,{" "}
        {data.per_prompt.machine_hours} machine-hours and{" "}
        {data.per_prompt.calls.toLocaleString()} model calls.
      </p>
      <p>{data.caveats.join(" ")}</p>
    </>
  );
}

/** The chart's own caveats, as the section's caption should carry them. Read from the data so the
    caption cannot drift from the export that produced the bars. */
export function effortCaveats(data: Effort): string {
  return data.caveats.join(" ");
}
