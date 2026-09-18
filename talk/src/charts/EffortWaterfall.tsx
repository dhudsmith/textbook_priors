import { scaleLinear } from "d3-scale";
import { useWidth } from "../hooks";
import { plotBox, rowLeft, useHover } from "./primitives";

/* The project's timeline: what happened, when, in lanes over one clock.

   Four lanes, two of instants and two of intervals, and the difference between them is the whole
   point. A prompt and a commit are dated to the minute and nothing in the repository says how
   long either took, so they are drawn as marks with no width - a tick, a dot - and never given a
   bar. A job's manifest states its own `wall_seconds`, so a job is a bar, and the bar means what
   a bar should mean.

   Where jobs of one lane overlap, the lane draws the period they occupied between them rather
   than one bar per job: 587 score jobs in seventeen waves read as seventeen bars, not as a wall.
   The count in each is in the tooltip and the lane's own total sits in the gutter.

   One continuous axis rather than a row per day. The shape of this project is bursts separated
   by gaps - two and a half days pass between the last result and the first talk prompt - and a
   row per day normalises every day to the same width, which is exactly the information the
   picture exists to show. */

export interface EffortLane {
  id: string; kind: "point" | "span" | "rate"; label: string; count: number; note: string;
  agent_count?: number; hours?: number; cpu_hours?: number; busy_hours?: number; blocks?: number;
  chunks?: number; peak_per_hour?: number; peak_per_bin?: number; bin_minutes?: number;
  mean_per_hour?: number; unit?: string;
}
export interface EffortPoint { minute: number; at: string; title: string; agent?: boolean }
export interface Effort {
  span: { from: string; to: string; minutes: number };
  days: { date: string; minute: number }[];
  lanes: EffortLane[];
  points: Record<string, EffortPoint[]>;
  /** per lane: [start minute, end minute, jobs in the block] */
  spans: Record<string, [number, number, number][]>;
  /** per lane: [bin start minute, calls in the bin]; the bin width is the lane's bin_minutes */
  rates: Record<string, [number, number][]>;
  counts: {
    calls_peak_per_hour: number; prompts: number; commits: number; agent_commits: number;
    jobs: number; calls: number; machine_hours: number; days_with_prompts: number;
  };
  machine: {
    wall_hours: number; cpu_hours: number; busy_wall_hours: number; mean_concurrency: number;
    peak_concurrency: number; first_job: string; last_job: string;
  };
  headline: string;
  method: string[];
  caveats: string[];
}

const LANE_HUE: Record<string, string> = {
  prompts: "var(--principle)",
  commits: "var(--agent)",
  /* the service's two lanes share a hue on purpose: the bars are when its jobs were open, the
     area above them how hard it was working inside those windows */
  calls: "var(--nearmiss)",
  llm_jobs: "var(--nearmiss)",
  local_jobs: "var(--good)",
};

const ROW = 38;
/* the rate lane is the loudest thing in the figure because it carries the largest number, so it
   gets the height an area needs to be read as a shape rather than as a thick bar */
const RATE_ROW = 72;
const rowH = (lane: EffortLane) => (lane.kind === "rate" ? RATE_ROW : ROW);
const dayLabel = (d: string) => `${Number(d.slice(8, 10))} Sep`;
const hrs = (h: number) => (h >= 10 ? h.toFixed(0) : h >= 1 ? h.toFixed(1) : h.toFixed(2));

/** The one-line tally under a lane's name: what it counted, and what that cost. */
function laneTally(lane: EffortLane): string {
  if (lane.kind === "point") {
    return lane.agent_count != null
      ? `${lane.count} · ${lane.agent_count} co-authored by an agent`
      : `${lane.count}`;
  }
  if (lane.kind === "rate") {
    return `${lane.count.toLocaleString()} calls in ${lane.chunks} chunks · peak `
      + `${Math.round(lane.peak_per_bin ?? 0).toLocaleString()} in ${lane.bin_minutes} min`;
  }
  return `${lane.count} jobs · ${hrs(lane.hours ?? 0)} h wall · ${hrs(lane.cpu_hours ?? 0)} h CPU`;
}

/** The bins the export already chose, as a step outline. The export fixes the bin width so the
    peak the lane names is the peak the lane draws, whatever the browser is doing. */
function rateOutline(rows: [number, number][], binMinutes: number,
                     x: (m: number) => number, top: number, base: number, ceiling: number) {
  const at = (v: number) => base - (v / ceiling) * (base - top);
  const parts: string[] = [];
  for (const [start, calls] of rows) {
    const a = x(start);
    const b = Math.max(x(start + binMinutes), a + 1);
    parts.push(`M${a.toFixed(1)},${base.toFixed(1)}`
               + `L${a.toFixed(1)},${at(calls).toFixed(1)}`
               + `L${b.toFixed(1)},${at(calls).toFixed(1)}`
               + `L${b.toFixed(1)},${base.toFixed(1)}Z`);
  }
  return parts.join("");
}

