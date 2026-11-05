"""Command-line entry point."""

import argparse
from pathlib import Path
import sys

from .config import ConfigError, load_config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a directory tree without changing it.")
    parser.add_argument("--config", required=True, type=Path, help="TOML configuration file")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    from .app import run
    return run(config)
