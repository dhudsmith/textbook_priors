import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import App from "./App";
import { STATIC } from "./data";
import "./styles.css";

const root = createRoot(document.getElementById("root")!);
const tree = (
  <StrictMode>
    <App />
  </StrictMode>
);

/* Normally React decides when to paint. In static mode (`?static=1`, or reduced motion) the whole
   page has to be on screen before the document fires `load`, so that a headless screenshot or a
   print catches the finished page rather than a half-rendered one: the snapshot is already read
   synchronously in that mode, so one flush puts everything up at once. */
if (STATIC) flushSync(() => root.render(tree));
else root.render(tree);
