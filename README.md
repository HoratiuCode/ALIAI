# ALIAI

A simple CLI tool to find old/unused files and optionally move selected ones to Trash.

## Welcome Message

When you start the program, it prints:

`Welcome to ALIAI`

## What It Scans by Default

- `~/Documents`
- `~/Pictures`
- `~/Downloads`
- `~/Desktop`
- App bundles in `~/Applications` and `/Applications`

## Requirements

- Python 3
- macOS (uses `~/.Trash` for safe deletion)

## Usage

Run a standard scan:

```bash
python3 aliai.py
```

Show help:

```bash
python3 aliai.py --help
```

Scan files older than 6 months:

```bash
python3 aliai.py --age 6m
```

Scan files older than 1 year and show only first 50:

```bash
python3 aliai.py --age 1y --limit 50
```

Enable interactive deletion:

```bash
python3 aliai.py --delete
```

Skip app bundle scanning:

```bash
python3 aliai.py --no-apps
```

## Landing Page

A minimalist landing page is available at `index.html`.

Open it in a browser to preview the project overview.
