import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App";
// The app's own fonts.
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
// Blattform's fonts; the browser fetches them only under that theme.
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/instrument-sans";
// The sheet's fonts; Andika's files lie in public/fonts and are declared in styles/fonts.css.
import "@fontsource-variable/playwrite-de-grund";
import "@fontsource-variable/playwrite-de-va";
import "@fontsource-variable/playwrite-de-sas";
import "@fontsource-variable/playwrite-de-la";
import "./styles/fonts.css";
import "./styles/theme.css";
import "./styles/chrome.css";
import "./styles/forms.css";
import "./styles/paper.css";
import "./styles/editor.css";
import "./styles/sheet.css";
import "./styles/school.css";
import "./styles/tables.css";
import "./styles/text.css";
import "./styles/panel.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
