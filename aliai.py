#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_FOLDERS = [
    str(Path.home() / "Documents"),
    str(Path.home() / "Pictures"),
    str(Path.home() / "Downloads"),
    str(Path.home() / "Desktop"),
]

LARGE_SCAN_FOLDERS = DEFAULT_FOLDERS + [
    str(Path.home() / "Movies"),
    str(Path.home() / "Music"),
    str(Path.home() / "Public"),
]

DEFAULT_APP_FOLDERS = [str(Path.home() / "Applications"), "/Applications"]
SYSTEM_SCAN_FOLDERS = [
    str(Path.home() / "Library" / "Caches"),
    str(Path.home() / "Library" / "Logs"),
    str(Path.home() / "Library" / "Application Support"),
    "/Library/Caches",
    "/Library/Logs",
    "/Library/Application Support",
]

TIME_PRESETS = {
    "standard": 180,
    "long": 365,
    "very-long": 730,
}

KNOWN_UNWANTED_KEYWORDS = {
    "advancedmaccleaner",
    "adload",
    "crossrider",
    "genieo",
    "installmac",
    "mackeeper",
    "searchprotect",
    "safefinder",
    "spigot",
    "vsearch",
}
LOW_VALUE_DIR_NAMES = {"caches", "logs", "tmp", "temporaryitems"}


@dataclass
class FileCandidate:
    path: Path
    size: int
    atime: float
    mtime: float
    item_type: str = "file"
    reason: str = "old-file"


@dataclass
class ScanProgress:
    total_steps: int
    completed_steps: int = 0
    last_percent: int = -1

    def update(self, current_path: Path) -> None:
        self.completed_steps += 1
        if self.total_steps <= 0:
            return

        percent = min(100, int((self.completed_steps / self.total_steps) * 100))
        if percent == self.last_percent:
            return

        self.last_percent = percent
        filled = percent // 4
        bar = "#" * filled + "-" * (25 - filled)
        short_path = str(current_path)
        if len(short_path) > 48:
            short_path = "..." + short_path[-45:]
        sys.stdout.write(f"\rScanning progress: [{bar}] {percent:>3}%  {short_path:<48}")
        sys.stdout.flush()

    def finish(self) -> None:
        if self.total_steps <= 0:
            return
        if self.last_percent != 100:
            self.last_percent = 100
            bar = "#" * 25
            sys.stdout.write(f"\rScanning progress: [{bar}] 100%  {'Scan complete':<48}")
            sys.stdout.flush()
        print()


def format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def pick_last_used(stat_result: os.stat_result) -> float:
    # "Unused" means "not opened", so use access time only.
    return stat_result.st_atime


def classify_folder_reason(path: Path) -> str:
    lower_name = path.name.lower()
    lower_parts = {part.lower() for part in path.parts}

    if lower_name in LOW_VALUE_DIR_NAMES or lower_parts.intersection(LOW_VALUE_DIR_NAMES):
        return "cache-log"
    if any(keyword in lower_name for keyword in KNOWN_UNWANTED_KEYWORDS):
        return "review"
    return "old-folder"


def count_walk_steps(folder: Path, include_hidden: bool, apps_only: bool = False) -> int:
    if not folder.exists() or not folder.is_dir():
        return 0

    steps = 0
    for root, dirs, files in os.walk(folder):
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if not apps_only:
                files = [f for f in files if not f.startswith('.')]

        steps += 1

        if apps_only:
            dirs[:] = [d for d in dirs if not d.endswith(".app")]

    return steps


