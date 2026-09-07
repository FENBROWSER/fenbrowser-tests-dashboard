# FenBrowser WPT Dashboard

Automated Web Platform Tests (WPT) runner for FenBrowser that publishes a public GitHub Pages dashboard.

## What this does

- Runs WPT across 16 parallel lanes on Windows GitHub-hosted runners nightly
- Aggregates results into compact historical snapshots stored in this repo
- Generates a static dashboard showing pass rates, failures, and trends over time

## Pipeline

| Workflow | Purpose |
|----------|---------|
| `conformance-grid.yml` | Executes 16 WPT lanes in parallel |
| `nightly-snapshot.yml` | Runs daily at 01:20 UTC, aggregates results, commits snapshot to `history/` |
| `portal-release.yml` | Publishes dashboard to GitHub Pages on `main` branch changes |

## Tools

- `tools/summarize_lane.py` — Reduces raw WPT output to compact metrics
- `tools/assemble_snapshot.py` — Merges lane summaries into a single snapshot
- `tools/render_portal.py` — Generates the static HTML dashboard

## Configuration

- **Tested revision**: Defaults to `rewrite-history` branch of `FENBROWSER/fenbrowser` (override via workflow dispatch)
- **Runners**: Windows (FenBrowser's WPT launcher is Windows-only)
- **Storage**: Keeps lane artifacts for 2 days; long-term history is committed JSON in `history/`

## First run

1. Open **Actions → Record FenBrowser WPT snapshot → Run workflow**
2. Once a snapshot is produced, enable GitHub Pages with **GitHub Actions** as the deployment source