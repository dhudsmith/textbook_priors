import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { useTalk } from "../state";
import { Band, Body, CountTile, Header, Tile } from "../components/ui";
import { WorkflowDiagram } from "../components/diagrams";
import { title as copy } from "../content";

/* The QR code is rendered client-side from the page's own URL, so it is right wherever the site
   is deployed and needs no image file. */
function PageQR({ caption, size = 196 }: { caption: string; size?: number }) {
  const [href, setHref] = useState("");
  useEffect(() => setHref(window.location.href.split("#")[0].split("?")[0]), []);
  if (!href) return null;
  return (
    <div className="qr">
      <QRCodeSVG value={href} size={size} level="M" marginSize={0} bgColor="#ffffff"
                 fgColor="#17171a" title={`QR code for ${href}`} />
      <div className="cap">{caption}</div>
    </div>
  );
}

export { PageQR };

export function Title() {
  const { study } = useTalk();
  const led = study.ledger;

  return (
    <Band id="top">
      <div className="title-band title-grid">
        <div>
          <Header id="top" eyebrow="Clemson HPC Day">{copy.header}</Header>
          <p className="byline">
            <span className="who">{copy.byline.who}</span>
            <span className="where">{copy.byline.where}</span>
          </p>
          <p className="lede">{copy.standfirst}</p>
        </div>
        <PageQR caption={copy.qr} />
      </div>
      <p>{copy.intro.lede}</p>
      <p className="pullquote">{copy.intro.question}</p>
      <Body paras={[copy.intro.body]} bullets={copy.intro.bullets} />
      <div className="tiles">
        <Tile value={led.work_dates.length}
              unit="days of work, from the plan to the report" />
        <CountTile value={led.calls} unit="raw model responses, archived and write-protected" />
        <Tile value={led.datasets} unit="MedMNIST 2D benchmarks, every one in the release" />
        <CountTile value={led.tests ?? 0} unit="tests that run before anything else is computed" />
      </div>
      <p className="note">
        Every number on this page comes from the run's own files, exported once by{" "}
        <code>talk/scripts/export_talk_data.py</code> from commit{" "}
        <code>{study.provenance.run_git_commit.slice(0, 10)}</code>.
      </p>

      <h3>{copy.workflow.header}</h3>
      <p>{copy.workflow.lede}</p>
      <WorkflowDiagram />
      <p className="note">{copy.workflow.caption}</p>
    </Band>
  );
}
