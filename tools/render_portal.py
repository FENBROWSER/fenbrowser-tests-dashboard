#!/usr/bin/env python3
import argparse
import html
import json
from pathlib import Path


def load_history(folder: Path):
    runs = []
    for item in folder.glob("snapshot-*.json"):
        try:
            with item.open("r", encoding="utf-8") as handle:
                runs.append(json.load(handle))
        except (OSError, json.JSONDecodeError):
            continue
    runs.sort(key=lambda entry: entry.get("capturedAtUtc") or "", reverse=True)
    return runs


def short_rev(value):
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, list):
        return ", ".join(str(part)[:10] for part in value)
    return "unknown"


def pct(value):
    return "n/a" if value is None else f"{float(value):.2f}%"


def count_table(title, values):
    rows = "".join(
        f"<tr><td>{html.escape(str(name))}</td><td>{int(count):,}</td></tr>"
        for name, count in sorted((values or {}).items())
    )
    if not rows:
        rows = "<tr><td colspan='2'>No data</td></tr>"
    return (
        f"<section class='panel'><h2>{html.escape(title)}</h2>"
        "<table><thead><tr><th>Status</th><th>Count</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runs = load_history(Path(args.history))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    latest = runs[0] if runs else {}
    health = "Complete" if latest.get("complete") else "Partial / not yet available"

    recent_rows = []
    for run in runs[:30]:
        recent_rows.append(
            "<tr>"
            f"<td>{html.escape(str(run.get('capturedAtUtc', '')))}</td>"
            f"<td><code>{html.escape(short_rev(run.get('fenBrowserRevision')))}</code></td>"
            f"<td>{int(run.get('filesCompleted') or 0):,} / {int(run.get('filesStarted') or 0):,}</td>"
            f"<td>{int(run.get('subtestsPassed') or 0):,} / {int(run.get('subtestsTotal') or 0):,}</td>"
            f"<td>{html.escape(pct(run.get('subtestPassRate')))}</td>"
            f"<td>{int(run.get('unexpectedTestFailures') or 0):,}</td>"
            f"<td>{int(run.get('observedLanes') or 0)} / {int(run.get('expectedLanes') or 0)}</td>"
            "</tr>"
        )
    history_rows = "".join(recent_rows) or "<tr><td colspan='7'>No WPT snapshots have been recorded yet.</td></tr>"

    status_sections = (
        count_table("Harness outcomes", latest.get("harnessStatusCounts"))
        + count_table("Subtest outcomes", latest.get("subtestStatusCounts"))
        + count_table("Result classes", latest.get("resultClassCounts"))
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FenBrowser WPT Dashboard</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ margin: 0; background: #0b1020; color: #e6edf7; }}
main {{ width: min(1180px, 92vw); margin: 0 auto; padding: 48px 0 72px; }}
h1 {{ margin: 0 0 8px; font-size: clamp(2rem, 5vw, 3.5rem); }}
h2 {{ margin-top: 0; font-size: 1.05rem; }}
p {{ color: #9fb0c6; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 28px 0; }}
.card, .panel {{ background: #121a2d; border: 1px solid #26324a; border-radius: 14px; padding: 18px; }}
.card strong {{ display: block; font-size: 1.65rem; margin-top: 8px; }}
.label {{ color: #90a2ba; font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
th, td {{ text-align: left; border-bottom: 1px solid #26324a; padding: 10px 8px; vertical-align: top; }}
th {{ color: #a9bad0; font-weight: 600; }}
code {{ color: #b9d7ff; }}
.good {{ color: #8ee6a8; }}
.warn {{ color: #ffd280; }}
.scroll {{ overflow-x: auto; }}
footer {{ margin-top: 28px; color: #71849d; font-size: .85rem; }}
</style>
</head>
<body>
<main>
  <h1>FenBrowser WPT Dashboard</h1>
  <p>Automated Web Platform Tests executed against FenBrowser with public GitHub-hosted runners.</p>

  <div class="cards">
    <div class="card"><span class="label">Run state</span><strong class="{'good' if latest.get('complete') else 'warn'}">{html.escape(health)}</strong></div>
    <div class="card"><span class="label">Subtest pass rate</span><strong>{html.escape(pct(latest.get('subtestPassRate')))}</strong></div>
    <div class="card"><span class="label">Subtests</span><strong>{int(latest.get('subtestsPassed') or 0):,} / {int(latest.get('subtestsTotal') or 0):,}</strong></div>
    <div class="card"><span class="label">Test files completed</span><strong>{int(latest.get('filesCompleted') or 0):,}</strong></div>
    <div class="card"><span class="label">Unexpected test failures</span><strong>{int(latest.get('unexpectedTestFailures') or 0):,}</strong></div>
    <div class="card"><span class="label">FenBrowser revision</span><strong><code>{html.escape(short_rev(latest.get('fenBrowserRevision')))}</code></strong></div>
  </div>

  <div class="grid">{status_sections}</div>

  <section class="panel" style="margin-top:14px">
    <h2>Recent runs</h2>
    <div class="scroll">
      <table>
        <thead><tr><th>Captured (UTC)</th><th>FenBrowser</th><th>Files</th><th>Subtests</th><th>Pass rate</th><th>Unexpected tests</th><th>Lanes</th></tr></thead>
        <tbody>{history_rows}</tbody>
      </table>
    </div>
  </section>

  <footer>Latest WPT revision: <code>{html.escape(short_rev(latest.get('wptRevision')))}</code></footer>
</main>
</body>
</html>
"""
    (output / "index.html").write_text(document, encoding="utf-8")


if __name__ == "__main__":
    main()