def scan_folder(
    folder: Path,
    days_unused: int,
    include_hidden: bool,
    include_folders: bool,
    progress: Optional[ScanProgress] = None,
) -> list[FileCandidate]:
    cutoff = datetime.now().timestamp() - days_unused * 86400
    candidates: list[FileCandidate] = []
    dir_sizes: dict[Path, int] = {}

    if not folder.exists() or not folder.is_dir():
        return candidates

    for root, dirs, files in os.walk(folder, topdown=False):
        root_path = Path(root)

        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]

        if progress is not None:
            progress.update(root_path)

        for filename in files:
            file_path = root_path / filename
            try:
                st = file_path.stat()
            except (PermissionError, FileNotFoundError):
                continue

            last_used = pick_last_used(st)
            if last_used <= cutoff:
                candidates.append(
                    FileCandidate(
                        path=file_path,
                        size=st.st_size,
                        atime=st.st_atime,
                        mtime=st.st_mtime,
                        item_type="file",
                        reason="old-file",
                    )
                )

        total_dir_size = 0
        for filename in files:
            file_path = root_path / filename
            try:
                total_dir_size += file_path.stat().st_size
            except (PermissionError, FileNotFoundError):
                continue

        for dirname in dirs:
            dir_path = root_path / dirname
            if dir_path.suffix == ".app":
                continue
            total_dir_size += dir_sizes.get(dir_path, 0)

        dir_sizes[root_path] = total_dir_size

        if root_path == folder or not include_folders or root_path.suffix == ".app":
            continue

        try:
            st = root_path.stat()
        except (PermissionError, FileNotFoundError):
            continue

        last_used = pick_last_used(st)
        if last_used <= cutoff:
            candidates.append(
                FileCandidate(
                    path=root_path,
                    size=dir_sizes.get(root_path, 0),
                    atime=st.st_atime,
                    mtime=st.st_mtime,
                    item_type="folder",
                    reason=classify_folder_reason(root_path),
                )
            )

    candidates.sort(key=lambda x: x.atime, reverse=False)
    return candidates


def scan_apps_folder(
    folder: Path,
    days_unused: int,
    include_hidden: bool,
    progress: Optional[ScanProgress] = None,
) -> list[FileCandidate]:
    cutoff = datetime.now().timestamp() - days_unused * 86400
    candidates: list[FileCandidate] = []

    if not folder.exists() or not folder.is_dir():
        return candidates

    for root, dirs, _files in os.walk(folder):
        root_path = Path(root)

        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]

        if progress is not None:
            progress.update(root_path)

        app_dirs = [d for d in dirs if d.endswith(".app")]
        for app_name in app_dirs:
            app_path = root_path / app_name
            try:
                st = app_path.stat()
            except (PermissionError, FileNotFoundError):
                continue

            last_used = pick_last_used(st)
            if last_used <= cutoff:
                candidates.append(
                    FileCandidate(
                        path=app_path,
                        size=st.st_size,
                        atime=st.st_atime,
                        mtime=st.st_mtime,
                        item_type="software",
                        reason="old-software",
                    )
                )

        # Do not descend into app bundles after we identify them.
        dirs[:] = [d for d in dirs if not d.endswith(".app")]

    candidates.sort(key=lambda x: x.atime)
    return candidates


def print_results(candidates: list[FileCandidate], limit: int) -> None:
    if not candidates:
        print("No old files, folders, or software found with current settings.")
        return

    print("\nOld/unused items:")
    print("Idx  Type      Reason      Last Used    Size      Path")
    print("---  --------  ----------  ----------   -------   ----")

    shown = candidates[:limit]
    for i, item in enumerate(shown, start=1):
        last_used_ts = item.atime
        last_used = datetime.fromtimestamp(last_used_ts).strftime("%Y-%m-%d")
        print(
            f"{i:<3}  {item.item_type:<8}  {item.reason:<10}  "
            f"{last_used:<10}   {format_size(item.size):<8}  {item.path}"
        )

    total_size = sum(x.size for x in candidates)
    software_count = sum(1 for item in candidates if item.item_type == "software")
    folder_count = sum(1 for item in candidates if item.item_type == "folder")
    file_count = len(candidates) - software_count - folder_count
    print(
        f"\nFound {len(candidates)} items "
        f"({file_count} files, {folder_count} folders, {software_count} software), "
        f"total size: {format_size(total_size)}"
    )
    if len(candidates) > limit:
        print(f"Showing first {limit}. Increase --limit to see more.")


def move_to_trash(path: Path, trash_dir: Path) -> Path:
    trash_dir.mkdir(parents=True, exist_ok=True)
    destination = trash_dir / path.name

    # Avoid name collisions in Trash
    if destination.exists():
        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        while True:
            candidate = trash_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                destination = candidate
                break
            counter += 1

    shutil.move(str(path), str(destination))
    return destination


def parse_indices(input_text: str, max_value: int) -> list[int]:
    selected: set[int] = set()

    for part in input_text.split(','):
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            start_text, end_text = part.split('-', 1)
            start, end = int(start_text), int(end_text)
            if start > end:
                start, end = end, start
            for value in range(start, end + 1):
                if 1 <= value <= max_value:
                    selected.add(value)
        else:
            value = int(part)
            if 1 <= value <= max_value:
                selected.add(value)

    return sorted(selected)


