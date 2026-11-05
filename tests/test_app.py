from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
import subprocess
import unittest
import sys
from unittest.mock import patch

from cleanup_scanner.app import run
from tests.helpers import Fixture, RecordingWriter


class AppTests(Fixture):
    def invoke(self, *extra):
        return subprocess.run([sys.executable, "-m", "cleanup_scanner", "--config", str(self.config_path), *extra], text=True, capture_output=True, encoding="utf-8")

    def test_cli_clean_repeated_runs_and_unicode(self):
        image = self.file("旅行/é.CR2")
        video = self.file("2024-03 holiday.MP4")
        (self.root / "export").mkdir()
        (self.root / "empty").mkdir()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Analysis complete.", result.stdout)
        self.assertEqual(result.stderr, "")
        files = list(self.output.glob("*.jsonl"))
        self.assertEqual(len(files), 4)
        all_records = [json.loads(line) for path in files for line in path.read_text().splitlines()]
        self.assertIn({"path": str(image.parent), "entry_type": "directory"}, all_records)
        self.assertIn({"path": str(video), "entry_type": "file"}, all_records)
        self.assertEqual(self.invoke().returncode, 0)
        self.assertEqual(len(list(self.output.glob("*.jsonl"))), 8)

    def test_invalid_config_creates_no_output(self):
        text = self.config_path.read_text().replace("'reports'", "'photos/results'")
        self.config_path.write_text(text)
        result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside", result.stderr)
        self.assertFalse((self.root / "results").exists())

    def test_cli_output_failure(self):
        self.output.touch()
        result = self.invoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete with errors", result.stdout)
        self.assertIn("Error:", result.stderr)
        self.assertNotIn("Written:", result.stdout)

    def test_alternative_writer_and_scan_error_reporting(self):
        self.file("a.CR2")
        writer = RecordingWriter()
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = run(self.config, writer=writer)
        self.assertEqual(status, 0)
        self.assertEqual({f.path for f in writer.findings}, {str(self.root)})
        self.assertFalse(self.output.exists())
        with patch("cleanup_scanner.scanner.os.scandir", side_effect=PermissionError("denied")), redirect_stdout(stdout), redirect_stderr(stderr):
            status = run(self.config, writer=RecordingWriter())
        self.assertEqual(status, 1)
        self.assertIn("denied", stderr.getvalue())
        self.assertIn(str(self.root), stderr.getvalue())
        self.assertIn("complete with errors", stdout.getvalue())

    @unittest.skipUnless(os.name != "nt", "POSIX permission fixture")
    def test_subprocess_scan_permission_error(self):
        blocked = self.root / "blocked"
        blocked.mkdir()
        blocked.chmod(0)
        self.addCleanup(lambda: blocked.chmod(0o700))
        if os.access(blocked, os.R_OK | os.X_OK):
            self.skipTest("Current user bypasses directory permissions")
        result = self.invoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(blocked), result.stderr)
        self.assertIn("complete with errors", result.stdout)
        self.assertEqual(len(list(self.output.glob("*.jsonl"))), 4)
