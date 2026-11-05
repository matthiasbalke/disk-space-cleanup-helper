from pathlib import Path
import tempfile
import unittest

from cleanup_scanner.config import load_config
from cleanup_scanner.models import OutputResult

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/scan.toml"


class RecordingWriter:
    def start_run(self, context, categories):
        self.context = context
        self.categories = categories
        self.findings = []

    def write_finding(self, finding):
        self.findings.append(finding)

    def finish_run(self):
        return OutputResult()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "photos"
        self.root.mkdir()
        self.output = self.base / "reports"
        self.config_path = self.base / "scan.toml"
        self.config_path.write_text(EXAMPLE.read_text().replace("'../photos'", "'photos'").replace("'../reports'", "'reports'"), encoding="utf-8")
        self.config = load_config(self.config_path)

    def file(self, path):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        return target
