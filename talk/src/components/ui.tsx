import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { SECTIONS, useTalk } from "../state";
import { KIND_LABEL, type Callout as CalloutSpec } from "../content";
import { STATIC } from "../data";

/* ---- section --------------------------------------------------------------------------- */

/** One band of the scroll. Animates in on first entry and never again, and tells the rail it is
    the active section while it holds the middle of the viewport. */
export function Band({ id, className, children }: {
  id: string; className?: string; children: ReactNode;
}) {
  const { setActive } = useTalk();
  const ref = useRef<HTMLElement | null>(null);
  // `?static=1` and reduced motion skip the entry animation entirely: the band is already in.
  const [seen, setSeen] = useState(STATIC);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const enter = new IntersectionObserver(
      (es) => { if (es.some((e) => e.isIntersecting)) { setSeen(true); enter.disconnect(); } },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.02 });
    const active = new IntersectionObserver(
      (es) => { if (es.some((e) => e.isIntersecting)) setActive(id); },
      { rootMargin: "-45% 0px -45% 0px" });
    enter.observe(node);
    active.observe(node);
    return () => { enter.disconnect(); active.disconnect(); };
  }, [id, setActive]);

  return (
    <section id={id} ref={ref}
             className={`band${seen ? " seen" : ""}${className ? ` ${className}` : ""}`}
             aria-labelledby={`${id}-h`}>
      {children}
    </section>
  );
}

export function Header({ id, eyebrow, children }: {
  id: string; eyebrow?: string; children: ReactNode;
}) {
  return (
    <>
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      <h2 id={`${id}-h`}>{children}</h2>
    </>
  );
}

/** A section's prose. On the page it is paragraphs; projected, it is the section's bullets. The
    room reads the points while the speaker says the sentences, which is the opposite of the
    failure mode where a presenter reads their own paragraphs aloud. A block with no bullets
    projects its prose unchanged, so a section is never silently blanked. */
export function Body({ paras, bullets }: { paras: string[]; bullets?: readonly string[] }) {
  const { presenter } = useTalk();
  if (presenter && bullets?.length) {
    return <ul className="bullets">{bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>;
  }
  return <>{paras.map((p, i) => <p key={i}>{p}</p>)}</>;
}

/* ---- callouts -------------------------------------------------------------------------- */

/** A callout card: a left rule in its kind's colour, a small-caps label, a title that collapses
    the body, and a footer naming the file the claim can be checked against. In presenter mode
    the body and the source line are hidden by CSS and only the title is projected. */
export function Callout({ spec }: { spec: CalloutSpec }) {
  const [open, setOpen] = useState(true);
  const bodyId = useId();
  return (
    <aside className={`callout ${spec.kind}`} data-open={open}>
      <div className="label">{KIND_LABEL[spec.kind]}</div>
      <button className="title" aria-expanded={open} aria-controls={bodyId}
              onClick={() => setOpen((v) => !v)}>
        {spec.title}
      </button>
      {open && (
        <div className="body" id={bodyId}>
          {spec.body.map((p, i) => <p key={i}>{p}</p>)}
          <div className="src">{spec.source}</div>
        </div>
      )}
    </aside>
  );
}

export function Callouts({ items }: { items: CalloutSpec[] }) {
  if (!items.length) return null;
  return <div className="callouts">{items.map((c, i) => <Callout key={i} spec={c} />)}</div>;
}

/* ---- tiles ----------------------------------------------------------------------------- */

export function Tile({ value, unit }: { value: ReactNode; unit: string }) {
  return (
    <div className="tile">
      <div className="value">{value}</div>
      <div className="unit">{unit}</div>
    </div>
  );
}

/** A stat tile whose number counts up on first paint. Reduced motion and `?static=1`
    get the final value straight away. */
export function CountTile({ value, unit, format = (n: number) => n.toLocaleString("en-US") }: {
  value: number; unit: string; format?: (n: number) => string;
}) {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    if (STATIC) { setShown(value); return; }
    let frame = 0;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 900);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return <Tile value={format(shown)} unit={unit} />;
}

/* ---- dataset picker -------------------------------------------------------------------- */

/** Shared across sections 2, 5 and 12 (talk/PLAN.md section 3): whoever picks dermamnist at the
    top sees dermamnist all the way down. Each chip carries the dataset's own colour as a swatch,
    and the name as the label, so identity is never colour alone. */
