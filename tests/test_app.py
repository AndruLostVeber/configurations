import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "main.py"


class AppTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        (self.folder / "repo.yml").write_text(
            "A: []\n",
            encoding="utf-8",
        )
        self.settings = {
            "package": "A",
            "repository": "repo.yml",
            "test_mode": True,
            "version": "1.0.0",
            "output_file": "graph.svg",
            "ascii_tree": False,
        }

    def run_stage(self, stage):
        config = self.folder / "config.yml"
        config.write_text(json.dumps(self.settings), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(APP), str(stage), str(config)],
            capture_output=True, text=True, timeout=15,
        )

    def test_prints_settings(self):
        result = self.run_stage(1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), len(self.settings))
        for key in self.settings:
            self.assertIn(key + ":", result.stdout)

    def test_rejects_bad_settings(self):
        errors = {
            "package": "a",
            "repository": "missing.yml",
            "test_mode": "true",
            "version": "latest",
            "output_file": "folder/",
            "ascii_tree": 1,
        }
        for key, value in errors.items():
            with self.subTest(key=key):
                old = self.settings[key]
                self.settings[key] = value
                result = self.run_stage(1)
                self.settings[key] = old
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)
