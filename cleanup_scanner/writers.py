"""JSONL result writer, replaceable without changing traversal or rules."""

from datetime import timezone
import json

from .models import Finding, OutputResult, Problem, RunContext


class JsonlWriter:
    def start_run(self, context: RunContext, categories: list[str]) -> None:
        self.context = context
        self.records: dict[str, dict[str, Finding]] = {category: {} for category in categories}

    def write_finding(self, finding: Finding) -> None:
        self.records[finding.category][finding.path] = finding

    def _write_records(self, stream, records):
        for path in sorted(records):
            # ensure_ascii escapes even undecodable Unix filename bytes losslessly.
            stream.write(json.dumps(records[path].to_dict(), ensure_ascii=True, allow_nan=False) + "\n")

    def finish_run(self) -> OutputResult:
        result = OutputResult()
        output = self.context.output_dir
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            for category in self.records:
                result.errors.append(Problem(str(output / category), str(exc)))
            return result
        timestamp = self.context.started_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%S%fZ")
        suffix = 0
        # Reserve all category names together. If another run races us, release
        # only our reservations and choose a new shared suffix.
        while True:
            token = timestamp + (f"_{suffix}" if suffix else "")
            reserved = []
            failures = []
            collision = False
            for category in self.records:
                path = output / f"{category}_{token}.jsonl"
                try:
                    with path.open("x", encoding="utf-8"):
                        pass
                    reserved.append((category, path))
                except FileExistsError:
                    collision = True
                    break
                except OSError as exc:
                    failures.append(Problem(str(path), str(exc)))
            if not collision:
                result.errors.extend(failures)
                break
            for _, path in reserved:
                try:
                    path.unlink()
                except OSError as exc:
                    result.errors.append(Problem(str(path), f"Could not release output reservation: {exc}"))
            suffix += 1
        for category, path in reserved:
            try:
                with path.open("w", encoding="utf-8", newline="\n") as stream:
                    self._write_records(stream, self.records[category])
                result.paths.append(path)
            except (OSError, ValueError, TypeError) as exc:
                result.errors.append(Problem(str(path), str(exc)))
                try:
                    path.unlink()
                except OSError as cleanup:
                    result.errors.append(Problem(str(path), f"Incomplete output could not be removed: {cleanup}"))
        return result
