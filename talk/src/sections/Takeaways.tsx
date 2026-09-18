import { Band, Bullets, Callouts, Header } from "../components/ui";
import { PageQR } from "./Title";
import { takeaways as copy, LINKS } from "../content";
import { asset } from "../data";

/* The end of the talk, and the section the speaker speaks from: his own takeaways as bullets,
   the three the agent proposed kept separate under their own heading, and the understanding-debt
   note, which arrived here when "what four days cost" was cut. The links and the QR code close
   the page, as they did at the end of the cut section. */

export function Takeaways() {
  return (
    <Band id="takeaways">
      <Header id="takeaways" eyebrow="11">{copy.header}</Header>
      <Bullets items={copy.bullets} />

      <Callouts items={copy.callouts} />

      <h3>{copy.added.header}</h3>
      <Bullets items={copy.added.bullets} />

      <div style={{ marginTop: "2rem" }}>
        <div>
          <h3>Links</h3>
          <ul style={{ fontSize: "0.9rem" }}>
            {LINKS.map((l) => (
              <li key={l.href}><a href={l.href}>{l.label}</a></li>
            ))}
            <li><a href={asset("report.pdf")}>the technical report, as a PDF</a></li>
          </ul>
        </div>
        <div className="qrblock"><PageQR caption="Take the page with you" /></div>
      </div>
    </Band>
  );
}
