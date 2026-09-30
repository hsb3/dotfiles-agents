import { createRoot } from "react-dom/client";
import "@carbon/charts/styles.css";
import "./styles.scss";
import { BrowserApp } from "./views";

createRoot(document.getElementById("root")!).render(<BrowserApp />);
