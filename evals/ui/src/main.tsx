import { createRoot } from "react-dom/client";
import "./styles.scss";
import { BrowserApp } from "./views";

createRoot(document.getElementById("root")!).render(<BrowserApp />);
