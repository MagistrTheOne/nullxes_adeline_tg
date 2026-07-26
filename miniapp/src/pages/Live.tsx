import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Captions,
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
/** Mic / turn indicator while live */
type Turn = "listening" | "thinking" | "speaking" | "muted";

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
  const detail = (details || "").toLowerCase();
  if (detail.includes("max duration") || detail.includes("maxsession")) {
    return "Сессия Anam закончилась по таймеру. Нажми Start session ещё раз.";
  }
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

function turnLabel(turn: Turn): string {
  switch (turn) {
    case "listening":
      return "Слушает";
    case "thinking":
      return "Думает";
    case "speaking":
      return "Отвечает";
    case "muted":
      return "Микрофон выкл";
  }
}

export function Live({ onClose }: Props) {
  const clientRef = useRef<LiveClient | null>(null);
  const busyRef = useRef(false);
  const startingRef = useRef(false);
  const intentionalStopRef = useRef(false);
  const phaseRef = useRef<Phase>("idle");
  const turnRef = useRef<Turn>("listening");
  const micMutedRef = useRef(false);
  const userBuf = useRef("");
  /** Dedup for MESSAGE_HISTORY_UPDATED (custom LLM path). */
  const lastUserMsgIdRef = useRef<string>("");
  const showCaptionsRef = useRef(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timersRef = useRef<number[]>([]);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const [phase, setPhase] = useState<Phase>("idle");
  const [turn, setTurn] = useState<Turn>("listening");
  const [status, setStatus] = useState("");
  const [caption, setCaption] = useState("");
  const [showCaptions, setShowCaptions] = useState(true);
  const [micMuted, setMicMuted] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");

  const setPhaseSafe = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);

  const setTurnSafe = useCallback((next: Turn) => {
    turnRef.current = next;
    setTurn(next);
  }, []);

  const clearTimers = useCallback(() => {
    for (const id of timersRef.current) window.clearTimeout(id);
    timersRef.current = [];
  }, []);

  const ensureVideoMutedPlaying = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = true;
    video.defaultMuted = true;
    video.volume = 0;
    video.setAttribute("muted", "");
    void video.play().catch(() => undefined);
  }, []);

  const armMic = useCallback(() => {
    const client = clientRef.current;
    if (!client) return;
    try {
      client.unmuteInputAudio();
    } catch {
      /* ignore */
    }
    micMutedRef.current = false;
    setMicMuted(false);
    if (phaseRef.current === "live" && turnRef.current !== "thinking" && turnRef.current !== "speaking") {
      setTurnSafe("listening");
    }
  }, [setTurnSafe]);

  const markLive = useCallback(() => {
    if (phaseRef.current !== "connecting" || !clientRef.current) return;
    ensureVideoMutedPlaying();
    clearTimers();
    setPhaseSafe("live");
    setStatus("Live session · Secure connection");
    armMic();
    setTurnSafe("listening");
  }, [armMic, clearTimers, ensureVideoMutedPlaying, setPhaseSafe, setTurnSafe]);

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
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.srcObject = null;
    }
    setError("");
    setPhaseSafe("idle");
    setTurnSafe("listening");
    setSeconds(0);
    setCaption("");
    setMicMuted(false);
    micMutedRef.current = false;
    setStatus("");
    userBuf.current = "";
    lastUserMsgIdRef.current = "";
    intentionalStopRef.current = false;
  }, [clearTimers, setPhaseSafe, setTurnSafe]);

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

  async function speakAsPersona(text: string) {
    const client = clientRef.current;
    if (!client || !text.trim()) return;
    setTurnSafe("speaking");
    setStatus("Отвечает…");
    if (showCaptionsRef.current) setCaption(text);
    // Prefer talk() — more reliable TTS on Telegram WebView than TalkMessageStream alone.
    try {
      await client.talk(text);
    } catch {
      try {
        const talkStream = client.createTalkMessageStream();
        if (talkStream.isActive()) {
          await talkStream.streamMessageChunk(text, true);
        }
      } catch {
        /* ignore — UI already shows caption */
      }
    }
    // Keep persona audio element unmuted after each utterance.
    const audio = audioRef.current;
    if (audio) {
      audio.muted = false;
      audio.volume = 1;
      void audio.play().catch(() => undefined);
    }
    setStatus("Слушает…");
    setTurnSafe(micMutedRef.current ? "muted" : "listening");
  }

  async function handleUserSpeech(text: string) {
    if (busyRef.current || !clientRef.current) return;
    const trimmed = text.trim();
    if (!trimmed) return;

    busyRef.current = true;
    setTurnSafe("thinking");
    setStatus("Думает…");
    if (showCaptionsRef.current) setCaption(trimmed);

    try {
      const { reply } = await chatWithBrain(trimmed);
      if (!clientRef.current) return;
      await speakAsPersona(reply);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setStatus(`Ошибка: ${msg}`);
      setTurnSafe(micMutedRef.current ? "muted" : "listening");
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
    setTurnSafe("listening");
    setStatus("Connecting to NULLXES…");
    setSeconds(0);
    setCaption("");
    userBuf.current = "";
    lastUserMsgIdRef.current = "";

    try {
      const unlock = audioRef.current;
      if (unlock) {
        unlock.muted = false;
        void unlock.play().catch(() => undefined);
        unlock.pause();
      }

      const session = await createSessionToken();
      const { sessionToken } = session;
      if (!sessionToken) throw new Error("empty session token");
      if (!startingRef.current) return;

      const client = createAnamClient(sessionToken);
      clientRef.current = client;
      let greetingSpoken = false;

      const speakGreetingOnce = () => {
        if (greetingSpoken || !session.speakGreeting || !session.greeting) return;
        if (!clientRef.current) return;
        greetingSpoken = true;
        void (async () => {
          // Wait a beat so video/audio pipes are ready.
          await new Promise((r) => window.setTimeout(r, 400));
          if (!clientRef.current || intentionalStopRef.current) return;
          busyRef.current = true;
          try {
            await speakAsPersona(session.greeting!);
          } finally {
            busyRef.current = false;
          }
        })();
      };

      client.addListener(AnamEvent.SESSION_READY, () => {
        setStatus("Session ready…");
        armMic();
      });
      client.addListener(AnamEvent.CONNECTION_ESTABLISHED, () => {
        setStatus("Secure link…");
      });
      client.addListener(AnamEvent.MIC_PERMISSION_PENDING, () => {
        setStatus("Разреши микрофон в Telegram…");
      });
      client.addListener(AnamEvent.MIC_PERMISSION_GRANTED, () => {
        setStatus("Микрофон OK…");
        armMic();
      });
      client.addListener(AnamEvent.MIC_PERMISSION_DENIED, (err) => {
        clearTimers();
        setError(`Микрофон запрещён: ${err}`);
        setPhaseSafe("error");
        setStatus("Нет доступа к микрофону");
      });
      client.addListener(AnamEvent.INPUT_AUDIO_STREAM_STARTED, () => {
        armMic();
      });
      client.addListener(AnamEvent.VIDEO_STREAM_STARTED, () => {
        ensureVideoMutedPlaying();
        const id = window.setTimeout(() => {
          markLive();
          speakGreetingOnce();
        }, LIVE_FALLBACK_MS);
        timersRef.current.push(id);
      });
      client.addListener(AnamEvent.VIDEO_PLAY_STARTED, () => {
        ensureVideoMutedPlaying();
        markLive();
        speakGreetingOnce();
      });
      client.addListener(AnamEvent.AUDIO_STREAM_STARTED, (stream) => {
        const audio = audioRef.current;
        if (!audio) return;
        audio.srcObject = stream;
        audio.muted = false;
        audio.volume = 1;
        void audio.play().catch(() => undefined);
      });
      client.addListener(AnamEvent.USER_SPEECH_STARTED, () => {
        if (micMutedRef.current || busyRef.current) return;
        setTurnSafe("listening");
        setStatus("Слушает…");
      });
      client.addListener(AnamEvent.USER_SPEECH_ENDED, () => {
        if (micMutedRef.current || busyRef.current) return;
        setStatus("Обрабатываю речь…");
      });
      // Doc path for CUSTOMER_CLIENT_V1: respond only when last turn is user.
      client.addListener(AnamEvent.MESSAGE_HISTORY_UPDATED, (messages) => {
        if (micMutedRef.current || busyRef.current) return;
        const list = Array.isArray(messages) ? messages : [];
        if (list.length === 0) return;
        const last = list[list.length - 1];
        if (String(last?.role || "").toLowerCase() !== "user") return;
        const id = String(last.id || "");
        const text = String(last.content || "").trim();
        if (!text) return;
        if (id && id === lastUserMsgIdRef.current) return;
        if (id) lastUserMsgIdRef.current = id;
        else lastUserMsgIdRef.current = text;
        void handleUserSpeech(text);
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
          if (chunk) setTurnSafe("speaking");
          if (showCaptionsRef.current) {
            setCaption((prev) =>
              event.endOfSpeech ? chunk || prev : `${prev}${chunk}`.slice(-280),
            );
          }
          if (event.endOfSpeech && !busyRef.current) {
            setTurnSafe(micMutedRef.current ? "muted" : "listening");
            setStatus("Live session · Secure connection");
          }
          return;
        }

        if (role === "user") {
          // Captions only — brain turns come from MESSAGE_HISTORY_UPDATED (Anam custom-LLM docs).
          if (!micMutedRef.current && !busyRef.current) {
            setTurnSafe("listening");
          }
          userBuf.current += chunk;
          if (showCaptionsRef.current && userBuf.current) {
            setCaption(userBuf.current.slice(-280));
          }
          if (event.endOfSpeech) {
            userBuf.current = "";
          }
        }
      });

      ensureVideoMutedPlaying();
      const video = videoRef.current;
      if (video) {
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
      // Mic can be ready after stream starts — force unmute once more.
      armMic();
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
    if (micMutedRef.current) {
      client.unmuteInputAudio();
      micMutedRef.current = false;
      setMicMuted(false);
      setTurnSafe("listening");
      setStatus("Live session · Secure connection");
    } else {
      client.muteInputAudio();
      micMutedRef.current = true;
      setMicMuted(true);
      setTurnSafe("muted");
      setStatus("Микрофон выключен");
    }
  }

  async function endAndClose() {
    await stopSession();
    onClose();
  }

  const isLive = phase === "live";
  const isConnecting = phase === "connecting";
  const showPreview = phase === "idle" || phase === "error" || isConnecting;

  const subtitle = isConnecting
    ? status || "Connecting…"
    : isLive
      ? turnLabel(turn)
      : phase === "error"
        ? error || status || "Session ended"
        : "Standing by · connection check";

  const pillTone =
    turn === "speaking"
      ? "bg-sky-400"
      : turn === "thinking"
        ? "bg-amber-400 animate-pulse"
        : turn === "muted"
          ? "bg-red-400"
          : isLive
            ? "bg-emerald-400"
            : isConnecting
              ? "bg-amber-400 animate-pulse"
              : "bg-neutral-400";

  return (
    <div className="relative mx-auto flex h-[var(--tg-viewport-stable-height,100vh)] w-full max-w-md flex-col overflow-hidden bg-black">
      <video
        id="persona-video"
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="absolute inset-0 z-0 h-full w-full object-cover object-center bg-black"
      />
      <audio ref={audioRef} autoPlay playsInline className="hidden" />

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
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/5 bg-linear-to-t from-black/75 to-transparent" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-linear-to-b from-black/50 to-transparent" />
        </div>
      ) : (
        <>
          <div className="pointer-events-none absolute inset-x-0 top-0 z-[1] h-28 bg-linear-to-b from-black/55 to-transparent" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 z-[1] h-2/5 bg-linear-to-t from-black/70 to-transparent" />
        </>
      )}

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
            {isConnecting || turn === "thinking" ? (
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
          <span className="rounded-md border border-white/10 bg-black/40 px-1.5 py-1 font-mono text-[10px] tabular-nums text-neutral-200">
            {formatTimer(seconds)}
          </span>
        </div>
      </header>

      <p className="pointer-events-none absolute left-3 top-[4.5rem] z-[2] text-[9px] font-medium tracking-[0.18em] text-white/35">
        NULLXES
      </p>

      {showCaptions && caption && isLive ? (
        <div className="relative z-10 mx-3 mt-auto mb-2 rounded-xl border border-white/10 bg-black/55 px-3 py-2 text-[13px] leading-snug text-white backdrop-blur-md">
          {caption}
        </div>
      ) : (
        <div className="relative z-10 mt-auto" />
      )}

      <div className="relative z-10 mb-2 flex items-end justify-between px-3">
        <div className="inline-flex max-w-[78%] items-center gap-2 rounded-full border border-white/10 bg-black/50 px-2.5 py-1.5 backdrop-blur-md">
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${pillTone}`} />
          <span className="truncate text-[11px] text-neutral-100">
            {isLive ? turnLabel(turn) : isConnecting ? "Connecting" : "Idle"}
            <span className="text-neutral-400"> · </span>
            {PERSONA_NAME}
          </span>
        </div>
        <span className="text-[10px] text-white/30">HD</span>
      </div>

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
                  : turn === "listening"
                    ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
                    : turn === "thinking"
                      ? "border-amber-500/40 bg-amber-500/20 text-amber-200"
                      : turn === "speaking"
                        ? "border-sky-500/40 bg-sky-500/20 text-sky-200"
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
