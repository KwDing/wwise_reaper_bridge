# core/bridge_logic.py
from __future__ import annotations
import time

from core.models import Result
from utils.system import file_exists, open_in_editor, is_reaper_running, launch_reaper_and_run_lua
from utils.wwise_waapi import get_selected_sfx, import_audio_to_wwise, get_original_sources_by_prop
from utils.settings_store import load_settings, read_selected
from utils.app_paths import (
    config_json_path,
    reaper_import_lua_path,
    reaper_render_lua_path,
    check_render_format_lua_path,
    temp_render_dir
)


def open_in_reaper(config_path, last_path, ui) -> Result:
    settings = load_settings(config_path)
    if not file_exists(settings.reaper_path):
        return Result("error", "reaper.exe not found!")

    selection = get_selected_sfx()
    if selection is None:
        ui.show_error("Error", "Could not connect to Wwise. Is it running?")
        return Result("error", "WAAPI connection failed")

    if not selection:
        last = read_selected(last_path)
        if not last:
            ui.show_info("Error", "No objects selected and no history found.")
            return Result("warn", "No selection and no history")

        choice = ui.ask_yes_no(
            "No selection",
            "No object selected. Open last selection file for modification?",
        )
        if choice:
            open_in_editor(last_path)

    launch_reaper_and_run_lua(settings.reaper_path, reaper_import_lua_path)
    return Result("info", f"Opening REAPER. Logged {len(selection)} item(s).")

def modify_source(config_path, last_path, ui) -> Result:
    # Check if REAPER is running
    if not is_reaper_running():
        ui.show_error("Error", "REAPER is not running.\nPlease open REAPER and the project first.")
        return Result("error", "REAPER not running")

    # Check History
    if not last_path.exists():
        ui.show_error("Error", "No history file found. Use 'Open in REAPER' first.")
        return Result("error", "No history found")

    objs = read_selected(last_path)
    if not objs:
        return Result("warn", "History is empty")

    # Validate Reaper Path
    settings = load_settings(config_path)
    if not file_exists(settings.reaper_path):
        return Result("error", "reaper.exe not found!")

    temp_render_dir.mkdir(parents=True, exist_ok=True)

    for item in temp_render_dir.iterdir():
        if item.is_file():
            try:
                item.unlink(missing_ok=True)
            except OSError:
                print(f"Warning: Could not delete {item}")


    launch_reaper_and_run_lua(settings.reaper_path, reaper_render_lua_path)


    # Query Wwise details BY PATH (not by id)
    obj_paths = [o.path for o in objs if o.path]
    wwise_details = get_original_sources_by_prop(obj_paths,"path", None)
    print(f"details:{wwise_details}")

    success_flag = temp_render_dir / "success.flag"
    timeout_seconds = 60 * (len(obj_paths) + 1)
    start_time = time.time()

    # Poll for the flag
    while not success_flag.exists():
        if time.time() - start_time > timeout_seconds:
            return Result("error", "Timeout: Reaper script did not finish in time.")
        time.sleep(0.2)

    # --- Mapping Phase ---
    waapi_tasks = []

    for obj in objs:
        # Logic: If <name>.wav exists, we prepare it for import.
        # This assumes the Reaper script names files exactly as `obj.name`.
        expected_wav = temp_render_dir / f"{obj.name}.wav"

        if expected_wav.exists():
            waapi_tasks.append({
                "objectPath": obj.path,
                "audioFile": str(expected_wav.resolve())
            })

    # Optional: Delete flag immediately after detection
    try:
        success_flag.unlink(missing_ok=True)
    except OSError:
        pass

    if not waapi_tasks:
        return Result("warn", "Reaper finished, but no matching WAV files were found for selected objects.")
    print(f"tasks:{waapi_tasks}")
    # Import to Wwise
    success_count = import_audio_to_wwise(waapi_tasks)

    return Result("info", f"Sync Complete. Imported {success_count}/{len(waapi_tasks)} files.")

def check_render_format(ui):
    settings = load_settings(config_json_path)
    # 1) Check REAPER running
    if not is_reaper_running():
        ui.show_error(
            "Error",
            "REAPER is not running.\nPlease open REAPER and the project first."
        )
        return Result("error", "REAPER not running")

    launch_reaper_and_run_lua(settings.reaper_path, check_render_format_lua_path)
    return Result("info", f"Show repear config string in Reaper Console.")