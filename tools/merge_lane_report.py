#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def load_records(folder: Path):
    records = []
    for path in sorted(folder.glob("lane-*.json")):
        with path.open("r", encoding="utf-8") as handle:
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
    return values[0] if len(values) == 1 else values


def build_report(records, expected_lanes, run_id):
    lanes = sorted(int(record["lane"]) for record in records)
    files_started = sum(int(record.get("filesStarted") or 0) for record in records)
    files_completed = sum(int(record.get("filesCompleted") or 0) for record in records)
    subtest_counts = merge_counts(records, "subtestStatusCounts")
    subtests_total = sum(subtest_counts.values())
    subtests_passed = int(subtest_counts.get("PASS", 0))
    unhealthy = [
        int(record["lane"])
        for record in records
        if (not record.get("summaryPresent"))
        or int(record.get("engineProcessExit") or 0) != 0
        or record.get("failurePhase")
        or record.get("infrastructureResultClass")
        or record.get("timedOut")
        or record.get("stalled")
    ]
    return {
        "schemaVersion": 1,
        "runId": str(run_id),
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "expectedLanes": expected_lanes,
        "observedLanes": len(lanes),
        "laneIds": lanes,
        "unhealthyLaneIds": unhealthy,
        "complete": len(lanes) == expected_lanes and not unhealthy,
        "fenBrowserRevision": single_value(records, "fenBrowserRevision"),
        "wptRevision": single_value(records, "wptRevision"),
        "filesStarted": files_started,
        "filesCompleted": files_completed,
        "harnessStatusCounts": merge_counts(records, "harnessStatusCounts"),
        "resultClassCounts": merge_counts(records, "resultClassCounts"),
        "subtestStatusCounts": subtest_counts,
        "subtestsPassed": subtests_passed,
        "subtestsTotal": subtests_total,
        "subtestPassRate": round(subtests_passed / subtests_total * 100, 4) if subtests_total else None,
        "unexpectedTestFailures": sum(int(record.get("unexpectedTestFailures") or 0) for record in records),
        "unexpectedSubtestFailures": sum(int(record.get("unexpectedSubtestFailures") or 0) for record in records),
        "engineExitCodes": dict(sorted(Counter(str(record.get("engineProcessExit", 0)) for record in records).items())),
        "lanes": sorted(records, key=lambda record: int(record["lane"])),
    }


def render_markdown(report):
    status = "PASS" if report["complete"] else "STARTUP/INFRASTRUCTURE FAILURE"
    unhealthy = ", ".join(str(lane) for lane in report["unhealthyLaneIds"]) or "none"
    return "\n".join(
        [
            f"# FenBrowser WPT Run {report['runId']}",
            "",
            f"**Status:** `{status}`",
            f"**Lanes:** {report['observedLanes']}/{report['expectedLanes']}",
            f"**Unhealthy lanes:** {unhealthy}",
            f"**Files:** {report['filesCompleted']} completed / {report['filesStarted']} started",
            f"**Subtests:** {report['subtestsPassed']}/{report['subtestsTotal']} passed",
            f"**Unexpected test failures:** {report['unexpectedTestFailures']}",
            f"**Unexpected subtest failures:** {report['unexpectedSubtestFailures']}",
            "",
            "| Lane | Exit | Files | Failure phase | Infrastructure |",
            "| ---: | ---: | ---: | --- | --- |",
            *[
                f"| {record['lane']} | {record.get('engineProcessExit', 0)} | "
                f"{record.get('filesCompleted', 0)}/{record.get('filesStarted', 0)} | "
                f"{record.get('failurePhase') or ''} | {record.get('infrastructureResultClass') or ''} |"
                for record in report["lanes"]
            ],
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", required=True, type=Path)
    parser.add_argument("--diagnostics", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--expected-lanes", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    records = load_records(args.incoming)
    if not records:
        raise SystemExit("No lane summaries were found.")

    report = build_report(records, args.expected_lanes, args.run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "run-report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (args.output_dir / "run-report.md").write_text(render_markdown(report), encoding="utf-8")

    diagnostics = sorted(args.diagnostics.glob("**/*"))
    diagnostics_root = args.output_dir / "diagnostics"
    for path in diagnostics:
        if path.is_file():
            relative = path.relative_to(args.diagnostics)
            destination = diagnostics_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
