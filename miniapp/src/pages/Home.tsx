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
      text: "Message Adeline",
      isVisible: true,
      isEnabled: true,
      hasShineEffect: false,
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

  return (
    <div className="flex min-h-(--tg-viewport-stable-height,100vh) flex-col gap-4 p-3 pb-[calc(12px+env(safe-area-inset-bottom))]">
      <Card className="overflow-hidden">
        <div className="relative aspect-4/5 bg-secondary">
          {card?.imageUrl ? (
            <img
              src={card.imageUrl}
              alt={card.name || "Adeline Kalen"}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-5xl font-semibold tracking-widest text-muted-foreground/40">
              AK
            </div>
          )}
        </div>
        <CardContent className="space-y-3 pt-4">
          <div>
            <h1 className="text-xl font-semibold">
              {card?.name || "Adeline Kalen"} NULLXES
            </h1>
            <p className="text-sm text-muted-foreground">
              {card?.title || "Enterprise Executive"}
            </p>
          </div>
          <Badge variant="success" className="gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {card?.status || "Online · ready"}
          </Badge>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {card?.blurb ||
              "Ваш цифровой ассистент NULLXES. Пишите в чат, звоните голосом или выходите в живой видео-разговор."}
          </p>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Button
          type="button"
          variant="secondary"
          className="h-auto flex-col items-start gap-2 p-4 text-left"
          onClick={handleVoice}
        >
          <Mic className="h-5 w-5 text-primary" />
          <span className="font-semibold">Голос</span>
          <span className="text-xs font-normal text-muted-foreground">
            Голосовой в чате бота
          </span>
        </Button>
        <Button
          type="button"
          variant="secondary"
          className="h-auto flex-col items-start gap-2 p-4 text-left"
          onClick={onLive}
        >
          <Video className="h-5 w-5 text-primary" />
          <span className="font-semibold">Видео-аватар</span>
          <span className="text-xs font-normal text-muted-foreground">
            Live Anam stream
          </span>
        </Button>
      </div>

      <Button type="button" size="lg" className="w-full" onClick={onChat}>
        <MessageSquare className="h-5 w-5" />
        Message Adeline
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        {hint || "Чат Mini App и Telegram — одна история."}
      </p>
    </div>
  );
}
