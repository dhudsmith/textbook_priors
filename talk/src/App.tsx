import { Suspense, lazy, useEffect, useLayoutEffect } from "react";
import { TalkProvider } from "./state";
import { STATIC, loadStudy } from "./data";
import { useAsync, useInView } from "./hooks";
import { Band, Header, Rail } from "./components/ui";
import { Title } from "./sections/Title";
import { Workflow } from "./sections/Workflow";
import { Premise } from "./sections/Premise";
import { Question } from "./sections/Question";
import { Design } from "./sections/Design";
import { Models } from "./sections/Models";
import { Machine } from "./sections/Machine";
import { Sample } from "./sections/Sample";
import { Results } from "./sections/Results";
import { Thinking } from "./sections/Thinking";
import { Verdicts } from "./sections/Verdicts";
import { ModelSize } from "./sections/ModelSize";
import { Takeaways } from "./sections/Takeaways";
import { title, explore } from "./content";

/* The explorer is the one heavy part of the page and nobody sees it during the talk, so it is a
   separate chunk that loads when it first scrolls into view. */
const Explore = lazy(() => import("./sections/Explore"));

function ExploreBand() {
  const { ref, seen } = useInView<HTMLDivElement>("400px");
  return (
    <Band id="explore">
      <Header id="explore">{explore.header}</Header>
      <div ref={ref} className="explore-slot">
        {seen && (
          <Suspense fallback={<p className="note">Loading the explorer…</p>}>
            <Explore />
          </Suspense>
        )}
      </div>
    </Band>
  );
}

function Page() {
  // The QR audience can be sent straight to the section on screen, but the sections above it grow
  // as their data and images arrive, so the browser's own jump lands short. Re-jump once.
  const jump = () => {
    const id = window.location.hash.slice(1);
    if (id) document.getElementById(id)?.scrollIntoView({ block: "start" });
  };
  // Static mode has the whole page in hand at mount, so the jump is part of the first paint and a
  // screenshot of `#h4` is of h4.
  useLayoutEffect(() => { if (STATIC) jump(); });
  useEffect(() => {
    if (!window.location.hash) return;
    const t = window.setTimeout(jump, 400);
    const t2 = window.setTimeout(jump, 1600);
    return () => { window.clearTimeout(t); window.clearTimeout(t2); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="shell">
      <Rail />
      <main className="main" id="main">
        <Title />
        <Question />
        <Design />
        <Models />
        <Workflow />
        <Machine />
        <Sample />
        <Results />
        <ModelSize />
        <Thinking />
        <Verdicts />
        <Premise />
        <Takeaways />
        <ExploreBand />
      </main>
    </div>
  );
}

export default function App() {
  const { data: study, error } = useAsync(loadStudy);
  if (error) {
    return (
      <main className="main" style={{ padding: "3rem" }}>
        <h1>{title.header}</h1>
        <p>The data snapshot could not be loaded: {error}</p>
        <p className="note">
          The page reads <code>data/study.json</code>, written by the <code>talk_data</code> rule.
        </p>
      </main>
    );
  }
  if (!study) {
    return (
      <main className="main" style={{ padding: "3rem" }}>
        <p className="note">Loading the run…</p>
      </main>
    );
  }
  return (
    <TalkProvider study={study}>
      <a className="skip" href="#main">Skip to the talk</a>
      <Page />
    </TalkProvider>
  );
}
