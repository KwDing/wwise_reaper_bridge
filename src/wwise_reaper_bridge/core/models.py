# core/models.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional

Level = Literal["info", "warn", "error"]
DEFAULT_RENDER_FORMAT = "ZXZhdxgAAQ=="
DEFAULT_REAPER_PATH = r"C:\Program Files\REAPER (x64)\reaper.exe"

@dataclass
class Result:
    level: Level
    message: str

@dataclass
class Settings:
    reaper_path: str = DEFAULT_REAPER_PATH
    reaper_render_format: str = DEFAULT_RENDER_FORMAT

@dataclass(frozen=True)
class SelectedObj:
    id: str
    name: str
    path: str
    type: str
    source_path: Optional[str] = None
