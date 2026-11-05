from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import patch

from cleanup_scanner.models import Finding, RunContext
from cleanup_scanner.writers import JsonlWriter
from tests.helpers import Fixture


class WriterTests(Fixture):
    def writer(self, categories=("files", "empty")):
        writer = JsonlWriter()
        writer.start_run(RunContext(datetime(2026, 11, 5, 14, 30, tzinfo=timezone.utc), self.output), list(categories))
        return writer

    def test_sort_deduplicate_metadata_and_special_characters(self):
        writer = self.writer()
        names = ["z", "A", "a", 'héllo "quote"\\newline\n.mp4']
        for name in names + ["a"]:
            writer.write_finding(Finding("files", str(self.root / name), "file", {"size_bytes": 42, "size_scope": "recursive", "complete": False}))
        result = writer.finish_run()
        self.assertFalse(result.errors)
        self.assertEqual(len(result.paths), 2)
        data = result.paths[0].read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in data]
        self.assertEqual([r["path"] for r in records], sorted(str(self.root / name) for name in names))
        self.assertTrue(all(r["size_bytes"] == 42 and r["complete"] is False for r in records))
        self.assertEqual(result.paths[1].read_bytes(), b"")
        self.assertTrue(all("2026-11-05T143000000000Z" in path.name for path in result.paths))

    def test_reserved_fields_and_invalid_record(self):
        for metadata in [{"path": "oops"}, {"entry_type": "oops"}]:
            with self.assertRaises(ValueError):
                Finding("files", str(self.root), "directory", metadata)
        with self.assertRaises(ValueError):
            Finding("files", "relative", "file")

    def test_collision_preserves_previous_results(self):
        first = self.writer().finish_run()
        second = self.writer().finish_run()
        self.assertTrue(all(path.exists() for path in first.paths + second.paths))
        self.assertTrue(all("_1.jsonl" in p.name for p in second.paths))
        self.assertEqual(len(list(self.output.iterdir())), 4)

    def test_late_collision_releases_reservations(self):
        self.output.mkdir()
        existing = self.output / "empty_2026-11-05T143000000000Z.jsonl"
        existing.write_text("keep")
        result = self.writer().finish_run()
        self.assertEqual(existing.read_text(), "keep")
        self.assertEqual(len(list(self.output.iterdir())), 3)
        self.assertTrue(all("_1.jsonl" in path.name for path in result.paths))

    def test_category_write_failure_isolated_and_partial_removed(self):
        writer = self.writer()
        real_write = writer._write_records
        calls = 0
        def fail_once(stream, records):
            nonlocal calls
            calls += 1
            if calls == 1:
                stream.write("partial")
                raise OSError("disk error")
            real_write(stream, records)
        with patch.object(writer, "_write_records", side_effect=fail_once):
            result = writer.finish_run()
        self.assertEqual(len(result.paths), 1)
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(result.paths[0].name.startswith("empty_"))
        self.assertEqual(list(self.output.iterdir()), result.paths)

    def test_category_open_failure_isolated(self):
        original = Path.open
        def fail(path, *args, **kwargs):
            if path.name.startswith("files_"):
                raise PermissionError("denied")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", fail):
            result = self.writer().finish_run()
        self.assertEqual(len(result.paths), 1)
        self.assertEqual(len(result.errors), 1)

    def test_output_creation_failure(self):
        self.output.touch()
        result = self.writer().finish_run()
        self.assertFalse(result.paths)
        self.assertEqual(len(result.errors), 2)