export function DatasetPicker({ only }: { only?: (name: string) => boolean }) {
  const { study, dataset, setDataset, hue } = useTalk();
  return (
    <div className="controls picker" role="group" aria-label="Dataset">
      <span className="group-label">dataset</span>
      {study.datasets
        .filter((d) => !only || only(d.name))
        .map((d) => (
          <button key={d.name} className="chip" aria-pressed={d.name === dataset}
                  onClick={() => setDataset(d.name)}>
            <span className="swatch" style={{ background: hue(d.name) }} aria-hidden="true" />
            {d.name.replace("mnist", "")}
          </button>
        ))}
    </div>
  );
}

/* ---- figure frame ---------------------------------------------------------------------- */

/** Every chart on the page is wrapped in this: a caption naming the file its numbers come from,
    and a text summary for a screen reader (talk/PLAN.md section 5). */
export function ChartFrame({ caption, source, summary, children }: {
  caption: string; source: string; summary: ReactNode; children: ReactNode;
}) {
  return (
    <figure className="chart">
      <div className="chart-scroll">{children}</div>
      <figcaption>
        {caption} <span className="file presenter-hide">{source}</span>
        <details className="a11y-summary">
          <summary>Read this chart as text</summary>
          {summary}
        </details>
      </figcaption>
    </figure>
  );
}

/* ---- verdict dots ---------------------------------------------------------------------- */

/** Twelve dots, filled where the comparison won. Shape as well as fill, so the encoding survives
    colour-vision deficiency and a black-and-white print. */
export function Dots({ per, order, label }: {
  per: Record<string, boolean>; order: string[]; label: string;
}) {
  const shown = order.filter((d) => d in per);
  const won = shown.filter((d) => per[d]);
  return (
    <span className="dots" role="img"
          aria-label={`${label}: won on ${won.length} of ${shown.length} — ` +
                      `${won.join(", ") || "none"}`}>
      {shown.map((d) => (
        <svg key={d} width="13" height="13" viewBox="0 0 11 11">
          <title>{`${d}: ${per[d] ? "won" : "did not win"}`}</title>
          {per[d]
            ? <circle cx="5.5" cy="5.5" r="4.2" fill="var(--good)" />
            : <path d="M1.4 1.4 L9.6 9.6 M9.6 1.4 L1.4 9.6" stroke="var(--ink-muted)"
                    strokeWidth="1.6" fill="none" />}
        </svg>
      ))}
    </span>
  );
}

/* ---- rail ------------------------------------------------------------------------------ */

export function Rail() {
  const { active, presenter, setPresenter } = useTalk();
  // On a phone the rail is one sticky line naming the section on screen; tapping it opens the
  // list. On a desktop the media query ignores `open` and the list is simply there.
  const [open, setOpen] = useState(false);
  const here = SECTIONS.find((s) => s.id === active) ?? SECTIONS[0];
  const number = (id: string) => {
    const i = SECTIONS.findIndex((s) => s.id === id);
    return i > 0 ? String(i) : "";
  };
  return (
    <nav className={`rail${open ? " open" : ""}`} aria-label="Sections">
      <p className="railhead">Talk outline</p>
      <button className="railtoggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <span className="num">{number(here.id)}</span>
        <span>{here.short}</span>
        <span aria-hidden="true">{open ? "⌃" : "⌄"}</span>
      </button>
      <ol>
        {SECTIONS.map((s) => (
          <li key={s.id} className={s.id === "explore" ? "after" : undefined}>
            <a href={`#${s.id}`} aria-current={active === s.id} onClick={() => setOpen(false)}>
              <span className="dot" aria-hidden="true" />
              <span className="num">{number(s.id)}</span>
              <span>{s.short}</span>
            </a>
          </li>
        ))}
      </ol>
      <div className="railfoot">
        <p>
          <kbd>space</kbd> <kbd>⇟</kbd> next screen · <kbd>[</kbd> <kbd>]</kbd> section ·{" "}
          <kbd>p</kbd> presenter
        </p>
        <button className="plain" onClick={() => setPresenter(!presenter)}
                aria-pressed={presenter}>
          {presenter ? "Leave presenter mode" : "Presenter mode"}
        </button>
      </div>
    </nav>
  );
}

/* ---- misc ------------------------------------------------------------------------------ */

export function Pill({ yes, children }: { yes: boolean; children: ReactNode }) {
  return <span className={`pill ${yes ? "yes" : "no"}`}>{yes ? "✓" : "✕"} {children}</span>;
}

export function Deep({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="deep">
      <summary>{summary}</summary>
      {children}
    </details>
  );
}
