"""Reproducible synthetic acceptance/performance check; no benchmark dependencies."""

from collections import Counter
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from cleanup_scanner.app import run
from cleanup_scanner.config import load_config


def main():
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        root = base / "photos"
        root.mkdir()
        for i in range(1000):
            directory = root / str(i)
            directory.mkdir()
            (directory / "export").mkdir()
            for j in range(10):
                (directory / f"{j}.CR2").touch()
            (directory / "2024-01-01 clip.MP4").touch()
        config_path = base / "scan.toml"
        example = Path(__file__).resolve().parents[1] / "examples/scan.toml"
        config_path.write_text(example.read_text().replace("'../photos'", "'photos'").replace("'../reports'", "'reports'"))
        config = load_config(config_path)
        original = os.scandir
        visits = Counter()
        def listing(path):
            visits[str(path)] += 1
            return original(path)
        started = time.perf_counter()
        with patch("cleanup_scanner.scanner.os.scandir", side_effect=listing), redirect_stdout(io.StringIO()):
            assert run(config) == 0
        elapsed = time.perf_counter() - started
        assert len(visits) == 2001 and all(n == 1 for n in visits.values())
        for category in [r.category for r in config.rules]:
            files = list(config.output_dir.glob(f"{category}_*.jsonl"))
            assert len(files) == 1
            records = [json.loads(line) for line in files[0].read_text().splitlines()]
            paths = [r["path"] for r in records]
            assert len(paths) == 1000 and paths == sorted(set(paths))
        print(f"2,001 directories; 11,000 files; 4,000 findings; one enumeration per directory; {elapsed:.3f}s analysis and output")


if __name__ == "__main__":
    main()
