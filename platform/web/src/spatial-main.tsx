import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter/index.css";
import "@fontsource/jetbrains-mono/index.css";
import "./index.css";
import "./spatial/spatial.css";
import SpatialApp from "./spatial/SpatialApp";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SpatialApp />
  </StrictMode>,
);