export function EffortWaterfall({ data, height }: { data: Effort; height?: number }) {
  const { ref, width: measured } = useWidth<HTMLDivElement>(820);
  const { width, tight } = plotBox(measured);
  const { show, hide, tip } = useHover();

  const left = rowLeft(measured, 214);
  const right = 12;
  const top = 30;
  const innerW = Math.max(200, width - left - right);
  const offsets: number[] = [];
  let stack = 0;
  for (const lane of data.lanes) {
    offsets.push(stack);
    stack += rowH(lane);
  }
  const plotH = stack;
  const drawn = Math.max(height ?? 0, top + plotH + 16);

  const x = scaleLinear().domain([0, data.span.minutes]).range([left, left + innerW]);
  const minute = (m: number) => x(m);

  /* A bar never renders narrower than a hairline, so a two-minute wave is still visible. The
     floor is a drawing minimum, not a duration: the tooltip carries the real one. */
  const barW = (a: number, b: number) => Math.max(3, minute(b) - minute(a));

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={drawn} role="img"
           aria-label={`What happened when, from ${data.span.from.slice(0, 10)} to ` +
                       `${data.span.to.slice(0, 10)}, in ${data.lanes.length} lanes over one ` +
                       `clock: ${data.counts.prompts} prompts and ${data.counts.commits} times ` +
                       `code was written, each drawn as a moment, and ${data.counts.jobs} jobs ` +
                       "drawn as the periods they ran"}>
        {/* alternating lane bands, so a row is followed across a wide plot */}
        {data.lanes.map((lane, i) => (
          i % 2 === 1 ? (
            <rect key={`band-${lane.id}`} x={0} y={top + offsets[i]} width={width}
                  height={rowH(lane)} fill="var(--surface-sunken)" />
          ) : null
        ))}

        {/* the days: one gridline each, labelled across the top like a project plan */}
        <g className="axis">
          {data.days.map((d, i) => {
            /* the span starts mid-morning, so the first day's midnight sits off the plot: its
               gridline is dropped and its label centred on the part of the day that is shown */
            const a = Math.max(minute(d.minute), left);
            const b = Math.min(i + 1 < data.days.length
              ? minute(data.days[i + 1].minute) : left + innerW, left + innerW);
            return (
              <g key={d.date}>
                {minute(d.minute) >= left && (
                  <line x1={a} x2={a} y1={top - 6} y2={top + plotH} stroke="var(--rule)" />
                )}
                {b - a > 26 && (
                  <text x={(a + b) / 2} y={top - 12} textAnchor="middle"
                        style={{ fontSize: "var(--chart-tick)", fill: "var(--ink-muted)" }}>
                    {dayLabel(d.date)}
                  </text>
                )}
              </g>
            );
          })}
          <line x1={left} x2={left + innerW} y1={top} y2={top} stroke="var(--rule-strong)" />
        </g>

        {data.lanes.map((lane, i) => {
          const y0 = top + offsets[i];
          const h = rowH(lane);
          const mid = y0 + h / 2;
          const hue = LANE_HUE[lane.id] ?? "var(--ink-secondary)";
          return (
            <g key={lane.id}>
              <text x={8} y={mid - 3} className="axis"
                    style={{ fontSize: "var(--chart-row)", fontWeight: 600, fill: "var(--ink)" }}>
                {tight && lane.label.length > 24 ? `${lane.label.slice(0, 23)}…` : lane.label}
              </text>
              {/* Two clear pixels under the lane's name: at 14 px apart the tally's ascenders
                  met the name's descenders. */}
              <text x={8} y={mid + 14} className="axis"
                    style={{ fontSize: "var(--chart-tick)", fill: "var(--ink-muted)" }}>
                {laneTally(lane)}
              </text>

              {lane.kind === "rate" && (() => {
                const rows = data.rates[lane.id] ?? [];
                const bin = lane.bin_minutes ?? 15;
                const ceiling = Math.max(1, lane.peak_per_bin ?? 1);
                const base = y0 + h - 7;
                const d = rateOutline(rows, bin, minute, y0 + 15, base, ceiling);
                const peakAt = rows.reduce((best, r) => (r[1] > best[1] ? r : best),
                                           [0, 0] as [number, number]);
                return (
                  <g onMouseEnter={(e) => show(e, (
                       <>
                         <div className="k">{lane.label}</div>
                         <strong>{lane.count.toLocaleString()} calls</strong> across{" "}
                         {lane.chunks} chunks · peak{" "}
                         {Math.round(lane.peak_per_bin ?? 0).toLocaleString()} in {bin} min
                         {" "}({Math.round(lane.peak_per_hour ?? 0).toLocaleString()}/h), mean{" "}
                         {Math.round(lane.mean_per_hour ?? 0).toLocaleString()}/h while the
                         service was busy
                         <div className="k mono">{lane.note}</div>
                       </>
                     ))} onMouseLeave={hide}>
                    <rect x={left} y={y0} width={innerW} height={h} fill="transparent" />
                    <line x1={left} x2={left + innerW} y1={base} y2={base} stroke="var(--rule)" />
                    <path d={d} fill={hue} fillOpacity={0.85} stroke={hue} strokeWidth={0.6} />
                    <text x={Math.min(minute(peakAt[0]) + 7, left + innerW - 120)}
                          y={y0 + 22} className="axis"
                          style={{ fontSize: "var(--chart-tick)", fill: "var(--ink-muted)" }}>
                      peak {Math.round(lane.peak_per_bin ?? 0).toLocaleString()} calls in {bin} min
                    </text>
                  </g>
                );
              })()}
              {lane.kind === "span" && (
                /* the track a bar sits on: without it a two-minute wave reads as a tick */
                <line x1={left} x2={left + innerW} y1={mid} y2={mid} stroke="var(--rule)"
                      strokeWidth={1} />
              )}
              {lane.kind === "span" && (data.spans[lane.id] ?? []).map(([a, b, n]) => (
                <g key={`${lane.id}-${a}`}
                   onMouseEnter={(e) => show(e, (
                     <>
                       <div className="k">{lane.label}</div>
                       <strong>{n} job{n === 1 ? "" : "s"}</strong> over{" "}
                       {b - a >= 60 ? `${((b - a) / 60).toFixed(1)} h` : `${(b - a).toFixed(0)} min`}
                       <div className="k mono">{lane.note}</div>
                     </>
                   ))} onMouseLeave={hide}>
                  <rect x={minute(a)} y={mid - 16} width={barW(a, b)} height={32}
                        fill="transparent" />
                  <rect x={minute(a)} y={mid - 7} width={barW(a, b)} height={14} rx={2}
                        fill={hue} />
                </g>
              ))}

              {lane.kind === "point" && (data.points[lane.id] ?? []).map((p) => (
                <g key={`${lane.id}-${p.at}-${p.title.slice(0, 8)}`}
                   onMouseEnter={(e) => show(e, (
                     <>
                       <div className="k mono">
                         {p.at.slice(0, 10)} {p.at.slice(11, 16)}
                         {p.agent === false ? " · no agent trailer" : ""}
                       </div>
                       <strong>{p.title}</strong>
                     </>
                   ))} onMouseLeave={hide}>
                  <rect x={minute(p.minute) - 4} y={y0 + 4} width={8} height={h - 8}
                        fill="transparent" style={{ cursor: "pointer" }} />
                  {lane.id === "prompts" ? (
                    /* an instant, drawn as an instant: a full-height tick with no width */
                    <line x1={minute(p.minute)} x2={minute(p.minute)} y1={mid - 11} y2={mid + 11}
                          stroke={hue} strokeWidth={2} strokeLinecap="round" />
                  ) : (
                    <circle cx={minute(p.minute)} cy={mid} r={3}
                            fill={p.agent === false ? "var(--surface)" : hue}
                            stroke={p.agent === false ? "var(--ink-muted)" : "none"}
                            strokeWidth={1.2} />
                  )}
                </g>
              ))}
            </g>
          );
        })}

        <line x1={left} x2={left} y1={top - 6} y2={top + plotH} stroke="var(--rule-strong)" />
        <line x1={left} x2={left + innerW} y1={top + plotH} y2={top + plotH}
              stroke="var(--rule-strong)" />
      </svg>
      {tip}

      <div className="controls" aria-label="How to read the lanes">
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="8" height="12" aria-hidden="true">
            <line x1="4" y1="1" x2="4" y2="11" stroke={LANE_HUE.prompts} strokeWidth="2"
                  strokeLinecap="round" />
          </svg>
          a tick is a moment — we know when it was, not how long it took
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="14" height="12" aria-hidden="true">
            <rect x="0" y="3" width="14" height="6" rx="2" fill={LANE_HUE.llm_jobs} />
          </svg>
          a bar is a period jobs ran — each job timed itself
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="16" height="12" aria-hidden="true">
            <path d="M0 11 L3 7 L6 9 L9 2 L12 6 L16 4 L16 11 Z" fill={LANE_HUE.calls}
                  fillOpacity="0.82" />
          </svg>
          an area is a rate — calls spread across the chunk that recorded them
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          peak {data.machine.peak_concurrency} jobs at once ·{" "}
          {hrs(data.machine.wall_hours)} h of job time inside{" "}
          {hrs(data.machine.busy_wall_hours)} h of wall clock
        </span>
      </div>
    </div>
  );
}

