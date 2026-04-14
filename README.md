# ALIAI

A simple CLI tool to find old files and software you have not used for a long time, then optionally move selected items to Trash.

## Welcome Message

When you start the program, it prints:

`Welcome to ALIAI`

## What It Scans by Default

- `~/Documents`
- `~/Pictures`
- `~/Downloads`
- `~/Desktop`
- Software/app bundles in `~/Applications` and `/Applications`

Use `--large-scan` to also scan:

- `~/Movies`
- `~/Music`
- `~/Public`

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

Scan only software you have not used for a long time:

```bash
python3 aliai.py --software-only --age 1y
```

Run a larger scan across more folders:

```bash
python3 aliai.py --large-scan
```

Use a longer built-in time preset:

```bash
python3 aliai.py --time-preset very-long
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

## Output

Results show a `Type` column so you can quickly see whether each match is a regular file or software.

For longer scans, you can use:

- `--time-preset standard` for 180 days
- `--time-preset long` for 1 year
- `--time-preset very-long` for 2 years
- `--age 3y` or any custom value when you want a longer exact threshold

## Landing Page

A minimalist landing page is available at `index.html`.

Open it in a browser to preview the project overview.
