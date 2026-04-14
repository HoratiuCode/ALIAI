# ALIAI

A simple CLI tool to find old files, old folders, and software you have not used for a long time, then optionally move selected items to Trash.

Before results are shown, ALIAI now builds a scan plan and displays a percentage loading bar so you can track progress from `0%` to `100%`.

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

Use `--system-scan` to also inspect:

- `~/Library/Caches`
- `~/Library/Logs`
- `~/Library/Application Support`
- `/Library/Caches`
- `/Library/Logs`
- `/Library/Application Support`

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

Scan old folders too:

```bash
python3 aliai.py --scan-folders --age 1y
```

Run a larger scan across more folders:

```bash
python3 aliai.py --large-scan
```

Scan broader user and system cleanup locations:

```bash
python3 aliai.py --system-scan --time-preset very-long --limit 100
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

Results show `Type` and `Reason` columns so you can quickly see whether each match is a file, folder, or software item.

During scanning, the CLI shows a progress bar with a percentage and the current path being scanned.

For longer scans, you can use:

- `--time-preset standard` for 180 days
- `--time-preset long` for 1 year
- `--time-preset very-long` for 2 years
- `--age 3y` or any custom value when you want a longer exact threshold

Reason labels:

- `old-file` means a regular file that appears old or unused
- `old-folder` means a regular folder that appears old or unused
- `cache-log` means a cache/log/temp-style folder that is often low-value cleanup material
- `review` means the folder name matches a small set of potentially unwanted patterns and should be inspected manually

`review` is not malware detection. It is only a cautious hint to inspect the folder before deleting it.

## Landing Page

A minimalist landing page is available at `index.html`.

Open it in a browser to preview the project overview.
