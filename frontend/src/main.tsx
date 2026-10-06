import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App";
// The app's own fonts.
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
// The sheet's fonts; Andika's files lie in public/fonts and are declared in styles.css.
import "@fontsource-variable/playwrite-de-grund";
import "@fontsource-variable/playwrite-de-va";
import "@fontsource-variable/playwrite-de-sas";
import "@fontsource-variable/playwrite-de-la";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
