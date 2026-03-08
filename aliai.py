#!/usr/bin/env python3
import argparse
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FileCandidate:
    path: Path
    size: int
    atime: float
    mtime: float


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


def scan_folder(folder: Path, days_unused: int, include_hidden: bool) -> list[FileCandidate]:
    cutoff = datetime.now().timestamp() - days_unused * 86400
    candidates: list[FileCandidate] = []

    if not folder.exists() or not folder.is_dir():
        return candidates

    for root, dirs, files in os.walk(folder):
        root_path = Path(root)

        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]

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
                    )
                )

    candidates.sort(key=lambda x: x.atime, reverse=False)
    return candidates


def scan_apps_folder(folder: Path, days_unused: int, include_hidden: bool) -> list[FileCandidate]:
    cutoff = datetime.now().timestamp() - days_unused * 86400
    candidates: list[FileCandidate] = []

    if not folder.exists() or not folder.is_dir():
        return candidates

    for root, dirs, _files in os.walk(folder):
        root_path = Path(root)

        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]

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
                    )
                )

        # Do not descend into app bundles after we identify them.
        dirs[:] = [d for d in dirs if not d.endswith(".app")]

    candidates.sort(key=lambda x: x.atime)
    return candidates


def print_results(candidates: list[FileCandidate], limit: int) -> None:
    if not candidates:
        print("No old files found with current settings.")
        return

    print("\nOld/unused files:")
    print("Idx  Last Used    Size      File")
    print("---  ----------   -------   ----")

    shown = candidates[:limit]
    for i, item in enumerate(shown, start=1):
        last_used_ts = item.atime
        last_used = datetime.fromtimestamp(last_used_ts).strftime("%Y-%m-%d")
        print(f"{i:<3}  {last_used:<10}   {format_size(item.size):<8}  {item.path}")

    total_size = sum(x.size for x in candidates)
    print(f"\nFound {len(candidates)} files, total size: {format_size(total_size)}")
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
        choice = input("\nFound files. Do you want to delete any? (y/N): ").strip().lower()
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
        selection = input("Choose files to move to Trash: ").strip()
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

    print("\nSelected files:")
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

    print(f"\nMoved {moved_count} files to Trash, freed {format_size(moved_size)}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="aliAI: find old/unused files in your Documents, Pictures, Downloads, and Desktop folders."
    )
    parser.add_argument(
        "--folders",
        nargs="+",
        default=[str(Path.home() / "Documents"), str(Path.home() / "Pictures"), str(Path.home() / "Downloads"), str(Path.home() / "Desktop")],
        help="Folders to scan (default: ~/Documents ~/Pictures ~/Downloads ~/Desktop)",
    )
    parser.add_argument(
        "--app-folders",
        nargs="+",
        default=[str(Path.home() / "Applications"), "/Applications"],
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
    return parser


def print_startup_commands() -> None:
    print("\nCommands:")
    print("- --folders <paths...>       Folders to scan (default: ~/Documents ~/Pictures ~/Downloads ~/Desktop)")
    print("- --app-folders <paths...>   App folders to scan (default: ~/Applications /Applications)")
    print("- --days <n>                 Age threshold in days (default: 180)")
    print("- --age <n|n[d|w|m|y]>       Flexible age, e.g. 30d, 12w, 6m, 2y")
    print("- --limit <n>                Max files shown (default: 100)")
    print("- --include-hidden           Include hidden files/folders")
    print("- --delete                   Enable interactive deletion to Trash")
    print("- --no-apps                  Skip scanning .app bundles")
    print("- --help                     Show full help and exit")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    print("Welcome to ALIAI")

    if args.days < 0:
        parser.error("--days must be >= 0")
    if args.limit <= 0:
        parser.error("--limit must be > 0")

    try:
        days_unused = parse_age_to_days(args.age) if args.age is not None else args.days
    except ValueError as exc:
        parser.error(f"--age error: {exc}")

    print_startup_commands()

    all_candidates: list[FileCandidate] = []
    for folder in args.folders:
        folder_path = Path(folder).expanduser().resolve()
        print(f"Scanning: {folder_path}")
        all_candidates.extend(scan_folder(folder_path, days_unused, args.include_hidden))

    if not args.no_apps:
        for folder in args.app_folders:
            folder_path = Path(folder).expanduser().resolve()
            print(f"Scanning apps: {folder_path}")
            all_candidates.extend(scan_apps_folder(folder_path, days_unused, args.include_hidden))

    all_candidates.sort(key=lambda c: c.atime)

    print_results(all_candidates, args.limit)
    interactive_delete(all_candidates, args.limit, args.delete)


if __name__ == "__main__":
    main()
