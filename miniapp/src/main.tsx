import { createRoot } from "react-dom/client";
import App from "./App";
import { initTelegram } from "./init";
import "./index.css";

try {
  initTelegram();
} catch (e) {
  console.warn("Telegram SDK init skipped/failed (browser preview?)", e);
}

// No StrictMode: double-mount breaks Anam WebRTC sessions.
createRoot(document.getElementById("root")!).render(<App />);
