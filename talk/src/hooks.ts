import { useEffect, useRef, useState } from "react";
import { STATIC, settledValue } from "./data";

/** Load a JSON file once and re-render when it arrives. Errors surface as text, not a blank page. */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[] = []): {
  data: T | null; error: string | null;
} {
  // In static mode the snapshot is already in hand, so the very first render carries it and a
  // screenshot never catches the loading line. Normally this starts empty and fills in an effect.
  const [state, setState] = useState<{ data: T | null; error: string | null }>(() => {
    if (!STATIC) return { data: null, error: null };
    try {
      return { data: settledValue(load()) ?? null, error: null };
    } catch {
      return { data: null, error: null };
    }
  });
  useEffect(() => {
    let live = true;
    let pending: Promise<T>;
    try {
      pending = load();
    } catch (err) {
      setState({ data: null, error: (err as Error).message });
      return;
    }
    const now = settledValue(pending);
    if (now !== undefined) { setState({ data: now, error: null }); return; }
    setState({ data: null, error: null });
    pending.then(
      (data) => live && setState({ data, error: null }),
      (err: Error) => live && setState({ data: null, error: err.message }),
    );
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

/** True once the element has been scrolled into view - used to defer the heavy panels. */
export function useInView<T extends Element>(rootMargin = "300px") {
  const ref = useRef<T | null>(null);
  // `?static=1` mounts the deferred panels immediately, so a screenshot shows the whole page.
  const [seen, setSeen] = useState(STATIC);
  useEffect(() => {
    const node = ref.current;
    if (!node || seen) return;
    if (typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { setSeen(true); io.disconnect(); }
    }, { rootMargin });
    io.observe(node);
    return () => io.disconnect();
  }, [seen, rootMargin]);
  return { ref, seen };
}

/** Measure a container's width so the SVG charts can be responsive without a resize library. */
export function useWidth<T extends HTMLElement>(fallback = 720) {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const measure = () => setWidth(Math.max(280, node.clientWidth));
    measure();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }
    const ro = new ResizeObserver(measure);
    ro.observe(node);
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}

/** The site's one media query in JS: dark mode picks the dark step of each series colour. */
export function useDark() {
  const [dark, setDark] = useState(() =>
    typeof window !== "undefined" && window.matchMedia
      ? window.matchMedia("(prefers-color-scheme: dark)").matches : false);
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = (e: MediaQueryListEvent) => setDark(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return dark;
}
