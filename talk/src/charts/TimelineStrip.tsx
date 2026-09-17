import { useMemo, useState } from "react";
import { scaleLinear } from "d3-scale";
import type { Timeline, TimelineEntry } from "../types";
import { useWidth } from "../hooks";
import { useHover, plotBox, short as _short } from "./primitives";

void _short;

/* One tick per prompt that materially directed the work. Time is the x axis (real clock time
   within each day), the kind is the colour, and every kind also has its own row, so the encoding
   is position-plus-colour rather than colour alone. */

const KIND_COLOUR: Record<string, string> = {
  direct: "var(--principle)",
  build: "var(--ink-secondary)",
  run: "var(--good)",
  decide: "var(--agent)",
  catch: "var(--nearmiss)",
  rewind: "var(--ink-muted)",
};

const minutes = (e: TimelineEntry) => {
  const [h, m] = e.time.split(":").map(Number);
  return h * 60 + m;
};

export function TimelineStrip({ timeline, days, height = 150 }: {
  timeline: Timeline; days?: string[]; height?: number;
}) {
  const { ref, width: measured } = useWidth<HTMLDivElement>(760);
  const { width, tight } = plotBox(measured);
  const { show, hide, tip } = useHover();
  const [picked, setPicked] = useState<TimelineEntry | null>(null);

  const shownDays = days ?? timeline.days;
  const entries = useMemo(
    () => timeline.entries.filter((e) => shownDays.includes(e.date)),
    [timeline.entries, shownDays]);

  const margin = { top: 14, right: 12, bottom: 30, left: 56 };
  const inner = Math.max(220, width - margin.left - margin.right);
  const rowH = (height - margin.top - margin.bottom) / Math.max(1, shownDays.length);
  const lo = Math.min(...entries.map(minutes)) - 25;
  const hi = Math.max(...entries.map(minutes)) + 25;
  const x = scaleLinear().domain([lo, hi]).range([margin.left, margin.left + inner]);
  // Nine HH:MM labels sat edge to edge at 390 px with no gap between them.
  const hours = [];
  for (let h = Math.ceil(lo / 60); h * 60 <= hi; h += tight ? 4 : 2) hours.push(h);

  const kinds = timeline.kinds.filter((k) => entries.some((e) => e.kind === k.id));

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img"
           aria-label={`${entries.length} directing prompts across ${shownDays.length} day(s), ` +
                       `one tick each, from SESSION_LOG.md`}>
        <g className="axis">
          {hours.map((h) => (
            <g key={h} transform={`translate(${x(h * 60)} 0)`}>
              <line y1={margin.top - 6} y2={height - margin.bottom} stroke="var(--grid)" />
              <text y={height - margin.bottom + 15} textAnchor="middle">
                {String(h).padStart(2, "0")}:00
              </text>
            </g>
          ))}
        </g>
        {shownDays.map((day, i) => {
          const y = margin.top + rowH * i + rowH / 2;
          return (
            <g key={day}>
              <text x={margin.left - 10} y={y + 4} textAnchor="end" className="axis"
                    style={{ fontSize: 11, fill: "var(--ink-muted)" }}>
                {day.slice(5)}
              </text>
              <line x1={margin.left} x2={margin.left + inner} y1={y} y2={y}
                    stroke="var(--rule)" />
              {entries.filter((e) => e.date === day).map((e) => (
                <g key={`${e.date}-${e.time}`}
                   onMouseEnter={(ev) => show(ev, (
                     <>
                       <div className="k mono">{e.date} {e.time} · {e.kind}</div>
                       <strong>{e.title}</strong>
                     </>
                   ))}
                   onMouseLeave={hide}>
                  <rect x={x(minutes(e)) - 9} y={y - 14} width={18} height={28} fill="transparent"
                        style={{ cursor: "pointer" }}
                        onClick={() => setPicked(picked === e ? null : e)} />
                  <line x1={x(minutes(e))} x2={x(minutes(e))} y1={y - 9} y2={y + 9}
                        stroke={KIND_COLOUR[e.kind] ?? "var(--ink)"} strokeWidth={2.4}
                        strokeLinecap="round" />
                </g>
              ))}
            </g>
          );
        })}
      </svg>
      {tip}
      <div className="controls" aria-label="Kinds of entry">
        {kinds.map((k) => (
          <span key={k.id} className="chip" style={{ cursor: "default" }}>
            <svg width="10" height="12" aria-hidden="true">
              <line x1="5" y1="1" x2="5" y2="11" stroke={KIND_COLOUR[k.id]} strokeWidth="2.4"
                    strokeLinecap="round" />
            </svg>
            {k.id} — {k.label}
          </span>
        ))}
      </div>
      {picked && (
        <div className="card" style={{ maxWidth: "42rem", cursor: "default" }}>
          <div className="hid">{picked.date} {picked.time} · {picked.kind}</div>
          <div className="claim">{picked.title}</div>
          <p style={{ fontSize: "0.86rem", marginBottom: 0 }}>{picked.lead}</p>
        </div>
      )}
    </div>
  );
}
