"""Coordinate a run and report its outcome."""

from datetime import datetime, timezone
import sys

from .models import RunContext
from .rules import FindingRule
from .scanner import scan
from .writers import JsonlWriter


def run(config, *, writer=None, started_at=None) -> int:
    context = RunContext(started_at or datetime.now(timezone.utc), config.output_dir)
    writer = writer if writer is not None else JsonlWriter()
    rules = [FindingRule(rule) for rule in config.rules]
    writer.start_run(context, [rule.category for rule in rules])
    errors = scan(config.root, rules, writer)
    output = writer.finish_run()
    errors.extend(output.errors)
    for problem in errors:
        print(f"Error: {problem}", file=sys.stderr)
    for path in output.paths:
        print(f"Written: {path}")
    print(f"Analysis complete{' with errors' if errors else ''}. {len(output.paths)} result files written.")
    return 1 if errors else 0
