import json
from pathlib import Path

from typing import Optional
from pydantic import BaseModel, Field

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

class YoloSettings(BaseModel):
    conf: float = 0.25

class Settings(BaseModel):
    yolo: YoloSettings = Field(default_factory=YoloSettings)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            file.write(self.model_dump_json(indent=4))

def load_settings():
    if not CONFIG_PATH.exists():
        config = Settings()
        config.save()
        return config

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
            return Settings.model_validate(data)
        except:
            return Settings()

SETTINGS = load_settings()