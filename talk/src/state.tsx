import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { DatasetMeta, Study } from "./types";
import { useDark } from "./hooks";

/* Shared state: the loaded snapshot, the dataset the audience picked (remembered across every
   section, so whoever chose dermamnist at the top sees dermamnist all the way down), and
   presenter mode, which hides the deep panels and the callout bodies so the projected page is
   clean while the QR audience on their own phones still sees everything. */

export const SECTIONS = [
  { id: "top", label: "Textbook priors", short: "Title" },
  { id: "premise", label: "This talk was built the way it is about", short: "Premise" },
  { id: "question", label: "The question", short: "The question" },
  { id: "design", label: "Five arms, seven hypotheses", short: "The design" },
  { id: "machine", label: "The machine", short: "The machine" },
  { id: "h1", label: "H1 — Is the textbook worth labelled images?", short: "H1 substitution" },
  { id: "h2", label: "H2 — The bank, or just the model?", short: "H2 the bank" },
  { id: "h3", label: "H3 and H7 — Does a bigger model read better?", short: "H3 / H7 scale" },
  { id: "h4", label: "H4 and H6 — What if the model thinks?", short: "H4 / H6 thinking" },
  { id: "h5", label: "H5 — Does the textbook add anything?", short: "H5 complement" },
  { id: "verdicts", label: "Seven verdicts", short: "Verdicts" },
  { id: "close", label: "What the four days cost", short: "The close" },
  { id: "explore", label: "Explore", short: "Explore" },
] as const;

interface Ctx {
  study: Study;
  dataset: string;
  setDataset: (d: string) => void;
  meta: DatasetMeta;
  metaOf: (name: string) => DatasetMeta;
  presenter: boolean;
  setPresenter: (v: boolean) => void;
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
  const [presenter, setPresenter] = useState(false);
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

  useEffect(() => {
    document.body.classList.toggle("presenter", presenter);
  }, [presenter]);

  // Keyboard: `p` toggles presenter mode, arrows and space move one section.
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
      if (e.key === "p" || e.key === "P") { setPresenter((v) => !v); e.preventDefault(); }
      else if (e.key === "ArrowDown" || e.key === "ArrowRight" || e.key === "PageDown"
               || (e.key === " " && !e.shiftKey)) { go(here + 1); e.preventDefault(); }
      else if (e.key === "ArrowUp" || e.key === "ArrowLeft" || e.key === "PageUp"
               || (e.key === " " && e.shiftKey)) { go(here - 1); e.preventDefault(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  const value: Ctx = {
    study, dataset, setDataset, meta: metaOf(dataset), metaOf,
    presenter, setPresenter, active, setActive, dark, hue, armHue, armDash,
  };
  return <TalkContext.Provider value={value}>{children}</TalkContext.Provider>;
}
