import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Band, Bullets, Header } from "../components/ui";
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
      <Bullets items={copy.intro.bullets} />
    </Band>
  );
}
