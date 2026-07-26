import { useState } from "react";
import { Chat } from "@/pages/Chat";
import { Home } from "@/pages/Home";
import { Live } from "@/pages/Live";

type Screen = "home" | "live" | "chat";

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");

  if (screen === "live") {
    return <Live onClose={() => setScreen("home")} />;
  }

  if (screen === "chat") {
    return <Chat onClose={() => setScreen("home")} />;
  }

  return (
    <Home
      onLive={() => setScreen("live")}
      onChat={() => setScreen("chat")}
      onVoiceHint={() => undefined}
    />
  );
}
