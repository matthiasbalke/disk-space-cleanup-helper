from pathlib import Path
import tempfile
import unittest

from cleanup_scanner.config import ConfigError, load_config

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/scan.toml"


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / "photos").mkdir()
        self.path = self.base / "scan.toml"
        self.text = EXAMPLE.read_text().replace("'../photos'", "'photos'").replace("'../reports'", "'reports'")

    def load(self, text=None):
        self.path.write_text(self.text if text is None else text, encoding="utf-8")
        return load_config(self.path)

    def test_example_and_relative_paths(self):
        cfg = self.load()
        self.assertEqual(cfg.root, (self.base / "photos").resolve())
        self.assertEqual(len(cfg.rules), 4)
        self.assertTrue(cfg.rules[-1].pattern.search("2024-03-21 clip.MP4"))
        self.assertFalse(cfg.output_dir.exists())

    def test_containment(self):
        for output in ["photos", "photos/reports"]:
            with self.subTest(output=output), self.assertRaisesRegex(ConfigError, "outside"):
                self.load(self.text.replace("'reports'", repr(output)))
        self.assertEqual(self.load(self.text.replace("'reports'", "'photos-more'")).output_dir.name, "photos-more")

    def test_missing_and_file_root(self):
        for root in ["missing", "scan.toml"]:
            with self.subTest(root=root), self.assertRaises(ConfigError):
                self.load(self.text.replace("'photos'", repr(root)))

    def test_invalid_rules(self):
        cases = [
            self.text.replace("'^\\d{4}(?:-\\d{2}(?:-\\d{2})?)? '", "'['"),
            self.text.replace("rules.dated_mp4_files", 'rules."bad/name"'),
            self.text.replace("kind = 'file'", "kind = 'unknown'"),
            self.text.replace("target = 'parent'", "target = 'directory'"),
            self.text.replace("output_format = 'jsonl'", "output_format = 'sqlite'"),
            self.text + "\nunknown = true\n",
            self.text + "\n[rules.directories_with_cr2]\n",
            self.text.replace("extension = 'cr2'", "extension = 42"),
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ConfigError):
                self.load(text)
        self.assertFalse((self.base / "reports").exists())

    def test_link_aliases(self):
        alias = self.base / "alias"
        try:
            alias.symlink_to(self.base / "photos", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(ConfigError, "outside"):
            self.load(self.text.replace("'reports'", "'alias/new'"))
        with self.assertRaisesRegex(ConfigError, "link"):
            self.load(self.text.replace("'photos'", "'alias'"))

    def test_case_colliding_categories_rejected(self):
        with self.assertRaisesRegex(ConfigError, "unique ignoring case"):
            self.load(self.text + "\n[rules.DIRECTORIES_WITH_CR2]\nkind = 'empty_directory'\ntarget = 'directory'\n")
