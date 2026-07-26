"""Intent → Confidence → Memory → FSM soft routing (before LLM reply)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from services.user_state import user_states

# Confidence gates
CONF_CLARIFY = 0.6
CONF_PROCEED = 0.8

INTENT_LABELS = (
    "smalltalk",
    "explore_product",
    "business_interest",
    "pricing",
    "pilot",
    "partnership",
    "support",
    "escalate",
    "unknown",
)


@dataclass
class TurnRoute:
    intent: str
    confidence: float
    action: str  # clarify | proceed | answer_from_memory | stay
    experience_mode: str
    sales_stage: str
    topics_covered: list[str]
    memory_hits: list[str]
    guidance: str


_PATTERNS: list[tuple[str, float, list[str]]] = [
    (
        "escalate",
        0.9,
        [
            r"\bwhite\s*label\b",
            r"\boem\b",
            r"инвест",
            r"партн[её]р",
            r"лиценз",
            r"эксклюзив",
            r"юридич",
            r"договор",
            r"magistrtheone",
        ],
    ),
    (
        "pricing",
        0.88,
        [
            r"\bцен[аыуе]?\b",
            r"стоим",
            r"скол[ьк]ко\s+(стоит|будет)",
            r"\bпрайс\b",
            r"\bprice\b",
            r"\bcost\b",
            r"бюджет",
            r"5\s*млн",
            r"миллион",
        ],
    ),
    (
        "pilot",
        0.86,
        [
            r"пилот",
            r"\bpilot\b",
            r"попроб",
            r"внедр",
            r"запуск",
            r"proof\s*of\s*concept",
            r"\bpoc\b",
        ],
    ),
    (
        "partnership",
        0.84,
        [
            r"white\s*label",
            r"совместн",
            r"дистриб",
            r"реселл",
            r"партн[её]рств",
        ],
    ),
    (
        "business_interest",
        0.78,
        [
            r"для\s+(компан|бизнес|команд|отдел)",
            r"enterprise",
            r"корпорат",
            r"автоматиз",
            r"процесс",
            r"hr\b",
            r"продаж",
            r"поддержк",
            r"сотрудник",
            r"масштаб",
        ],
    ),
    (
        "explore_product",
        0.72,
        [
            r"что\s+(такое|умеет|можете)",
            r"расскаж",
            r"возможн",
            r"платформ",
            r"цифров",
            r"как\s+работ",
            r"demo",
            r"демо",
            r"показать",
        ],
    ),
    (
        "support",
        0.7,
        [
            r"не\s+работа",
            r"ошибк",
            r"помоги",
            r"как\s+открыть",
            r"микрофон",
            r"не\s+слыш",
            r"баг",
        ],
    ),
    (
        "smalltalk",
        0.65,
        [
            r"^(привет|здравств|hi|hello|hey)\b",
            r"как\s+дела",
            r"кто\s+ты",
            r"расскажи\s+о\s+себе",
            r"просто\s+поговор",
            r"потыкать",
            r"знаком",
        ],
    ),
]


def _score_intent(text: str) -> tuple[str, float]:
    low = text.lower().strip()
    if not low:
        return "unknown", 0.0
    best_intent = "unknown"
    best = 0.0
    for intent, base, patterns in _PATTERNS:
        hits = sum(1 for p in patterns if re.search(p, low, re.IGNORECASE))
        if not hits:
            continue
        # More hits → higher confidence, capped
        conf = min(0.98, base + 0.04 * (hits - 1))
        if conf > best:
            best = conf
            best_intent = intent
    if best_intent == "unknown":
        # Short casual → smalltalk; longer → explore
        if len(low.split()) <= 4:
            return "smalltalk", 0.55
        return "explore_product", 0.52
    return best_intent, best


def _topic_for_intent(intent: str) -> str | None:
    return {
        "pricing": "pricing",
        "pilot": "pilot",
        "partnership": "partnership",
        "business_interest": "business",
        "explore_product": "product",
        "escalate": "escalate",
    }.get(intent)


def _soft_mode(
    current: str,
    intent: str,
    confidence: float,
    custom_unlocked: bool,
) -> str:
    if current == "custom" and custom_unlocked:
        # Soft exit from custom only on clear escalate/pricing business spike
        if intent in {"pricing", "pilot", "business_interest"} and confidence >= CONF_PROCEED:
            return "enterprise"
        return "custom"
    if intent in {"pricing", "pilot", "partnership", "business_interest", "escalate"}:
        if confidence >= CONF_PROCEED:
            return "enterprise"
        if confidence >= CONF_CLARIFY and current == "showcase":
            return "showcase"  # clarify first, don't hard-switch
    if intent in {"smalltalk", "explore_product", "support"} and confidence >= CONF_PROCEED:
        if current == "enterprise" and intent == "smalltalk":
            return "showcase"  # soft return
    return current or "showcase"


def _stage_for(intent: str, stage: str, action: str) -> str:
    if action == "clarify":
        return stage or "qualification"
    mapping = {
        "pricing": "pilot",
        "pilot": "pilot",
        "partnership": "partnership",
        "business_interest": "discovery",
        "explore_product": "overview",
        "escalate": "escalate",
        "smalltalk": "overview",
        "support": "overview",
    }
    return mapping.get(intent, stage or "overview")


def route_turn(user_id: int, user_text: str) -> TurnRoute:
    """Classify turn, update memory, soft-switch FSM mode. Call before LLM."""
    state = user_states.get(user_id)
    memory = dict(state.get("dialog_memory") or {})
    topics = list(memory.get("topics_covered") or [])
    facts = dict(memory.get("facts") or {})

    intent, confidence = _score_intent(user_text)
    topic = _topic_for_intent(intent)
    memory_hits: list[str] = []

    if topic and topic in topics:
        memory_hits.append(topic)

    if confidence < CONF_CLARIFY:
        action = "clarify"
    elif memory_hits and intent in {"pricing", "pilot", "partnership"}:
        action = "answer_from_memory"
    elif confidence >= CONF_PROCEED:
        action = "proceed"
    elif intent in {"smalltalk", "explore_product", "support"}:
        # Mid-confidence casual turns: continue softly, don't interrogate
        action = "proceed"
    else:
        action = "clarify"

    mode = _soft_mode(
        str(state.get("experience_mode") or "showcase"),
        intent,
        confidence,
        bool(state.get("custom_unlocked")),
    )
    stage = _stage_for(intent, str(state.get("sales_stage") or "start"), action)

    # Mark topic covered when user clearly asks (even if we clarify)
    if topic and confidence >= CONF_CLARIFY and topic not in topics:
        topics.append(topic)

    if intent == "pricing" and confidence >= CONF_CLARIFY:
        facts["asked_pricing"] = True
    if intent == "pilot" and confidence >= CONF_CLARIFY:
        facts["asked_pilot"] = True

    guidance_parts = [
        f"TURN_PIPELINE: intent={intent} confidence={confidence:.2f} action={action}",
        f"experience_mode→{mode} sales_stage→{stage}",
    ]
    if action == "clarify":
        guidance_parts.append(
            "Confidence низкая — задай ОДИН уточняющий вопрос. Не питчи цену/пилот."
        )
    if action == "answer_from_memory":
        guidance_parts.append(
            "Тема уже обсуждалась (memory). НЕ спрашивай снова «интересна ли цена/пилот». "
            "Кратко ответь по факту и предложи следующий шаг."
        )
    if "pricing" in topics or facts.get("asked_pricing"):
        guidance_parts.append(
            "MEMORY: цена уже поднималась. Пилот от 5 000 000 ₽; кастом → @MagistrTheOne. Не переспрашивай."
        )
    if "pilot" in topics or facts.get("asked_pilot"):
        guidance_parts.append(
            "MEMORY: пилот уже обсуждали. Не начинай discovery с нуля — продолжай с того места."
        )
    if mode != state.get("experience_mode"):
        guidance_parts.append(
            f"SOFT TRANSITION: плавно смени роль с {state.get('experience_mode')} на {mode} "
            "(без объявления «я переключаюсь в режим…»)."
        )

    guidance = "\n".join(guidance_parts)

    patch: dict[str, Any] = {
        "intent": intent,
        "intent_confidence": round(confidence, 3),
        "dialog_memory": {
            "topics_covered": topics[-20:],
            "last_intent": intent,
            "last_confidence": round(confidence, 3),
            "facts": facts,
        },
        "sales_stage": stage,
    }
    if mode != state.get("experience_mode"):
        patch["experience_mode"] = mode

    user_states.patch(user_id, **patch)

    return TurnRoute(
        intent=intent,
        confidence=confidence,
        action=action,
        experience_mode=mode,
        sales_stage=stage,
        topics_covered=topics,
        memory_hits=memory_hits,
        guidance=guidance,
    )


def build_turn_context_block(route: TurnRoute) -> str:
    return (
        "DIALOG_ROUTER (внутренняя схема; не цитируй пользователю):\n"
        f"{route.guidance}\n"
        f"topics_covered={route.topics_covered}\n"
        f"memory_hits={route.memory_hits}\n"
        "Порядок: Intent → Confidence → Memory → FSM branch → ответ."
    )
