"""Локальный store сводок: data/summaries/YYYY-MM-DD.json"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SUMMARIES_DIR = DATA_DIR / "summaries"
PROFILE_PATH = DATA_DIR / "nullxes_profile.json"


def get_daily_summary(date: str) -> dict:
    """date: YYYY-MM-DD"""
    path = SUMMARIES_DIR / f"{date}.json"
    if not path.exists():
        return {
            "available": False,
            "date": date,
            "message": "No summary file for this date",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "date": date,
            "message": f"Failed to read summary: {exc}",
        }
    if not payload:
        return {"available": False, "date": date, "message": "Empty summary"}
    return {"available": True, "date": date, "summary": payload}


def get_company_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {
            "available": False,
            "message": "Profile file missing",
        }
    try:
        return {
            "available": True,
            "profile": json.loads(PROFILE_PATH.read_text(encoding="utf-8")),
        }
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "message": str(exc)}
