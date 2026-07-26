import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, Send } from "lucide-react";
import { backButton, mainButton } from "@tma.js/sdk-react";
import {
  chatWithBrain,
  fetchHistory,
  fetchPersona,
  type ChatMessage,
} from "@/api/client";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

type Props = {
  onClose: () => void;
};

export function Chat({ onClose }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (mainButton.setParams.isAvailable()) {
      mainButton.setParams({ isVisible: false });
    }
    if (backButton.show.isAvailable()) backButton.show();
    const off = backButton.onClick(onClose);
    return () => {
      off();
      if (backButton.hide.isAvailable()) backButton.hide();
    };
  }, [onClose]);

  useEffect(() => {
    fetchPersona()
      .then((p) => setAvatarUrl(p.imageUrl || ""))
      .catch(() => undefined);
    fetchHistory()
      .then((r) => setMessages(r.messages || []))
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    setText("");
    setBusy(true);
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: value }]);
    try {
      const { history } = await chatWithBrain(value);
      setMessages(history);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-(--tg-viewport-stable-height,100vh) flex-col">
      <header className="flex items-center gap-3 border-b border-border px-3 py-3">
        <Button type="button" variant="ghost" size="icon" className="h-10 w-10" onClick={onClose}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <Avatar src={avatarUrl} alt="Adeline Kalen" className="h-9 w-9 grayscale" />
        <div className="min-w-0">
          <p className="truncate font-semibold">Adeline Kalen из NULLXES</p>
          <p className="truncate text-xs text-muted-foreground">Чат</p>
        </div>
      </header>

      <ScrollArea className="min-h-0 flex-1 px-3 py-4">
        <div className="flex flex-col gap-3">
          {messages.length === 0 ? (
            <p className="px-2 text-center text-sm text-muted-foreground">
              Напиши сообщение — история общая с чатом бота.
            </p>
          ) : null}
          {messages.map((m, i) => (
            <div
              key={`${m.role}-${i}-${m.content.slice(0, 12)}`}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "border border-border bg-card text-card-foreground"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {busy ? (
            <p className="text-xs text-muted-foreground">Печатает…</p>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <form
        onSubmit={onSubmit}
        className="flex gap-2 border-t border-border p-3 pb-[calc(12px+env(safe-area-inset-bottom))]"
      >
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Сообщение…"
          disabled={busy}
        />
        <Button type="submit" size="icon" disabled={busy || !text.trim()} aria-label="Send">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
