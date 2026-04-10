"""Settings persistence service."""
import json
import os
from models.schemas import AppSettings

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")


def load_settings() -> AppSettings:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return AppSettings(**json.load(f))
    except Exception:
        return AppSettings()


def save_settings(s: AppSettings) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(s.model_dump(), f, ensure_ascii=False, indent=2)
