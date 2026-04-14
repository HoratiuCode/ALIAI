# ALIAI

ALIAI is a macOS cleanup CLI that scans for old or unused files, folders, and software, then lets you review and optionally move selected items to Trash.

## Latest Modifications

- Added a live loading bar with progress from `0%` to `100%`
- Added support for scanning old folders, not only files
- Added software-focused scanning for unused `.app` bundles
- Added `--large-scan` to inspect more user folders
- Added `--system-scan` to inspect cache, log, and application support locations
- Added `Type` and `Reason` columns in the results
- Added longer scan presets with `--time-preset`

## What ALIAI Can Scan

Default scan:

- `~/Documents`
- `~/Pictures`
- `~/Downloads`
- `~/Desktop`
- `~/Applications`
- `/Applications`

Large scan adds:

- `~/Movies`
- `~/Music`
- `~/Public`

System scan adds:

- `~/Library/Caches`
- `~/Library/Logs`
- `~/Library/Application Support`
- `/Library/Caches`
- `/Library/Logs`
- `/Library/Application Support`

## Progress Bar

Before showing results, ALIAI prepares the scan and displays a live loading bar with percentage progress.

Example:

```text
Scanning progress: [##########---------------] 40%
```

For small scans, the progress can move very quickly. For larger scans, it updates while the scan is running.

## Requirements

- Python 3
- macOS

ALIAI uses `~/.Trash` so deleted items are moved to Trash instead of being permanently removed.

## Usage

Standard scan:

```bash
python3 aliai.py
```

Show help:

```bash
python3 aliai.py --help
```

Scan older items:

```bash
python3 aliai.py --age 6m
python3 aliai.py --age 1y --limit 50
python3 aliai.py --age 3y
```

Scan only software:

```bash
python3 aliai.py --software-only --age 1y
```

Include old folders:

```bash
python3 aliai.py --scan-folders --age 1y
```

Run a broader user scan:

```bash
python3 aliai.py --large-scan
```

Run a broader user and system cleanup scan:

```bash
python3 aliai.py --system-scan --scan-folders --time-preset very-long --limit 100
```

Use built-in time presets:

```bash
python3 aliai.py --time-preset standard
python3 aliai.py --time-preset long
python3 aliai.py --time-preset very-long
```

Enable interactive deletion:

```bash
python3 aliai.py --delete
```

Skip software scanning:

```bash
python3 aliai.py --no-apps
```

## Output

ALIAI shows results with:

- `Type`
- `Reason`
- `Last Used`
- `Size`
- `Path`

Possible `Type` values:

- `file`
- `folder`
- `software`

Possible `Reason` values:

- `old-file`
- `old-folder`
- `old-software`
- `cache-log`
- `review`

Reason meaning:

- `old-file` means an old or unused regular file
- `old-folder` means an old or unused regular folder
- `old-software` means an old or unused app bundle
- `cache-log` means a cache, log, or temp-style folder that may be low-value cleanup material
- `review` means the folder name matches a small set of potentially unwanted patterns and should be inspected manually

`review` is not malware detection. It is only a cautious flag for manual review.

## Notes

- `--system-scan` can be slower because it walks larger `Library` locations
- very large folders such as development workspaces, package caches, and downloads may take longer to scan
- the tool is designed to help you review candidates, not to auto-detect malware with certainty

## Landing Page

A simple landing page is available in `index.html`.
