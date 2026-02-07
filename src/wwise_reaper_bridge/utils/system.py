# utils/system.py
from __future__ import annotations
import os
import subprocess
from pathlib import Path

def file_exists(p: str) -> bool:
    return Path(p).exists()

def open_in_editor(path: Path) -> None:
    os.startfile(str(path))  # noqa: S606

def launch_reaper_new_tab(reaper_exe: str, script_on_start = "") -> None:
    cmd_args = [reaper_exe, "-new"]
    if script_on_start:
        cmd_args.append(script_on_start)
    subprocess.Popen(cmd_args)

def launch_reaper_and_run_lua(reaper_exe_path: str, lua_path: str = "") -> None:
    print(reaper_exe_path, lua_path)
    cmd_args = [reaper_exe_path]
    if lua_path:
        cmd_args.append(lua_path)
    subprocess.Popen(cmd_args)

def is_reaper_running() -> bool:
    """
    Checks if reaper.exe is in the running process list (Windows).
    """
    try:
        # tasklist returns a list of processes. We check if reaper.exe is inside.
        output = subprocess.check_output("tasklist", shell=True).decode()
        return "reaper.exe" in output.lower()
    except Exception:
        # Fallback: assume not running or permission error
        return False