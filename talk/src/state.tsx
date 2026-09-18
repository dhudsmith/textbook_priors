import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { DatasetMeta, Study } from "./types";
import { useDark } from "./hooks";

/* Shared state: the loaded snapshot, the dataset the audience picked (remembered across every
   section, so whoever chose dermamnist at the top sees dermamnist all the way down), and
   and the section on screen. The page has one form: the talk. */

export const SECTIONS = [
  { id: "top", short: "Title" },
  { id: "question", short: "Images and features" },
  { id: "design", short: "Classification arms" },
  { id: "models", short: "Models tested" },
  { id: "workflow", short: "How it is structured" },
  { id: "machine", short: "The workflow" },
  { id: "results", short: "Results" },
  { id: "size", short: "Model size and price" },
  { id: "thinking", short: "Thinking" },
  { id: "verdicts", short: "Verdicts" },
  { id: "premise", short: "How it unfolded" },
  { id: "takeaways", short: "Takeaways" },
  { id: "explore", short: "Extra" },
] as const;

interface Ctx {
  study: Study;
  dataset: string;
  setDataset: (d: string) => void;
  meta: DatasetMeta;
  metaOf: (name: string) => DatasetMeta;
  active: string;
  setActive: (id: string) => void;
  dark: boolean;
  /** A dataset's colour for the current theme; identity never depends on colour alone. */
  hue: (name: string) => string;
  /** An arm's colour for the current theme. */
  armHue: (id: string) => string;
  armDash: (id: string) => string | undefined;
}

const TalkContext = createContext<Ctx | null>(null);

export function useTalk(): Ctx {
  const ctx = useContext(TalkContext);
  if (!ctx) throw new Error("useTalk outside the provider");
  return ctx;
}

export function TalkProvider({ study, children }: { study: Study; children: ReactNode }) {
  const [dataset, setDataset] = useState("pneumoniamnist");
  const [active, setActive] = useState<string>("top");
  const dark = useDark();

  const byName = useMemo(
    () => new Map(study.datasets.map((d) => [d.name, d])), [study.datasets]);
  const metaOf = useCallback(
    (name: string) => byName.get(name) ?? study.datasets[0], [byName, study.datasets]);
  const hue = useCallback(
    (name: string) => (dark ? metaOf(name).colour_dark : metaOf(name).colour), [dark, metaOf]);
  const arms = useMemo(
    () => new Map(study.style.arms.map((a) => [a.id, a])), [study.style.arms]);
  const armHue = useCallback((id: string) => {
    const arm = id === "lit" ? study.style.literature : arms.get(id);
    return arm ? (dark ? arm.dark : arm.colour) : "var(--ink-muted)";
  }, [arms, dark, study.style.literature]);
  const armDash = useCallback((id: string) => {
    const arm = id === "lit" ? study.style.literature : arms.get(id);
    return arm?.dash ?? undefined;
  }, [arms, study.style.literature]);

  /* The page has two gears. A presentation clicker sends PageDown, PageUp, Space or the arrow
     keys, and every one of those is left to the browser, so one press scrolls one screen - the
     beat. Section jumps wear keys no remote sends: `]` and `[`, or shift with an arrow. Space is
     never intercepted, so it still activates whatever has focus. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const ids: string[] = SECTIONS.map((s) => s.id);
      const here = Math.max(0, ids.indexOf(active));
      const go = (i: number) => {
        const id = ids[Math.min(ids.length - 1, Math.max(0, i))];
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
        history.replaceState(null, "", `#${id}`);
      };
      if (e.key === "]" || (e.shiftKey && e.key === "ArrowDown")) {
        go(here + 1); e.preventDefault();
      } else if (e.key === "[" || (e.shiftKey && e.key === "ArrowUp")) {
        go(here - 1); e.preventDefault();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  /* The URL names the section on screen however the reader got there, not only by keyboard, so a
     speaker who wheels to a section can read its address aloud.
     The first seconds are left alone, because the page is still re-jumping to the hash it arrived
     with while its images and data land. */
  const [tracking, setTracking] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setTracking(true), 2000);
    return () => window.clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!tracking) return;
    if (window.location.hash.slice(1) !== active) {
      history.replaceState(null, "", `#${active}`);
    }
  }, [active, tracking]);

  const value: Ctx = {
    study, dataset, setDataset, meta: metaOf(dataset), metaOf,
    active, setActive, dark, hue, armHue, armDash,
  };
  return <TalkContext.Provider value={value}>{children}</TalkContext.Provider>;
}
