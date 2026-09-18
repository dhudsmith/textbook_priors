import { Band, Header } from "../components/ui";
import { ArchiveCall } from "../components/ArchiveCall";
import { sample as copy } from "../content";
import { useAsync, useInView } from "../hooks";
import { loadArchive } from "../data";

/* The hinge between how the project runs and what it found. Everything after this section is a
   number computed from answers of this shape, so the room sees one of them first: the picture the
   model was given, the two questions it was asked, and the two replies the archive holds.

   It sat at the foot of the workflow section, where it was the last thing under a heading about
   rules and nobody could tell what it was for. The heading stands alone here: the widget is what
   the section says, and a paragraph describing it first was in the way. */

export function Sample() {
  const { ref, seen } = useInView<HTMLDivElement>();
  const { data: archive, error } = useAsync(
    () => (seen ? loadArchive() : new Promise<never>(() => {})), [seen]);

  return (
    <Band id="sample">
      <Header id="sample">{copy.header}</Header>

      <div ref={ref}>
        {error && <p className="note">Could not load the archive sample: {error}</p>}
        {archive ? <ArchiveCall sample={archive} />
                 : <p className="note">Loading the archived answers…</p>}
      </div>
    </Band>
  );
}
