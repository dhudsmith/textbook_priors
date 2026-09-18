import { Band, Header } from "../components/ui";
import { WorkflowDiagram } from "../components/diagrams";
import { title as copy } from "../content";

/* The machinery, shown after the science it serves: the question and the hypotheses come first,
   and only then how the thing that answered them is wired. */
export function Workflow() {
  return (
    <Band id="workflow">
      <Header id="workflow" eyebrow="3">{copy.workflow.header}</Header>
      <p className="lede">{copy.workflow.lede}</p>
      <WorkflowDiagram />
    </Band>
  );
}