def parse_age_to_days(value: str) -> int:
    text = value.strip().lower()
    if not text:
        raise ValueError("Timeframe cannot be empty.")

    if text[-1].isdigit():
        number = int(text)
        if number < 0:
            raise ValueError("Timeframe must be >= 0.")
        return number

    unit = text[-1]
    amount_text = text[:-1]
    if not amount_text:
        raise ValueError("Missing number before timeframe unit.")

    amount = int(amount_text)
    if amount < 0:
        raise ValueError("Timeframe must be >= 0.")

    multipliers = {
        "d": 1,    # days
        "w": 7,    # weeks
        "m": 30,   # months (approx.)
        "y": 365,  # years (approx.)
    }
    if unit not in multipliers:
        raise ValueError("Invalid unit. Use d, w, m, or y.")

    return amount * multipliers[unit]


def interactive_delete(candidates: list[FileCandidate], limit: int, enable_delete: bool) -> None:
    if not candidates:
        return

    if not enable_delete:
        choice = input("\nFound items. Do you want to delete any? (y/N): ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Skipping deletion.")
            return

    shown = candidates[:limit]
    print("\nDelete options:")
    print("- Enter indexes like: 1,3,7")
    print("- Or ranges like: 2-6")
    print("- Type commands (or help / ?) to show options again")
    print("- Press Enter to show commands")
    print("- Type skip (or q / quit / exit) to skip deletion")

    while True:
        selection = input("Choose items to move to Trash: ").strip()
        if not selection:
            print("\nDelete command formats:")
            print("- Single/multiple: 1,3,7")
            print("- Range: 2-6")
            print("- Skip: skip, q, quit, exit")
            continue

        if selection.lower() in {"skip", "q", "quit", "exit"}:
            print("No files deleted.")
            return

        if selection.lower() in {"commands", "help", "?"}:
            print("\nDelete command formats:")
            print("- Single/multiple: 1,3,7")
            print("- Range: 2-6")
            print("- Skip: skip, q, quit, exit")
            continue
        break

    try:
        indexes = parse_indices(selection, len(shown))
    except ValueError:
        print("Invalid selection format. No files deleted.")
        return

    if not indexes:
        print("No valid indexes selected. No files deleted.")
        return

    print("\nSelected items:")
    for idx in indexes:
        print(f"- {shown[idx - 1].path}")

    confirm = input("Type DELETE to confirm: ").strip()
    if confirm != "DELETE":
        print("Confirmation failed. No files deleted.")
        return

    trash = Path.home() / ".Trash"
    moved_count = 0
    moved_size = 0

    for idx in indexes:
        file_item = shown[idx - 1]
        try:
            move_to_trash(file_item.path, trash)
            moved_count += 1
            moved_size += file_item.size
        except (PermissionError, FileNotFoundError, OSError) as exc:
            print(f"Could not move {file_item.path}: {exc}")

    print(f"\nMoved {moved_count} items to Trash, freed {format_size(moved_size)}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="aliAI: find old/unused files and software in your Documents, Pictures, Downloads, Desktop, and Applications folders."
    )
    parser.add_argument(
        "--folders",
        nargs="+",
        default=DEFAULT_FOLDERS,
        help="Folders to scan (default: ~/Documents ~/Pictures ~/Downloads ~/Desktop)",
    )
    parser.add_argument(
        "--app-folders",
        nargs="+",
        default=DEFAULT_APP_FOLDERS,
        help="App folders to scan for unused .app bundles (default: ~/Applications /Applications)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        help="Find files not used for this many days (default: 180).",
    )
    parser.add_argument(
        "--age",
        default=None,
        help="Timeframe for old files: number of days or value+unit like 30d, 12w, 6m, 2y.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max files shown in output (default: 100)",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and folders",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Enable interactive deletion (move to Trash)",
    )
    parser.add_argument(
        "--no-apps",
        action="store_true",
        help="Skip scanning app bundles",
    )
    parser.add_argument(
        "--software-only",
        action="store_true",
        help="Scan only software (.app bundles) used a long time ago",
    )
    parser.add_argument(
        "--scan-folders",
        action="store_true",
        help="Include old folders in results, not just files and apps",
    )
    parser.add_argument(
        "--large-scan",
        action="store_true",
        help="Scan more folders: adds ~/Movies ~/Music ~/Public to the standard scan",
    )
    parser.add_argument(
        "--system-scan",
        action="store_true",
        help="Also scan user and system cache/log/support folders for stale or review-worthy items",
    )
    parser.add_argument(
        "--time-preset",
        choices=sorted(TIME_PRESETS.keys()),
        default=None,
        help="Use a built-in age preset: standard=180d, long=1y, very-long=2y",
    )
    return parser


