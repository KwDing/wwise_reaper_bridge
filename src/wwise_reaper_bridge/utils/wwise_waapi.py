# utils/wwise_waapi.py
from __future__ import annotations
import json
from typing import List, Iterator, Optional, Any
from contextlib import contextmanager

from waapi import WaapiClient, CannotConnectToWaapiException

from core.models import SelectedObj
from utils.app_paths import last_selected_txt_path, last_selected_jsonl_path

@contextmanager
def ensure_waapi_client(client: Optional[Any] = None) -> Iterator[Any]:
    """
    Yield a WAAPI client.
    - If `client` is provided, yield it.
    - Otherwise create a temporary WaapiClient and close it on exit.
    """
    if client is not None:
        yield client
        return

    if WaapiClient is None:
        raise ImportError("WaapiClient not available. Install/import the WAAPI client library first.")

    with WaapiClient() as c:
        yield c

def get_selected(filter_types = [], ww_client = None) -> List[dict] | None:
    try:
        with ensure_waapi_client(ww_client) as client:
            selected = client.call(
                "ak.wwise.ui.getSelectedObjects",
                options={"return": ["id", "name", "path", "type"]},
            )
            objs = selected.get("objects", [])
            if filter_types:
                objs = [o for o in objs if o.get("type") in filter_types]
        return objs
    except CannotConnectToWaapiException:
        return None

def get_selected_sfx(ww_client = None) -> List[SelectedObj] | None:
    try:
        with ensure_waapi_client(ww_client) as client:
            selected = client.call(
                "ak.wwise.ui.getSelectedObjects",
                options={"return": ["id", "name", "path", "type"]},
            )
            objs = selected.get("objects", [])
            # SoundSFX only
            sounds = get_selected(["Sound"], client)
            if not sounds:
                return []
            ids = [o["id"] for o in sounds]
            source_map = get_original_sources_by_prop(ids, ww_client=client)
            out = []

            with last_selected_jsonl_path.open("w", encoding="utf-8") as fj,\
                last_selected_txt_path.open("w", encoding="utf-8") as ft:
                for o in sounds:
                    selected_obj = SelectedObj(
                        id=o["id"],
                        name=o["name"],
                        path=o["path"],
                        type=o["type"],
                        source_path=source_map.get(o["id"]))
                    out.append(selected_obj)
                    fj.write(json.dumps(selected_obj.__dict__, ensure_ascii = False)+ "\n")
                    ft.write(f"{selected_obj.path}|{selected_obj.source_path or ''}\n")
            return out
    except CannotConnectToWaapiException:
        return None


def import_audio_to_wwise(import_tasks: List[dict], ww_client = None) -> int:
    """
    import_tasks: list of dicts:
    [ { "objectPath": "...", "audioFile": "..." } ]
    """
    if not import_tasks:
        return 0
    imports = [
        {
            "objectPath": task["objectPath"],
            "audioFile": task["audioFile"],
            "objectType": "Sound",
            "importLanguage": "SFX"
        }
        for task in import_tasks
    ]
    import_payload = {
        "importOperation": "useExisting",
        "imports": imports
    }
    try:
        with ensure_waapi_client(ww_client) as client:
            result = client.call("ak.wwise.core.audio.import", import_payload)
            print(f"import audio results:\n{result}")
            return len(result.get("objects", [])) if isinstance(result, dict) else 0

    except CannotConnectToWaapiException:
        return 0
    except Exception:
        return 0

def get_original_sources_by_prop(props: list[str],
                                 propname: str = "id",
                                 ww_client = None) -> dict[str, str]:
    """
    Returns:
      { propname: originalWavFilePath }
    """
    if not props:
        return {}
    with ensure_waapi_client(ww_client) as client:
        info = client.call("ak.wwise.core.getInfo")
        ww_year = 0
        if isinstance(info, dict):
            ww_year = info.get("version", {}).get("year", 0)
        srcfile_key = "originalFilePath" if ww_year > 2021 else "sound:originalWavFilePath"
        result = client.call(
            "ak.wwise.core.object.get",
            {"from": {propname: props}},
            options={"return": [propname, srcfile_key]},
        )

        out = {}
        for item in result.get("return", []):
            wav = item.get("sound:originalWavFilePath") or item.get("originalFilePath")
            if wav:
                out[item[propname]] = wav

        return out

