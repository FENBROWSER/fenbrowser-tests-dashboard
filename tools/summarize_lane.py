#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def scan_subtests(raw_path: Path):
    counts = Counter()
    if not raw_path.exists():
        return counts
    with raw_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("action") == "test_status":
                status = str(event.get("status") or "UNKNOWN")
                counts[status] += 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--lane", required=True, type=int)
    parser.add_argument("--engine-exit", default=0, type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_dir = Path(args.source)
    summary_path = source_dir / "wpt.summary.json"
    raw_path = source_dir / "wpt.raw.json"

    summary = read_json(summary_path) if summary_path.exists() else {}
    subtests = scan_subtests(raw_path)

    record = {
        "schemaVersion": 1,
        "lane": args.lane,
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "summaryPresent": bool(summary),
        "engineProcessExit": args.engine_exit,
        "fenBrowserRevision": summary.get("FenBrowserRevision"),
        "wptRevision": summary.get("WptRevision"),
        "startedAtUtc": summary.get("StartedAtUtc"),
        "finishedAtUtc": summary.get("FinishedAtUtc"),
        "durationSeconds": summary.get("DurationSeconds"),
        "filesStarted": int(summary.get("TestStart") or 0),
        "filesCompleted": int(summary.get("TestEnd") or 0),
        "harnessStatusCounts": summary.get("StatusCounts") or {},
        "resultClassCounts": summary.get("ResultClassCounts") or {},
        "subtestStatusCounts": dict(sorted(subtests.items())),
        "unexpectedTestFailures": int(summary.get("UnexpectedTestFailures") or 0),
        "unexpectedSubtestFailures": int(summary.get("UnexpectedSubtestFailures") or 0),
        "timedOut": bool(summary.get("TimedOut") or False),
        "stalled": bool(summary.get("Stalled") or False),
        "failurePhase": summary.get("FailurePhase"),
        "infrastructureResultClass": summary.get("InfrastructureResultClass"),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
