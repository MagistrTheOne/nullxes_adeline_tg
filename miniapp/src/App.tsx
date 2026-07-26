import { useCallback, useState } from "react";
import { Chat } from "@/pages/Chat";
import { Home } from "@/pages/Home";
import { Live } from "@/pages/Live";

type Screen = "home" | "live" | "chat";

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const goHome = useCallback(() => setScreen("home"), []);
  const goLive = useCallback(() => setScreen("live"), []);
  const goChat = useCallback(() => setScreen("chat"), []);

  if (screen === "live") {
    return <Live onClose={goHome} />;
  }

  if (screen === "chat") {
    return <Chat onClose={goHome} />;
  }

  return (
    <Home onLive={goLive} onChat={goChat} onVoiceHint={() => undefined} />
  );
}
