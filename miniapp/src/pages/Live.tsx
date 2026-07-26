import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Captions,
  Mic,
  MicOff,
  PhoneOff,
  Video,
} from "lucide-react";
import { backButton, mainButton } from "@tma.js/sdk-react";
import { chatWithBrain, createSessionToken, fetchPersona } from "@/api/client";
import { AnamEvent, createAnamClient, type LiveClient } from "@/lib/anam";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Props = {
  onClose: () => void;
};

type Phase = "idle" | "connecting" | "live" | "error";

function formatTimer(sec: number): string {
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export function Live({ onClose }: Props) {
  const clientRef = useRef<LiveClient | null>(null);
  const busyRef = useRef(false);
  const startingRef = useRef(false);
  const userBuf = useRef("");
  const showCaptionsRef = useRef(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState("Нажми Start, чтобы набрать Adeline Kalen");
  const [caption, setCaption] = useState("");
  const [showCaptions, setShowCaptions] = useState(true);
  const [micMuted, setMicMuted] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    showCaptionsRef.current = showCaptions;
  }, [showCaptions]);

  useEffect(() => {
    fetchPersona()
      .then((p) => setPreviewUrl(p.imageUrl || ""))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (mainButton.setParams.isAvailable()) {
      mainButton.setParams({ isVisible: false });
    }
    if (backButton.show.isAvailable()) backButton.show();
    const off = backButton.onClick(() => {
      void stopSession().then(onClose);
    });
    return () => {
      off();
      if (backButton.hide.isAvailable()) backButton.hide();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (phase !== "live") return;
    const id = window.setInterval(() => setSeconds((v) => v + 1), 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  const stopSession = useCallback(async () => {
    startingRef.current = false;
    const client = clientRef.current;
    clientRef.current = null;
    if (client) {
      try {
        await client.stopStreaming();
      } catch {
        /* ignore */
      }
    }
    const video = videoRef.current;
    if (video) {
      video.srcObject = null;
      video.muted = true;
    }
    setPhase("idle");
    setSeconds(0);
    setCaption("");
    setMicMuted(false);
    setStatus("Нажми Start, чтобы набрать Adeline Kalen");
  }, []);

  async function handleUserSpeech(text: string) {
    if (busyRef.current || !clientRef.current) return;
    busyRef.current = true;
    setStatus("Думаю…");
    try {
      const { reply } = await chatWithBrain(text);
      if (showCaptionsRef.current) setCaption(reply);
      await clientRef.current.talk(reply);
      setStatus("На линии · говори с Adeline");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStatus(`Ошибка: ${msg}`);
    } finally {
      busyRef.current = false;
    }
  }

  async function startSession() {
    if (startingRef.current || clientRef.current) return;
    startingRef.current = true;
    setError("");
    setPhase("connecting");
    setStatus("Создаю session token…");
    setSeconds(0);

    try {
      const { sessionToken } = await createSessionToken();
      if (!sessionToken) throw new Error("empty session token");

      setStatus("Разреши микрофон и подключаю Anam…");
      const client = createAnamClient(sessionToken);
      clientRef.current = client;

      client.addListener(AnamEvent.SESSION_READY, () => {
        setStatus("Сессия готова, жду видео…");
      });
      client.addListener(AnamEvent.MIC_PERMISSION_PENDING, () => {
        setStatus("Нужен доступ к микрофону…");
      });
      client.addListener(AnamEvent.MIC_PERMISSION_DENIED, (err) => {
        setError(`Микрофон запрещён: ${err}`);
        setPhase("error");
        setStatus("Нет доступа к микрофону");
      });
      client.addListener(AnamEvent.VIDEO_STREAM_STARTED, () => {
        setStatus("Видео-поток получен…");
        const video = videoRef.current;
        if (video) {
          video.muted = true;
          void video.play().catch(() => undefined);
        }
      });
      client.addListener(AnamEvent.VIDEO_PLAY_STARTED, () => {
        const video = videoRef.current;
        if (video) {
          // Autoplay often needs muted start; unmute output after play.
          video.muted = false;
        }
        setPhase("live");
        setStatus("На линии · говори с Adeline");
      });
      client.addListener(AnamEvent.CONNECTION_CLOSED, (reason, details) => {
        setError(`Соединение закрыто: ${reason}${details ? ` · ${details}` : ""}`);
        setPhase("error");
        setStatus("Стрим остановлен");
        clientRef.current = null;
      });
      client.addListener(AnamEvent.MESSAGE_STREAM_EVENT_RECEIVED, (event) => {
        const role = (event.role || "").toLowerCase();
        const chunk = event.content || "";

        if (role === "persona" || role === "assistant") {
          if (showCaptionsRef.current) {
            setCaption((prev) =>
              event.endOfSpeech ? chunk || prev : `${prev}${chunk}`.slice(-280),
            );
          }
          return;
        }

        if (role === "user") {
          userBuf.current += chunk;
          if (event.endOfSpeech) {
            const text = userBuf.current.trim();
            userBuf.current = "";
            if (text) void handleUserSpeech(text);
          }
        }
      });

      const video = videoRef.current;
      if (video) {
        video.muted = true;
        video.setAttribute("playsinline", "true");
      }

      await client.streamToVideoElement("persona-video");
      // Fallback if VIDEO_PLAY_STARTED is delayed/missed in WebView
      window.setTimeout(() => {
        if (clientRef.current && startingRef.current) {
          const v = videoRef.current;
          if (v?.srcObject) {
            void v.play().then(() => {
              v.muted = false;
              setPhase((p) => (p === "connecting" ? "live" : p));
              setStatus((s) =>
                s.includes("Думаю") ? s : "На линии · говори с Adeline",
              );
            });
          }
        }
      }, 2500);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setPhase("error");
      setStatus(`Ошибка: ${msg}`);
      clientRef.current = null;
    } finally {
      startingRef.current = false;
    }
  }

  function toggleMic() {
    const client = clientRef.current;
    if (!client) return;
    if (micMuted) {
      client.unmuteInputAudio();
      setMicMuted(false);
    } else {
      client.muteInputAudio();
      setMicMuted(true);
    }
  }

  async function endCall() {
    await stopSession();
    onClose();
  }

  const isLive = phase === "live";
  const showPreview = phase === "idle" || phase === "error" || phase === "connecting";

  return (
    <div className="relative flex min-h-(--tg-viewport-stable-height,100vh) flex-col bg-background">
      <video
        id="persona-video"
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`absolute inset-0 h-full w-full object-cover bg-black ${
          isLive ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />

      {showPreview ? (
        <div className="absolute inset-0">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Adeline Kalen"
              className="h-full w-full object-cover opacity-80 grayscale"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-secondary text-4xl font-semibold text-muted-foreground">
              AK
            </div>
          )}
          <div className="absolute inset-0 bg-linear-to-t from-background via-background/40 to-transparent" />
        </div>
      ) : null}

      <div className="relative z-10 flex items-start justify-between p-4">
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            variant="secondary"
            size="icon"
            className="h-10 w-10"
            onClick={() => void endCall()}
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          {isLive ? (
            <Badge variant="outline" className="w-fit gap-1.5 border-neutral-600 text-white">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
              На линии · {formatTimer(seconds)}
            </Badge>
          ) : (
            <Badge variant="outline" className="w-fit gap-1.5 border-neutral-600 text-neutral-300">
              <Video className="h-3 w-3" />
              Готова к звонку
            </Badge>
          )}
        </div>
      </div>

      <div className="relative z-10 mt-auto space-y-3 p-4 pb-[calc(16px+env(safe-area-inset-bottom))]">
        {showCaptions && caption ? (
          <div className="rounded-xl border border-border bg-black/55 px-3 py-2 text-sm backdrop-blur">
            {caption}
          </div>
        ) : null}

        <p className="text-center text-sm text-muted-foreground">{status}</p>
        {error ? (
          <p className="text-center text-sm text-destructive">{error}</p>
        ) : null}

        {phase === "idle" || phase === "error" ? (
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => void startSession()}
          >
            <Video className="h-5 w-5" />
            Набрать Adeline Kalen
          </Button>
        ) : (
          <div className="flex items-center justify-center gap-4">
            <Button
              type="button"
              variant={micMuted ? "destructive" : "secondary"}
              size="icon"
              onClick={toggleMic}
              disabled={!isLive}
              aria-label="Mute mic"
            >
              {micMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="icon"
              className="h-16 w-16"
              onClick={() => void endCall()}
              aria-label="End call"
            >
              <PhoneOff className="h-6 w-6" />
            </Button>
            <Button
              type="button"
              variant={showCaptions ? "default" : "secondary"}
              size="icon"
              onClick={() => setShowCaptions((v) => !v)}
              aria-label="Captions"
            >
              <Captions className="h-5 w-5" />
            </Button>
          </div>
        )}

        {phase === "connecting" ? (
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => void stopSession()}
          >
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  );
}
