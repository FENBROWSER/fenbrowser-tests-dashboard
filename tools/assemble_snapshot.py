#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def load_records(folder: Path):
    records = []
    for item in sorted(folder.glob("lane-*.json")):
        with item.open("r", encoding="utf-8") as handle:
            records.append(json.load(handle))
    return records


def merge_counts(records, key):
    merged = Counter()
    for record in records:
        for name, value in (record.get(key) or {}).items():
            merged[str(name)] += int(value)
    return dict(sorted(merged.items()))


def single_value(records, key):
    values = sorted({record.get(key) for record in records if record.get(key)})
    if len(values) == 1:
        return values[0]
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--expected-lanes", type=int, default=16)
    args = parser.parse_args()

    incoming = Path(args.incoming)
    history = Path(args.history)
    history.mkdir(parents=True, exist_ok=True)

    records = load_records(incoming)
    if not records:
        raise SystemExit("No lane summaries were found.")

    seen_lanes = sorted({int(record["lane"]) for record in records})
    harness_counts = merge_counts(records, "harnessStatusCounts")
    class_counts = merge_counts(records, "resultClassCounts")
    subtest_counts = merge_counts(records, "subtestStatusCounts")

    subtest_total = sum(subtest_counts.values())
    subtest_pass = int(subtest_counts.get("PASS", 0))
    pass_rate = round((subtest_pass / subtest_total) * 100.0, 4) if subtest_total else None

    captured = datetime.now(timezone.utc)
    complete_lanes = sum(1 for record in records if record.get("summaryPresent"))
    unhealthy_lanes = [
        int(record["lane"])
        for record in records
        if (not record.get("summaryPresent"))
        or record.get("timedOut")
        or record.get("stalled")
    ]

    snapshot = {
        "schemaVersion": 1,
        "capturedAtUtc": captured.isoformat(),
        "expectedLanes": args.expected_lanes,
        "observedLanes": len(seen_lanes),
        "lanesWithSummaries": complete_lanes,
        "laneIds": seen_lanes,
        "unhealthyLaneIds": unhealthy_lanes,
        "complete": len(seen_lanes) == args.expected_lanes and not unhealthy_lanes,
        "fenBrowserRevision": single_value(records, "fenBrowserRevision"),
        "wptRevision": single_value(records, "wptRevision"),
        "filesStarted": sum(int(record.get("filesStarted") or 0) for record in records),
        "filesCompleted": sum(int(record.get("filesCompleted") or 0) for record in records),
        "harnessStatusCounts": harness_counts,
        "resultClassCounts": class_counts,
        "subtestStatusCounts": subtest_counts,
        "subtestsPassed": subtest_pass,
        "subtestsTotal": subtest_total,
        "subtestPassRate": pass_rate,
        "unexpectedTestFailures": sum(int(record.get("unexpectedTestFailures") or 0) for record in records),
        "unexpectedSubtestFailures": sum(int(record.get("unexpectedSubtestFailures") or 0) for record in records),
        "durationSecondsSummedAcrossLanes": round(
            sum(float(record.get("durationSeconds") or 0) for record in records), 3
        ),
        "lanes": sorted(records, key=lambda record: int(record["lane"])),
    }

    stamp = captured.strftime("%Y%m%dT%H%M%SZ")
    archive_path = history / f"snapshot-{stamp}.json"
    latest_path = history / "latest.json"

    for destination in (archive_path, latest_path):
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print(archive_path)
    print(latest_path)


if __name__ == "__main__":
    main()
