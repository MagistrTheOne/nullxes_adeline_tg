import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Captions,
  Info,
  Loader2,
  Mic,
  MicOff,
  Play,
  Square,
} from "lucide-react";
import { backButton, mainButton } from "@tma.js/sdk-react";
import { chatWithBrain, createSessionToken, fetchPersona } from "@/api/client";
import { AnamEvent, createAnamClient, type LiveClient } from "@/lib/anam";

type Props = {
  onClose: () => void;
};

type Phase = "idle" | "connecting" | "live" | "error";

const PERSONA_NAME = "Adeline Kalen";
const CONNECT_TIMEOUT_MS = 25_000;
const LIVE_FALLBACK_MS = 2_000;

function formatTimer(sec: number): string {
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function friendlyCloseReason(reason: string, details?: string): string {
  const hint =
    reason === "CONNECTION_CLOSED_CODE_MICROPHONE_PERMISSION_DENIED"
      ? "Нужен доступ к микрофону в Telegram"
      : reason === "CONNECTION_CLOSED_CODE_WEBRTC_FAILURE"
        ? "WebRTC не поднялся — проверь VPN/сеть"
        : reason === "CONNECTION_CLOSED_CODE_SIGNALLING_CLIENT_CONNECTION_FAILURE"
          ? "Не достучались до Anam"
          : reason === "CONNECTION_CLOSED_CODE_SERVER_CLOSED_CONNECTION"
            ? "Anam закрыл сессию"
            : "Стрим оборвался";
  return details ? `${hint} · ${details}` : hint;
}

function subtitleFor(phase: Phase, status: string, error: string): string {
  if (phase === "connecting") return status || "Connecting…";
  if (phase === "live") {
    if (status.includes("Думаю")) return "Thinking…";
    if (status.startsWith("Ошибка")) return status;
    return "Live session · Secure connection";
  }
  if (phase === "error") return error || status || "Session ended";
  return "Standing by · connection check";
}

export function Live({ onClose }: Props) {
  const clientRef = useRef<LiveClient | null>(null);
  const busyRef = useRef(false);
  const startingRef = useRef(false);
  const intentionalStopRef = useRef(false);
  const phaseRef = useRef<Phase>("idle");
  const userBuf = useRef("");
  const showCaptionsRef = useRef(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const timersRef = useRef<number[]>([]);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState("");
  const [caption, setCaption] = useState("");
  const [showCaptions, setShowCaptions] = useState(true);
  const [micMuted, setMicMuted] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  const setPhaseSafe = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);

  const clearTimers = useCallback(() => {
    for (const id of timersRef.current) window.clearTimeout(id);
    timersRef.current = [];
  }, []);

  const markLive = useCallback(() => {
    if (phaseRef.current !== "connecting" || !clientRef.current) return;
    const video = videoRef.current;
    if (video) {
      video.muted = false;
      void video.play().catch(() => undefined);
    }
    clearTimers();
    setPhaseSafe("live");
    setStatus("На линии");
  }, [clearTimers, setPhaseSafe]);

  useEffect(() => {
    showCaptionsRef.current = showCaptions;
  }, [showCaptions]);

  useEffect(() => {
    fetchPersona()
      .then((p) => setPreviewUrl(p.imageUrl || ""))
      .catch(() => undefined);
  }, []);

  const stopSession = useCallback(async () => {
    startingRef.current = false;
    intentionalStopRef.current = true;
    clearTimers();
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
    setError("");
    setPhaseSafe("idle");
    setSeconds(0);
    setCaption("");
    setMicMuted(false);
    setStatus("");
    intentionalStopRef.current = false;
  }, [clearTimers, setPhaseSafe]);

  useEffect(() => {
    if (mainButton.setParams.isAvailable()) {
      mainButton.setParams({ isVisible: false });
    }
    if (backButton.show.isAvailable()) backButton.show();
    const off = backButton.onClick(() => {
      void stopSession().then(() => onCloseRef.current());
    });
    return () => {
      off();
      if (backButton.hide.isAvailable()) backButton.hide();
      void stopSession();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (phase !== "live") return;
    const id = window.setInterval(() => setSeconds((v) => v + 1), 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  async function handleUserSpeech(text: string) {
    if (busyRef.current || !clientRef.current) return;
    busyRef.current = true;
    setStatus("Думаю…");
    try {
      const { reply } = await chatWithBrain(text);
      if (showCaptionsRef.current) setCaption(reply);
      if (!clientRef.current) return;
      await clientRef.current.talk(reply);
      setStatus("На линии");
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
    intentionalStopRef.current = false;
    clearTimers();
    setError("");
    setPhaseSafe("connecting");
    setStatus("Connecting to NULLXES…");
    setSeconds(0);
    setCaption("");

    try {
      const { sessionToken } = await createSessionToken();
      if (!sessionToken) throw new Error("empty session token");
      if (!startingRef.current) return;

      const client = createAnamClient(sessionToken);
      clientRef.current = client;

      client.addListener(AnamEvent.SESSION_READY, () => {
        setStatus("Session ready…");
      });
      client.addListener(AnamEvent.CONNECTION_ESTABLISHED, () => {
        setStatus("Secure link…");
      });
      client.addListener(AnamEvent.MIC_PERMISSION_PENDING, () => {
        setStatus("Allow microphone in Telegram…");
      });
      client.addListener(AnamEvent.MIC_PERMISSION_DENIED, (err) => {
        clearTimers();
        setError(`Микрофон запрещён: ${err}`);
        setPhaseSafe("error");
        setStatus("Нет доступа к микрофону");
      });
      client.addListener(AnamEvent.VIDEO_STREAM_STARTED, () => {
        const video = videoRef.current;
        if (video) {
          video.muted = true;
          void video.play().then(markLive).catch(() => undefined);
        }
        const id = window.setTimeout(markLive, LIVE_FALLBACK_MS);
        timersRef.current.push(id);
      });
      client.addListener(AnamEvent.VIDEO_PLAY_STARTED, () => {
        markLive();
      });
      client.addListener(AnamEvent.CONNECTION_CLOSED, (reason, details) => {
        clientRef.current = null;
        clearTimers();
        if (
          intentionalStopRef.current ||
          reason === "CONNECTION_CLOSED_CODE_NORMAL"
        ) {
          if (phaseRef.current !== "idle") {
            setError("");
            setPhaseSafe("idle");
            setStatus("");
          }
          return;
        }
        setError(friendlyCloseReason(String(reason), details));
        setPhaseSafe("error");
        setStatus("Session ended");
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
        video.setAttribute("webkit-playsinline", "true");
      }

      const timeoutId = window.setTimeout(() => {
        if (phaseRef.current !== "connecting" || !clientRef.current) return;
        void (async () => {
          await stopSession();
          setError("Таймаут. Разреши микрофон и попробуй снова.");
          setPhaseSafe("error");
          setStatus("Не удалось соединиться");
        })();
      }, CONNECT_TIMEOUT_MS);
      timersRef.current.push(timeoutId);

      await client.streamToVideoElement("persona-video");
    } catch (e) {
      clearTimers();
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setPhaseSafe("error");
      setStatus("Ошибка соединения");
      const client = clientRef.current;
      clientRef.current = null;
      if (client) {
        intentionalStopRef.current = true;
        try {
          await client.stopStreaming();
        } catch {
          /* ignore */
        }
        intentionalStopRef.current = false;
      }
    } finally {
      startingRef.current = false;
    }
  }

  function toggleMic() {
    const client = clientRef.current;
    if (!client || phaseRef.current !== "live") return;
    if (micMuted) {
      client.unmuteInputAudio();
      setMicMuted(false);
    } else {
      client.muteInputAudio();
      setMicMuted(true);
    }
  }

  async function endAndClose() {
    await stopSession();
    onClose();
  }

  const isLive = phase === "live";
  const isConnecting = phase === "connecting";
  const showPreview = phase === "idle" || phase === "error" || isConnecting;
  const subtitle = subtitleFor(phase, status, error);
  const pillLabel = isLive
    ? status.includes("Думаю")
      ? "Thinking"
      : "Live"
    : isConnecting
      ? "Connecting"
      : phase === "error"
        ? "Error"
        : "Idle";

  return (
    <div className="relative mx-auto flex h-[var(--tg-viewport-stable-height,100vh)] w-full max-w-md flex-col overflow-hidden bg-black">
      <video
        id="persona-video"
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="absolute inset-0 h-full w-full object-cover bg-black"
      />

      {showPreview ? (
        <div className="absolute inset-0 z-[1]">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt={PERSONA_NAME}
              className="h-full w-full object-cover object-top"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-[#0a0a0a] text-4xl font-semibold tracking-[0.2em] text-neutral-600">
              AK
            </div>
          )}
          <div className="absolute inset-0 bg-linear-to-t from-black/80 via-black/25 to-black/40" />
        </div>
      ) : (
        <div className="pointer-events-none absolute inset-0 z-[1] bg-linear-to-t from-black/70 via-transparent to-black/35" />
      )}

      {/* Top chrome */}
      <header className="relative z-10 flex shrink-0 items-start gap-2 px-3 pt-[max(10px,env(safe-area-inset-top))]">
        <button
          type="button"
          onClick={() => void endAndClose()}
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-black/45 text-white backdrop-blur-md active:bg-black/70"
          aria-label="Back"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="min-w-0 flex-1 pt-0.5">
          <p className="truncate text-[13px] font-semibold tracking-tight text-white">
            Talk · {PERSONA_NAME}
          </p>
          <p className="mt-0.5 flex items-center gap-1.5 truncate text-[11px] text-neutral-300">
            {isConnecting ? (
              <Loader2 className="h-3 w-3 shrink-0 animate-spin text-gold" />
            ) : null}
            <span className="truncate">{subtitle}</span>
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 pt-0.5">
          {isLive || isConnecting ? (
            <button
              type="button"
              onClick={() => void stopSession()}
              className="h-8 rounded-md bg-[#c23b3b] px-2.5 text-[11px] font-semibold text-white active:bg-[#a83232]"
            >
              End
            </button>
          ) : null}
          <span className="hidden items-center gap-1 rounded-md border border-white/10 bg-black/40 px-1.5 py-1 text-[10px] text-neutral-200 xs:flex sm:flex">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isLive
                  ? "bg-emerald-400"
                  : isConnecting
                    ? "bg-amber-400"
                    : "bg-emerald-400/80"
              }`}
            />
            {isLive ? "Online" : "Ready"}
          </span>
          <span className="rounded-md border border-white/10 bg-black/40 px-1.5 py-1 font-mono text-[10px] tabular-nums text-neutral-200">
            {formatTimer(seconds)}
          </span>
          <button
            type="button"
            onClick={() => setShowDetails((v) => !v)}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-white/10 bg-black/40 text-neutral-200 active:bg-black/60"
            aria-label="Details"
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {showDetails ? (
        <div className="relative z-10 mx-3 mt-2 rounded-xl border border-white/10 bg-black/70 px-3 py-2 text-[11px] leading-relaxed text-neutral-300 backdrop-blur-md">
          Anam native stream · NULLXES brain · mic via Telegram WebView.
          {error ? <p className="mt-1 text-red-400">{error}</p> : null}
        </div>
      ) : null}

      {/* Brand watermark */}
      <p className="pointer-events-none absolute left-3 top-[4.5rem] z-[2] text-[9px] font-medium tracking-[0.18em] text-white/35">
        NULLXES
      </p>

      {/* Captions */}
      {showCaptions && caption && isLive ? (
        <div className="relative z-10 mx-3 mt-auto mb-2 rounded-xl border border-white/10 bg-black/55 px-3 py-2 text-[13px] leading-snug text-white backdrop-blur-md">
          {caption}
        </div>
      ) : (
        <div className="relative z-10 mt-auto" />
      )}

      {/* Name pill */}
      <div className="relative z-10 mb-2 flex items-end justify-between px-3">
        <div className="inline-flex max-w-[70%] items-center gap-2 rounded-full border border-white/10 bg-black/50 px-2.5 py-1.5 backdrop-blur-md">
          <span
            className={`h-1.5 w-1.5 shrink-0 rounded-full ${
              isLive ? "bg-emerald-400" : isConnecting ? "bg-amber-400 animate-pulse" : "bg-neutral-400"
            }`}
          />
          <span className="truncate text-[11px] text-neutral-100">
            {pillLabel}
            <span className="text-neutral-400"> · </span>
            {PERSONA_NAME}
          </span>
        </div>
        <span className="text-[10px] text-white/30">HD</span>
      </div>

      {/* Bottom toolbar */}
      <footer className="relative z-10 px-3 pb-[calc(12px+env(safe-area-inset-bottom))]">
        {phase === "error" && error ? (
          <p className="mb-2 text-center text-[12px] text-red-400">{error}</p>
        ) : null}

        <div className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-black/55 px-2 py-2 backdrop-blur-md">
          <button
            type="button"
            disabled={!isLive}
            onClick={toggleMic}
            className={`flex h-11 w-11 items-center justify-center rounded-xl border transition-colors ${
              !isLive
                ? "border-white/5 bg-white/5 text-neutral-500"
                : micMuted
                  ? "border-red-500/40 bg-red-500/20 text-red-300"
                  : "border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
            }`}
            aria-label="Microphone"
          >
            {micMuted || !isLive ? (
              <MicOff className="h-4 w-4" />
            ) : (
              <Mic className="h-4 w-4" />
            )}
          </button>

          <button
            type="button"
            disabled={!isLive}
            onClick={() => setShowCaptions((v) => !v)}
            className={`flex h-11 w-11 items-center justify-center rounded-xl border transition-colors ${
              !isLive
                ? "border-white/5 bg-white/5 text-neutral-500"
                : showCaptions
                  ? "border-white/20 bg-white/15 text-white"
                  : "border-white/10 bg-white/5 text-neutral-300"
            }`}
            aria-label="Captions"
          >
            <Captions className="h-4 w-4" />
          </button>

          {isLive || isConnecting ? (
            <button
              type="button"
              onClick={() => void stopSession()}
              className="flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-white px-3 text-[13px] font-semibold text-black active:bg-neutral-200"
            >
              {isConnecting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Cancel
                </>
              ) : (
                <>
                  <Square className="h-3.5 w-3.5 fill-current" />
                  Stop session
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void startSession()}
              className="flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-white px-3 text-[13px] font-semibold text-black active:bg-neutral-200"
            >
              <Play className="h-4 w-4 fill-current" />
              Start session
            </button>
          )}
        </div>
      </footer>
    </div>
  );
}
