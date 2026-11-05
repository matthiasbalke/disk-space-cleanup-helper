from collections import Counter
from contextlib import contextmanager
import os
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch

from cleanup_scanner.config import Rule
from cleanup_scanner.rules import FindingRule
from cleanup_scanner.scanner import scan
from tests.helpers import Fixture, RecordingWriter


class ScannerTests(Fixture):
    def analyze(self, rules=None):
        writer = RecordingWriter()
        rules = rules or [FindingRule(rule) for rule in self.config.rules]
        writer.start_run(None, [rule.category for rule in rules])
        errors = scan(self.root, rules, writer)
        return writer, errors

    def test_all_categories_and_single_pass(self):
        self.file("a.CR2")
        self.file("b.cr2")
        nested = self.file("nested/deep/c.CR2").parent
        export = self.root / "ExPoRt"
        export.mkdir()
        dated = [self.file(name) for name in ["2024 clip.mp4", "2024-03 clip.MP4", "2024-03-21 clip.mp4"]]
        self.file("2024-03-21clip.mp4")
        self.file("clip.mp4")
        self.file("2024 clip.txt")
        real_scandir = os.scandir
        visits = Counter()
        calls = Counter()

        class CountedRule(FindingRule):
            def on_entry(inner, entry):
                calls[(inner.category, str(entry.path))] += 1
                yield from super(CountedRule, inner).on_entry(entry)

        def counted(path):
            visits[str(path)] += 1
            return real_scandir(path)

        with patch("cleanup_scanner.scanner.os.scandir", side_effect=counted):
            writer, errors = self.analyze([CountedRule(r) for r in self.config.rules])
        found = {cat: {f.path for f in writer.findings if f.category == cat} for cat in writer.categories}
        self.assertFalse(errors)
        self.assertEqual(found["directories_with_cr2"], {str(self.root), str(nested)})
        self.assertEqual(found["empty_directories"], {str(export)})
        self.assertEqual(found["export_directories"], {str(export)})
        self.assertEqual(found["dated_mp4_files"], {str(p) for p in dated})
        self.assertTrue(all(n == 1 for n in visits.values()))
        self.assertTrue(all(n == 1 for n in calls.values()))
        self.assertEqual(len(visits), 4)

    def test_empty_root(self):
        writer, errors = self.analyze()
        self.assertFalse(errors)
        self.assertEqual([(f.path, f.entry_type) for f in writer.findings], [(str(self.root), "directory")])

    def test_links_and_broken_links_prevent_empty(self):
        container = self.root / "links"
        container.mkdir()
        try:
            (container / "cycle").symlink_to(self.root, target_is_directory=True)
            (container / "broken.CR2").symlink_to(self.base / "missing")
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        writer, errors = self.analyze()
        self.assertFalse(errors)
        self.assertFalse(writer.findings)

    def test_unreadable_and_interrupted_directory(self):
        (self.root / "bad").mkdir()
        (self.root / "interrupted").mkdir()
        good = self.root / "good"
        good.mkdir()
        real_scandir = os.scandir

        @contextmanager
        def failing(path):
            if Path(path).name == "bad":
                raise PermissionError("denied")
            if Path(path).name == "interrupted":
                def broken():
                    raise OSError("enumeration interrupted")
                    yield
                yield broken()
            else:
                with real_scandir(path) as entries:
                    yield entries

        with patch("cleanup_scanner.scanner.os.scandir", side_effect=failing):
            writer, errors = self.analyze()
        self.assertEqual(len(errors), 2)
        self.assertEqual({f.path for f in writer.findings}, {str(good)})

    def test_entry_error_continues(self):
        good = self.file("ok.CR2")
        class BrokenEntry:
            path = str(good.parent / "vanished")
            def is_symlink(self):
                raise FileNotFoundError("vanished")
        real_scandir = os.scandir
        @contextmanager
        def entries(path):
            with real_scandir(path) as iterator:
                yield iter([BrokenEntry(), *iterator])
        with patch("cleanup_scanner.scanner.os.scandir", side_effect=entries):
            writer, errors = self.analyze()
        self.assertEqual(len(errors), 1)
        self.assertIn(str(self.root), {f.path for f in writer.findings})

    def test_new_rule_without_scanner_changes(self):
        target = self.file("notes.TXT")
        rules = [FindingRule(Rule("text", "file", "file", pattern=re.compile(r"\.txt$", re.I)))]
        writer, errors = self.analyze(rules)
        self.assertFalse(errors)
        self.assertEqual([f.path for f in writer.findings], [str(target)])

    def test_deep_tree_without_python_recursion(self):
        current = self.root
        # Short components keep this portable under normal Windows path limits.
        for _ in range(70):
            current = current / "d"
            current.mkdir()
        with patch("cleanup_scanner.scanner.os.scandir", wraps=os.scandir) as listing:
            writer, errors = self.analyze()
        self.assertFalse(errors)
        self.assertEqual(listing.call_count, 71)
        self.assertEqual([f.path for f in writer.findings], [str(current)])

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior requires Windows")
    def test_windows_junction(self):
        junction = self.root / "linked"
        completed = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.root)], capture_output=True)
        if completed.returncode:
            self.skipTest("Junction creation unavailable")
        self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        writer, errors = self.analyze()
        self.assertFalse(errors)
        self.assertFalse(writer.findings)

    @unittest.skipIf(os.name == "nt", "Windows does not allow these filename characters")
    def test_posix_special_filenames_round_trip(self):
        import json
        from datetime import datetime, timezone
        from cleanup_scanner.models import RunContext
        from cleanup_scanner.writers import JsonlWriter
        image = self.file('旅行/quote"line\nback\\.CR2')
        writer = JsonlWriter()
        writer.start_run(RunContext(datetime.now(timezone.utc), self.output), [r.category for r in self.config.rules])
        self.assertFalse(scan(self.root, [FindingRule(r) for r in self.config.rules], writer))
        result = writer.finish_run()
        self.assertFalse(result.errors)
        paths = [p for p in result.paths if p.name.startswith("directories_with_cr2_")]
        data = paths[0].read_text().splitlines()
        self.assertEqual(len(data), 1)
        self.assertEqual(json.loads(data[0])["path"], str(image.parent))
