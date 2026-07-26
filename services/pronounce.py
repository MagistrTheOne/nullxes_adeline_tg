"""Rewrite brand names for TTS (avoid letter-by-letter NULLXES)."""

from __future__ import annotations

import re

_BRAND_RU = "Нуллксес"
_BRAND_EN = "Nullexes"
_NULLXES_RE = re.compile(r"NULLXES", re.IGNORECASE)


def for_speech(text: str) -> str:
    if not text:
        return text
    spoken = _BRAND_RU if re.search(r"[а-яё]", text, re.IGNORECASE) else _BRAND_EN
    return _NULLXES_RE.sub(spoken, text)
