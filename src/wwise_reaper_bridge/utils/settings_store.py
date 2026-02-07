# utils/settings_store.py
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict
from core.models import Settings, SelectedObj
from typing import List
DEFAULT_REAPER_PATH = r"C:\Program Files\REAPER (x64)\reaper.exe"

def load_settings(path: str) -> Settings:
    path = Path(path)

    if not path.exists():
        return Settings()  # return defaults

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Settings(**data)

def save_settings(path: str, settings: Settings):
    path = Path(path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(settings), f, indent=4, ensure_ascii=False)

def write_selected(jsonlpath: Path, objs: List[SelectedObj]) -> None:
    jsonlpath.parent.mkdir(parents=True, exist_ok=True)
    with jsonlpath.open("w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o.__dict__, ensure_ascii=False) + "\n")

def write_selection_manifest(out: List["SelectedObj"], txt_path: Path, jsonl_path: Path) -> None:
    """
    Writes both files in SAME order.
    Only call this if out is non-empty.
    """
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    with txt_path.open("w", encoding="utf-8") as ft, jsonl_path.open("w", encoding="utf-8") as fj:
        for o in out:
            # txt: wwise_path|sourcepath(optional)
            ft.write(f"{o.path}|{o.source_path or ''}\n")

            # jsonl: full record
            fj.write(json.dumps(o.__dict__, ensure_ascii=False) + "\n")


def read_selected(path: Path) -> List[SelectedObj]:
    if not path.exists():
        return []
    out: List[SelectedObj] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            out.append(SelectedObj(**d))
        except Exception:
            # Ignore malformed lines
            pass
    return out
