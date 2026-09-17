import { useCallback, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import type { ScaleLinear } from "d3-scale";

/* The pieces every chart on this page is built from. D3 supplies the scales and the shapes; the
   marks are drawn by React, so hover, toggles and the keyboard path are ours. Grid and axes are
   solid hairlines one shade off the surface; marks are thin; a legend is always present for two
   or more series and the ones that fit are direct-labelled as well. */

export const MARGIN = { top: 16, right: 92, bottom: 38, left: 52 };

export const fmt3 = (v: number) => v.toFixed(3);
export const fmt2 = (v: number) => v.toFixed(2);
export const signed = (v: number, digits = 3) =>
  `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(digits)}`;
export const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
export const short = (d: string) => d.replace("mnist", "");

/** A model or reader as an axis tick: a stem plus its reasoning effort. The full identifiers are
    thirteen to twenty-two characters and nine of them will not fit under one axis at any tilt, so
    the axis wears the stem and the chart's text summary carries the exact names - which is where
    a reader who needs to reproduce a number will look anyway. */
const EFFORT = /-(minimal|low|medium|high)$/;
export function readerTick(id: string): string {
  const m = id.match(EFFORT);
  const base = m ? id.slice(0, m.index) : id;
  const closed = base.match(/^gpt-[\d.]+-([a-z]+)$/);
  let stem: string;
  if (closed) {
    stem = closed[1];
  } else {
    const family = base.match(/^([a-z]+)/);
    const size = base.match(/(\d+)b/i);
    stem = size && family ? `${family[1]} ${size[1]}b` : base;
  }
  return m ? `${stem} · ${m[1]}` : stem;
}

/** One SVG marker per dataset, so no two datasets share both a colour and a marker. */
export function Marker({ kind, x, y, r = 4, fill, stroke }: {
  kind: string; x: number; y: number; r?: number; fill: string; stroke?: string;
}) {
  const common = { fill, stroke: stroke ?? "var(--surface)", strokeWidth: stroke ? 2 : 0 };
  switch (kind) {
    case "square":
      return <rect x={x - r} y={y - r} width={2 * r} height={2 * r} rx={1} {...common} />;
    case "triangle":
      return <polygon points={`${x},${y - r * 1.2} ${x + r * 1.1},${y + r} ${x - r * 1.1},${y + r}`}
                      {...common} />;
    case "triangle-down":
      return <polygon points={`${x},${y + r * 1.2} ${x + r * 1.1},${y - r} ${x - r * 1.1},${y - r}`}
                      {...common} />;
    case "diamond":
      return <polygon points={`${x},${y - r * 1.3} ${x + r * 1.1},${y} ${x},${y + r * 1.3} ${x - r * 1.1},${y}`}
                      {...common} />;
    case "plus":
      return <path d={`M${x - r} ${y} H${x + r} M${x} ${y - r} V${y + r}`} stroke={fill}
                   strokeWidth={2.4} fill="none" strokeLinecap="round" />;
    default:
      return <circle cx={x} cy={y} r={r} {...common} />;
  }
}

export function AxisBottom({ scale, y, ticks, label, format = String }: {
  scale: (v: number) => number | undefined;
  y: number; ticks: number[]; label?: string; format?: (v: number) => string;
}) {
  const at = (v: number) => scale(v) ?? 0;
  return (
    <g className="axis" transform={`translate(0 ${y})`}>
      <line x1={at(ticks[0])} x2={at(ticks[ticks.length - 1])} y1={0} y2={0} />
      {ticks.map((t) => (
        <g key={t} transform={`translate(${at(t)} 0)`}>
          <line y2={5} />
          <text y={18} textAnchor="middle">{format(t)}</text>
        </g>
      ))}
      {label && (
        <text x={at(ticks[ticks.length - 1])} y={34} textAnchor="end"
              style={{ fontWeight: 600 }}>{label}</text>
      )}
    </g>
  );
}

export function AxisLeft({ scale, x, ticks, width, label, format = fmt2 }: {
  scale: ScaleLinear<number, number>; x: number; ticks: number[]; width: number;
  label?: string; format?: (v: number) => string;
}) {
  return (
    <g>
      <g className="grid">
        {ticks.map((t) => (
          <line key={t} x1={x} x2={x + width} y1={scale(t)} y2={scale(t)} />
        ))}
      </g>
      <g className="axis">
        {ticks.map((t) => (
          <text key={t} x={x - 8} y={scale(t) + 4} textAnchor="end">{format(t)}</text>
        ))}
        {label && (
          <text transform={`translate(${x - 40} ${scale(ticks[ticks.length - 1])}) rotate(-90)`}
                textAnchor="end" style={{ fontWeight: 600 }}>{label}</text>
        )}
      </g>
    </g>
  );
}

/** A zero rule for difference charts: dotted, grey, never dashed like a series. */
export function ZeroLine({ x, y1, y2 }: { x: number; y1: number; y2: number }) {
  return <line x1={x} x2={x} y1={y1} y2={y2} stroke="var(--ink-muted)" strokeWidth={1}
               strokeDasharray="1 3" />;
}

export interface Hover { x: number; y: number; node: ReactNode }

/** One tooltip implementation for the whole page. Hit areas are always bigger than the mark. */
export function useHover() {
  const [hover, setHover] = useState<Hover | null>(null);
  const show = useCallback((e: { clientX: number; clientY: number }, node: ReactNode) => {
    setHover({ x: e.clientX, y: e.clientY, node });
  }, []);
  const hide = useCallback(() => setHover(null), []);
  const tip = hover && typeof document !== "undefined"
    ? createPortal(
        <div className="tooltip" role="status"
             style={{
               left: Math.min(hover.x + 14, window.innerWidth - 320),
               top: Math.min(hover.y + 14, window.innerHeight - 160),
             }}>
          {hover.node}
        </div>, document.body)
    : null;
  return { show, hide, tip };
}

/** Push direct labels apart until none sits on another, keeping their order and staying inside
    the plot. Label collisions are the one layout fault a chart cannot be forgiven, and a series
    whose value coincides with another's - arm B and arm C on pneumoniamnist - always causes one. */
export function spreadLabels<T extends { y: number }>(
  items: T[], gap = 13, top = -Infinity, bottom = Infinity,
): T[] {
  const out = items.map((it) => ({ ...it })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < out.length; i++) {
    if (out[i].y - out[i - 1].y < gap) out[i].y = out[i - 1].y + gap;
  }
  const over = out.length ? out[out.length - 1].y - bottom : 0;
  if (over > 0) for (const it of out) it.y = Math.max(top, it.y - over);
  return out;
}

/** A legend is always present for two or more series (talk's accessibility pass). */
export function Legend({ items, onToggle, hidden }: {
  items: { id: string; label: string; colour: string; dash?: string }[];
  onToggle?: (id: string) => void;
  hidden?: Set<string>;
}) {
  return (
    <div className="controls" role="group" aria-label="Series">
      {items.map((s) => {
        const off = hidden?.has(s.id) ?? false;
        const inner = (
          <>
            <svg width="18" height="10" aria-hidden="true">
              <line x1="0" y1="5" x2="18" y2="5" stroke={s.colour} strokeWidth="2.4"
                    strokeDasharray={s.dash} />
              {off && <line x1="1" y1="9" x2="17" y2="1" stroke="var(--ink-muted)"
                            strokeWidth="1.4" />}
            </svg>
            {s.label}
          </>
        );
        /* A legend chip is not a picker. The picker's pressed state inverts the chip, and a
           series colour drawn on the opposite-polarity ground fails contrast - every swatch did,
           in dark. An active series wears the ordinary chip; a hidden one wears `.off` with its
           swatch struck through, and every legend on the page then looks the same. */
        return onToggle ? (
          <button key={s.id} className={`chip legend${off ? " off" : ""}`} aria-pressed={!off}
                  onClick={() => onToggle(s.id)}>{inner}</button>
        ) : (
          <span key={s.id} className="chip legend" style={{ cursor: "default" }}>{inner}</span>
        );
      })}
    </div>
  );
}
