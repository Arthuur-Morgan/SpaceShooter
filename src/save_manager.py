import json
import os
import sys
from pathlib import Path


if getattr(sys, 'frozen', False):
    SAVE_PATH = Path(sys.executable).resolve().parent / "save_data.json"
else:
    SAVE_PATH = Path(__file__).resolve().parent.parent / "save_data.json"
DEFAULT_SAVE = {
    "high_score": 0,
    "credits": 0,
    "owned_engines": ["base"],
    "owned_weapons": ["auto_cannon"],
    "equipped_engine": "base",
    "equipped_weapon": "auto_cannon",
    "equipped_shield": None,
    "invincibility_backups": 0,
    "owned_shields": [],
    "music_track": 0,
    # Persisted player config so settings survive restarts.
    "sensitivity": 5,
    "music_volume": 0.5,
    "keybinds": {},
    "difficulty": "medium",
    "encountered_enemies": [],
    "tutorial_completed": False,
    "adaptive_director": {"values": {}, "counts": {}, "total_encounters": 0},
}


def load_save_data():
    """Load the save file, falling back safely if it is missing or malformed."""
    try:
        with SAVE_PATH.open("r", encoding="utf-8") as save_file:
            saved = json.load(save_file)
        if not isinstance(saved, dict):
            raise ValueError("Save data must be a JSON object")
        data = {**DEFAULT_SAVE, **saved}
        data["high_score"] = max(0, int(data.get("high_score", 0)))
        data["credits"] = max(0, int(data.get("credits", 0)))
        data["music_track"] = max(0, int(data.get("music_track", 0)))
        data["invincibility_backups"] = max(0, int(data.get("invincibility_backups", 0)))
        if not isinstance(data.get("adaptive_director"), dict):
            data["adaptive_director"] = DEFAULT_SAVE["adaptive_director"].copy()
        for key, default_items in (("owned_weapons", ["auto_cannon"]), ("owned_engines", ["base"]), ("owned_shields", [])):
            if not isinstance(data.get(key), list):
                data[key] = default_items.copy()
        if not isinstance(data.get("encountered_enemies"), list):
            data["encountered_enemies"] = []
        if "auto_cannon" not in data["owned_weapons"]:
            data["owned_weapons"].append("auto_cannon")
        if "base" not in data["owned_engines"]:
            data["owned_engines"].append("base")
        # Validate persisted settings; fall back to safe defaults.
        data["sensitivity"] = max(2, min(15, int(data.get("sensitivity", 5))))
        data["music_volume"] = max(0.0, min(1.0, float(data.get("music_volume", 0.5))))
        if not isinstance(data.get("keybinds"), dict):
            data["keybinds"] = {}
        if data.get("difficulty") not in ("easy", "medium", "hard"):
            data["difficulty"] = "medium"
        data["tutorial_completed"] = bool(data.get("tutorial_completed", False))
        return data
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return DEFAULT_SAVE.copy()


def write_save_data(data):
    """Atomically save progress so an interrupted write won't corrupt the file."""
    temporary_path = SAVE_PATH.with_suffix(".json.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as save_file:
            json.dump(data, save_file, indent=4)
            save_file.write("\n")
        os.replace(temporary_path, SAVE_PATH)
        return True
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False
