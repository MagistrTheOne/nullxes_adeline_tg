import { useEffect, useState } from "react";
import { MessageSquare, Mic, Video } from "lucide-react";
import { mainButton } from "@tma.js/sdk-react";
import { fetchPersona, type PersonaCard } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type Props = {
  onLive: () => void;
  onChat: () => void;
  onVoiceHint: () => void;
};

export function Home({ onLive, onChat, onVoiceHint }: Props) {
  const [card, setCard] = useState<PersonaCard | null>(null);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  useEffect(() => {
    fetchPersona()
      .then(setCard)
      .catch((e: Error) => setError(e.message));
  }, []);

  // Hide Telegram MainButton — duplicate CTA was breaking layout.
  useEffect(() => {
    if (!mainButton.setParams.isAvailable()) return;
    mainButton.setParams({ isVisible: false });
    return () => {
      if (mainButton.setParams.isAvailable()) {
        mainButton.setParams({ isVisible: false });
      }
    };
  }, []);

  const handleVoice = () => {
    setHint("Закрой Mini App и отправь голосовое в чат боту.");
    onVoiceHint();
  };

  const displayName = card?.name || "Adeline Kalen";

  return (
    <div className="mx-auto flex w-full max-w-md min-h-(--tg-viewport-stable-height,100vh) flex-col gap-3 overflow-x-hidden bg-black p-3 pb-[calc(16px+env(safe-area-inset-bottom))]">
      <Card className="min-w-0 overflow-hidden border-neutral-800 bg-[#111] shadow-none">
        <div className="relative aspect-4/5 max-h-[46vh] bg-neutral-950">
          {card?.imageUrl ? (
            <img
              src={card.imageUrl}
              alt={displayName}
              className="h-full w-full object-cover object-top"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-5xl font-semibold tracking-widest text-neutral-600">
              AK
            </div>
          )}
        </div>
        <CardContent className="min-w-0 space-y-3 pt-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold leading-tight text-white">
              {displayName}{" "}
              <span className="text-gold">из NULLXES</span>
            </h1>
            <p className="text-sm text-gold/90">
              {card?.title || "Digital executive"}
            </p>
          </div>
          <Badge
            variant="outline"
            className="gap-1.5 border-neutral-600 bg-black/40 text-neutral-200"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {card?.status || "Online · ready"}
          </Badge>
          <p className="text-sm leading-relaxed text-neutral-400">
            {card?.blurb ||
              "Цифровая сотрудница NULLXES. Мы создаём цифровых сотрудников для компаний и персональных цифровых друзей."}
          </p>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
        </CardContent>
      </Card>

      <div className="grid min-w-0 grid-cols-2 gap-2">
        <button
          type="button"
          onClick={handleVoice}
          className="min-w-0 rounded-2xl border border-neutral-800 bg-[#111] p-3 text-left transition-colors hover:bg-neutral-900"
        >
          <Mic className="mb-2 h-5 w-5 text-gold" />
          <div className="truncate text-sm font-semibold text-white">Голос</div>
          <div className="mt-0.5 text-xs leading-snug text-neutral-400">
            Звонок в чате бота
          </div>
        </button>
        <button
          type="button"
          onClick={onLive}
          className="min-w-0 rounded-2xl border border-neutral-800 bg-[#111] p-3 text-left transition-colors hover:bg-neutral-900"
        >
          <Video className="mb-2 h-5 w-5 text-gold" />
          <div className="text-sm font-semibold leading-snug text-white">
            Набрать по видео
          </div>
          <div className="mt-0.5 truncate text-xs text-neutral-400">
            {displayName}
          </div>
        </button>
      </div>

      <Button
        type="button"
        size="lg"
        className="h-12 w-full shrink-0 rounded-full bg-white text-black hover:bg-neutral-200"
        onClick={onChat}
      >
        <MessageSquare className="h-5 w-5" />
        Написать Adeline
      </Button>

      {hint ? (
        <p className="text-center text-xs text-neutral-500">{hint}</p>
      ) : null}
    </div>
  );
}
