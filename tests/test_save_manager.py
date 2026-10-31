"""Regression checks for save persistence and legacy save migration."""

import json
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import save_manager


class SaveManagerTests(unittest.TestCase):
    def test_write_creates_user_data_directory(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            save_path = Path(temp_dir) / "nested" / "SpaceShooter" / "save_data.json"
            with patch.object(save_manager, "SAVE_PATH", save_path):
                self.assertTrue(save_manager.write_save_data({"credits": 125}))
                self.assertEqual(json.loads(save_path.read_text(encoding="utf-8"))["credits"], 125)

    def test_legacy_save_is_migrated_without_losing_progress(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            root = Path(temp_dir)
            legacy_path = root / "old-install" / "save_data.json"
            save_path = root / "user-data" / "SpaceShooter" / "save_data.json"
            legacy_path.parent.mkdir()
            legacy_path.write_text(json.dumps({"credits": 420, "tutorial_completed": True}), encoding="utf-8")

            with patch.object(save_manager, "SAVE_PATH", save_path), patch.object(
                save_manager, "LEGACY_SAVE_PATH", legacy_path
            ):
                data = save_manager.load_save_data()

            self.assertEqual(data["credits"], 420)
            self.assertTrue(data["tutorial_completed"])
            self.assertTrue(save_path.exists())
            self.assertTrue(legacy_path.exists())


if __name__ == "__main__":
    unittest.main()

