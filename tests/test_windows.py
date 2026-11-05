"""Native Windows checks; symlinks need privileges, junctions normally do not."""

import os
import subprocess
import unittest

from cleanup_scanner.config import ConfigError, load_config
from tests.helpers import Fixture


@unittest.skipUnless(os.name == "nt", "Native Windows path semantics")
class WindowsTests(Fixture):
    def test_case_insensitive_containment(self):
        text = self.config_path.read_text().replace("'reports'", "'PHOTOS/reports'")
        self.config_path.write_text(text)
        with self.assertRaisesRegex(ConfigError, "outside"):
            load_config(self.config_path)

    def test_junction_output_alias(self):
        alias = self.base / "alias"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(self.root)], capture_output=True)
        if result.returncode:
            self.skipTest("Junction creation unavailable")
        self.addCleanup(lambda: alias.rmdir() if alias.exists() else None)
        self.config_path.write_text(self.config_path.read_text().replace("'reports'", "'alias/reports'"))
        with self.assertRaisesRegex(ConfigError, "outside"):
            load_config(self.config_path)
