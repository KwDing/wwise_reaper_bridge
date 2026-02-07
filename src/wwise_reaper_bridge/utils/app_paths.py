# utils/app_paths.py
from __future__ import annotations
import os, sys
from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "WwiseReaperBridge"

def get_asset_path(rel_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore
    else:
        base = Path(__file__).resolve().parents[2]
    return base / rel_path

def _dir_from_env(var: str, fallback: Path) -> Path:
    v = os.environ.get(var)
    if v:
        return Path(v)
    return fallback

def get_appdata_dir() -> Path:
    p = Path(user_data_dir(APP_NAME, appauthor=False, roaming=True))
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_localdata_dir() -> Path:
    p = Path(user_data_dir(APP_NAME, appauthor=False, roaming=False))
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_temp_render_dir():
    p = localdata_dir / "renders"
    p.mkdir(parents=True, exist_ok=True)
    return p

appdata_dir = get_appdata_dir()
localdata_dir = get_localdata_dir()

config_json_path = appdata_dir / "config.json"
last_selected_jsonl_path = localdata_dir / "last_selected.jsonl"
last_selected_txt_path = localdata_dir / "last_selected.txt"

temp_render_dir = get_temp_render_dir()

lua_script_dir = get_asset_path("wwise_reaper_bridge/assets")
reaper_import_lua_path = lua_script_dir / "wrb_open_wwiseobj_in_reaper.lua"
reaper_render_lua_path = lua_script_dir / "wrb_export_tracks.lua"
check_render_format_lua_path = lua_script_dir / "wrb_show_render_format.lua"
