import { Band, Bullets, Header } from "../components/ui";
import { title as copy } from "../content";

/* The opening. The page's QR code used to sit beside this heading; it is in the rail now, where
   it stays on screen for the whole talk instead of scrolling away after the first minute. */

export function Title() {
  return (
    <Band id="top">
      <div className="title-band">
        <Header id="top" eyebrow={copy.eyebrow}>{copy.header}</Header>
        <p className="byline">
          <span className="who">{copy.byline.who}</span>
          <span className="where">{copy.byline.where}</span>
        </p>
        <p className="lede">{copy.standfirst}</p>
      </div>
      <p>{copy.intro.lede}</p>
      <p className="pullquote">{copy.intro.question}</p>
      <Bullets items={copy.intro.bullets} />
    </Band>
  );
}
