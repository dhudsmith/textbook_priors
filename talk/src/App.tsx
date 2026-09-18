import { Suspense, lazy, useEffect, useLayoutEffect } from "react";
import { TalkProvider } from "./state";
import { STATIC, loadStudy } from "./data";
import { useAsync, useInView } from "./hooks";
import { Band, Header, Rail } from "./components/ui";
import { Title } from "./sections/Title";
import { Premise } from "./sections/Premise";
import { Question } from "./sections/Question";
import { Design } from "./sections/Design";
import { Machine } from "./sections/Machine";
import { H1 } from "./sections/H1";
import { H2 } from "./sections/H2";
import { H3 } from "./sections/H3";
import { H4 } from "./sections/H4";
import { H5 } from "./sections/H5";
import { Verdicts } from "./sections/Verdicts";
import { Close } from "./sections/Close";
import { REFRAIN, explore } from "./content";

/* The explorer is the one heavy part of the page and nobody sees it during the talk, so it is a
   separate chunk that loads when it first scrolls into view. */
const Explore = lazy(() => import("./sections/Explore"));

function ExploreBand() {
  const { ref, seen } = useInView<HTMLDivElement>("400px");
  return (
    <Band id="explore" className="presenter-hide">
      <Header id="explore" eyebrow="12">{explore.header}</Header>
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
        <Premise />
        <Question />
        <Design />
        <Machine />
        <H1 />
        <H2 />
        <H3 />
        <H4 />
        {/* The refrain at the hinge of the talk: minute two, minute thirteen, minute twenty-four.
            Projected, because it is the sentence the room should leave with. */}
        <div className="refrain-band"><p className="pullquote">{REFRAIN}</p></div>
        <H5 />
        <Verdicts />
        <Close />
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
        <h1>Textbook priors over visual features</h1>
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