def print_startup_commands() -> None:
    print("\nCommands:")
    print("- --folders <paths...>       Folders to scan (default: ~/Documents ~/Pictures ~/Downloads ~/Desktop)")
    print("- --app-folders <paths...>   App folders to scan (default: ~/Applications /Applications)")
    print("- --software-only            Scan only software/app bundles")
    print("- --scan-folders             Include old folders in results")
    print("- --large-scan               Scan more folders (Movies, Music, Public)")
    print("- --system-scan              Scan cache/log/support folders too")
    print("- --time-preset <name>       Use standard, long, or very-long age presets")
    print("- --days <n>                 Age threshold in days (default: 180)")
    print("- --age <n|n[d|w|m|y]>       Flexible age, e.g. 30d, 12w, 6m, 2y")
    print("- --limit <n>                Max files shown (default: 100)")
    print("- --include-hidden           Include hidden files/folders")
    print("- --delete                   Enable interactive deletion to Trash")
    print("- --no-apps                  Skip scanning .app bundles")
    print("- --help                     Show full help and exit")


def build_scan_plan(
    folders_to_scan: list[str],
    app_folders: list[str],
    software_only: bool,
    no_apps: bool,
    include_hidden: bool,
) -> tuple[list[Path], list[Path], int]:
    file_paths = [] if software_only else [Path(folder).expanduser().resolve() for folder in folders_to_scan]
    app_paths = [] if no_apps else [Path(folder).expanduser().resolve() for folder in app_folders]

    total_steps = 0
    for folder_path in file_paths:
        total_steps += count_walk_steps(folder_path, include_hidden, apps_only=False)
    for folder_path in app_paths:
        total_steps += count_walk_steps(folder_path, include_hidden, apps_only=True)

    return file_paths, app_paths, total_steps


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.days < 0:
        parser.error("--days must be >= 0")
    if args.limit <= 0:
        parser.error("--limit must be > 0")
    if args.software_only and args.no_apps:
        parser.error("--software-only cannot be used with --no-apps")

    if args.large_scan and args.folders != DEFAULT_FOLDERS:
        parser.error("--large-scan cannot be used with custom --folders")
    if args.age is not None and args.time_preset is not None:
        parser.error("--age cannot be used with --time-preset")
    if args.days != 180 and args.time_preset is not None:
        parser.error("--days cannot be used with --time-preset")

    try:
        if args.age is not None:
            days_unused = parse_age_to_days(args.age)
        elif args.time_preset is not None:
            days_unused = TIME_PRESETS[args.time_preset]
        else:
            days_unused = args.days
    except ValueError as exc:
        parser.error(f"--age error: {exc}")

    folders_to_scan = list(LARGE_SCAN_FOLDERS if args.large_scan else args.folders)
    if args.system_scan:
        folders_to_scan.extend(SYSTEM_SCAN_FOLDERS)

    print("Welcome to ALIAI")
    print_startup_commands()
    print("Preparing scan plan...")

    file_paths, app_paths, total_steps = build_scan_plan(
        folders_to_scan,
        args.app_folders,
        args.software_only,
        args.no_apps,
        args.include_hidden,
    )
    progress = ScanProgress(total_steps=total_steps)

    all_candidates: list[FileCandidate] = []
    for folder_path in file_paths:
        print(f"Scanning folders/files: {folder_path}")
        all_candidates.extend(
            scan_folder(
                folder_path,
                days_unused,
                args.include_hidden,
                args.scan_folders or args.system_scan,
                progress,
            )
        )

    for folder_path in app_paths:
        print(f"Scanning software: {folder_path}")
        all_candidates.extend(scan_apps_folder(folder_path, days_unused, args.include_hidden, progress))

    progress.finish()

    all_candidates.sort(key=lambda c: c.atime)

    print_results(all_candidates, args.limit)
    interactive_delete(all_candidates, args.limit, args.delete)


if __name__ == "__main__":
    main()
