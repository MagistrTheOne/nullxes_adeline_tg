import { retrieveRawInitData } from "@tma.js/sdk-react";

export type ExperienceMode = "showcase" | "enterprise" | "custom";

export type CustomRole = {
  title?: string;
  tone?: string;
  goals?: string[];
  greeting?: string;
  boundaries?: string;
};

export type PersonaCard = {
  name: string;
  role: string;
  title: string;
  status: string;
  imageUrl: string;
  blurb: string;
  personaId: string;
  avatarId: string;
  experienceMode?: ExperienceMode;
  customUnlocked?: boolean;
  customRole?: CustomRole;
};

export type ExperienceState = {
  experience_mode?: ExperienceMode;
  custom_unlocked?: boolean;
  custom_role?: CustomRole;
  intro_shown?: boolean;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

function initDataHeader(): HeadersInit {
  let initData = "";
  try {
    initData = retrieveRawInitData() || "";
  } catch {
    initData = "";
  }
  return initData ? { "X-Telegram-Init-Data": initData } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...initDataHeader(),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    if (res.status === 503 || res.status === 502) {
      throw new Error(
        "Сервер/туннель недоступен. В чате бота нажми /start и открой Mini App новой кнопкой.",
      );
    }
    const err = await res
      .json()
      .catch(() => ({} as { error?: string; message?: string }));
    throw new Error(err.message || err.error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchPersona(): Promise<PersonaCard> {
  return request<PersonaCard>("/api/persona");
}

export function fetchExperience(): Promise<ExperienceState> {
  return request<ExperienceState>("/api/experience");
}

export function setExperienceMode(
  mode: ExperienceMode,
  customRole?: CustomRole,
): Promise<{ ok: boolean; experience: ExperienceState }> {
  return request("/api/experience", {
    method: "POST",
    body: JSON.stringify({ mode, customRole }),
  });
}

export type SessionTokenResponse = {
  sessionToken: string;
  greeting?: string;
  speakGreeting?: boolean;
  name?: string;
  role?: string;
};

export function createSessionToken(): Promise<SessionTokenResponse> {
  return request("/api/session-token", { method: "POST" });
}

export function fetchHistory(): Promise<{ messages: ChatMessage[] }> {
  return request("/api/history");
}

export function chatWithBrain(
  text: string,
): Promise<{ reply: string; history: ChatMessage[] }> {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}
