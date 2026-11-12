import json
import tempfile
import unittest
from pathlib import Path

from coros_unlock.config import Config


class ConfigTests(unittest.TestCase):
    def test_roundtrip(self):
        cfg = Config(device_name="COROS PACE 3", lock_when_away=False, present_after=3)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.json"
            cfg.save(path)
            loaded = Config.load(path)
            self.assertEqual(loaded, cfg)

    def test_unknown_keys_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.json"
            path.write_text(json.dumps({"device_name": "x", "future_key": 1}))
            loaded = Config.load(path)
            self.assertEqual(loaded.device_name, "x")

    def test_missing_file_returns_defaults(self):
        cfg = Config.load("/nonexistent/path/config.json")
        self.assertEqual(cfg, Config())


if __name__ == "__main__":
    unittest.main()
