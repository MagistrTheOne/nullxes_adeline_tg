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

  useEffect(() => {
    if (!mainButton.setParams.isAvailable()) return;

    mainButton.setParams({
      text: "Написать Adeline",
      isVisible: true,
      isEnabled: true,
      hasShineEffect: false,
      bgColor: "#111111",
      textColor: "#ffffff",
    });

    const off = mainButton.onClick(() => {
      onChat();
    });

    return () => {
      off();
      if (mainButton.setParams.isAvailable()) {
        mainButton.setParams({ isVisible: false });
      }
    };
  }, [onChat]);

  const handleVoice = () => {
    setHint("Закрой Mini App и отправь голосовое в чат боту.");
    onVoiceHint();
  };

  const displayName = card?.name || "Adeline Kalen";

  return (
    <div className="flex min-h-(--tg-viewport-stable-height,100vh) flex-col gap-4 bg-black p-3 pb-[calc(12px+env(safe-area-inset-bottom))]">
      <Card className="overflow-hidden border-neutral-800 bg-neutral-950 shadow-none">
        <div className="relative aspect-4/5 bg-neutral-950">
          {card?.imageUrl ? (
            <img
              src={card.imageUrl}
              alt={displayName}
              className="h-full w-full object-cover grayscale"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-5xl font-semibold tracking-widest text-neutral-600">
              AK
            </div>
          )}
        </div>
        <CardContent className="space-y-3 pt-4">
          <div>
            <h1 className="text-xl font-semibold text-white">
              {displayName} из NULLXES
            </h1>
            <p className="text-sm text-neutral-400">
              {card?.title || "Digital executive"}
            </p>
          </div>
          <Badge variant="outline" className="gap-1.5 border-neutral-600 text-neutral-200">
            <span className="h-1.5 w-1.5 rounded-full bg-white" />
            {card?.status || "Online · ready"}
          </Badge>
          <p className="text-sm leading-relaxed text-neutral-400">
            {card?.blurb ||
              "Цифровая сотрудница NULLXES. Мы создаём цифровых сотрудников для компаний и персональных цифровых друзей."}
          </p>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Button
          type="button"
          variant="secondary"
          className="h-auto flex-col items-start gap-2 border border-neutral-800 bg-neutral-950 p-4 text-left text-white hover:bg-neutral-900"
          onClick={handleVoice}
        >
          <Mic className="h-5 w-5 text-white" />
          <span className="font-semibold">Голос</span>
          <span className="text-xs font-normal text-neutral-400">
            Голосовой звонок в чате
          </span>
        </Button>
        <Button
          type="button"
          variant="secondary"
          className="h-auto flex-col items-start gap-2 border border-neutral-800 bg-neutral-950 p-4 text-left text-white hover:bg-neutral-900"
          onClick={onLive}
        >
          <Video className="h-5 w-5 text-white" />
          <span className="font-semibold leading-snug">
            Набрать {displayName} по видео
          </span>
        </Button>
      </div>

      <Button
        type="button"
        size="lg"
        className="w-full bg-white text-black hover:bg-neutral-200"
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
