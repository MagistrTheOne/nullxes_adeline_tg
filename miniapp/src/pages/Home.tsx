import { useEffect, useState } from "react";
import { MessageSquare, Mic, Video } from "lucide-react";
import { mainButton } from "@tma.js/sdk-react";
import {
  fetchPersona,
  setExperienceMode,
  type CustomRole,
  type PersonaCard,
} from "@/api/client";
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
  const [customUnlocked, setCustomUnlocked] = useState(false);
  const [customRole, setCustomRole] = useState<CustomRole>({});
  const [saving, setSaving] = useState(false);

  const reload = () =>
    fetchPersona()
      .then((p) => {
        setCard(p);
        setCustomUnlocked(Boolean(p.customUnlocked));
        setCustomRole(p.customRole || {});
      })
      .catch((e: Error) => setError(e.message));

  useEffect(() => {
    void reload();
  }, []);

  useEffect(() => {
    if (!mainButton.setParams.isAvailable()) return;
    mainButton.setParams({ isVisible: false });
    return () => {
      if (mainButton.setParams.isAvailable()) {
        mainButton.setParams({ isVisible: false });
      }
    };
  }, []);

  const saveCustomRole = async () => {
    if (!customUnlocked) return;
    setSaving(true);
    setError("");
    try {
      await setExperienceMode("custom", {
        title: customRole.title || "",
        tone: customRole.tone || "",
        goals: customRole.goals?.length
          ? customRole.goals
          : customRole.title
            ? [String(customRole.title)]
            : [],
        greeting: customRole.greeting || "",
        boundaries: customRole.boundaries || "",
      });
      setHint("Кастомная роль сохранена — откроется в видео.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleVoice = () => {
    setHint("Закрой Mini App и отправь голосовое в чат боту.");
    onVoiceHint();
  };

  const displayName = card?.name || "Adeline Kalen";

  return (
    <div className="mx-auto flex w-full max-w-md min-h-(--tg-viewport-stable-height,100vh) flex-col gap-3 overflow-x-hidden bg-black p-3 pb-[calc(16px+env(safe-area-inset-bottom))]">
      <Card className="min-w-0 overflow-hidden border-neutral-800 bg-[#111] shadow-none">
        <div className="w-full bg-neutral-950">
          <div className="relative w-full overflow-hidden aspect-3/4 max-h-[min(56vh,560px)]">
            {card?.imageUrl ? (
              <img
                src={card.imageUrl}
                alt={displayName}
                className="absolute inset-0 h-full w-full object-cover object-[center_18%]"
              />
            ) : (
              <div className="flex h-full min-h-70 w-full items-center justify-center text-5xl font-semibold tracking-widest text-neutral-600">
                AK
              </div>
            )}
          </div>
        </div>
        <CardContent className="min-w-0 space-y-3 pt-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold leading-tight text-white">
              {displayName}{" "}
              <span className="text-gold">из NULLXES</span>
            </h1>
            <p className="text-sm text-gold/90">
              {card?.title || "Цифровой сотрудник NULLXES"}
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
            Наберите по видео — Аделина сама поймёт, это знакомство или разговор
            про бизнес, и подстроится.
          </p>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
        </CardContent>
      </Card>

      <Button
        type="button"
        size="lg"
        disabled={Boolean(error)}
        className="h-14 w-full shrink-0 rounded-full bg-white text-base font-semibold text-black hover:bg-neutral-200"
        onClick={onLive}
      >
        <Video className="h-5 w-5" />
        Набрать по видео
      </Button>

      {customUnlocked ? (
        <div className="rounded-2xl border border-neutral-800 bg-[#111] p-3">
          <div className="text-sm font-semibold text-white">
            Свой цифровой сотрудник
          </div>
          <div className="mt-2 space-y-2">
            <input
              className="w-full rounded-lg border border-neutral-700 bg-black px-3 py-2 text-sm text-white outline-none"
              placeholder="Роль"
              value={customRole.title || ""}
              onChange={(e) =>
                setCustomRole((r) => ({ ...r, title: e.target.value }))
              }
            />
            <input
              className="w-full rounded-lg border border-neutral-700 bg-black px-3 py-2 text-sm text-white outline-none"
              placeholder="Тон"
              value={customRole.tone || ""}
              onChange={(e) =>
                setCustomRole((r) => ({ ...r, tone: e.target.value }))
              }
            />
            <Button
              type="button"
              disabled={saving}
              className="h-10 w-full rounded-full bg-white text-black hover:bg-neutral-200"
              onClick={() => void saveCustomRole()}
            >
              Сохранить роль
            </Button>
          </div>
        </div>
      ) : null}

      <div className="grid min-w-0 grid-cols-2 gap-2">
        <button
          type="button"
          onClick={handleVoice}
          className="min-w-0 rounded-2xl border border-neutral-800 bg-[#111] p-3 text-left transition-colors hover:bg-neutral-900"
        >
          <Mic className="mb-2 h-5 w-5 text-gold" />
          <div className="truncate text-sm font-semibold text-white">Голос</div>
          <div className="mt-0.5 text-xs leading-snug text-neutral-400">
            В чате бота
          </div>
        </button>
        <button
          type="button"
          onClick={onChat}
          className="min-w-0 rounded-2xl border border-neutral-800 bg-[#111] p-3 text-left transition-colors hover:bg-neutral-900"
        >
          <MessageSquare className="mb-2 h-5 w-5 text-gold" />
          <div className="truncate text-sm font-semibold text-white">Чат</div>
          <div className="mt-0.5 text-xs leading-snug text-neutral-400">
            Написать текстом
          </div>
        </button>
      </div>

      {hint ? (
        <p className="text-center text-xs text-neutral-500">{hint}</p>
      ) : null}
    </div>
  );
}
