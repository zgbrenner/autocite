import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { createApplicationAdapter } from "./services/createApplicationAdapter";
import "./styles.css";

const root = document.getElementById("root");
if (root === null) throw new Error("AutoCite root element was not found.");

createRoot(root).render(
  <StrictMode>
    <App adapter={createApplicationAdapter()} />
  </StrictMode>,
);
