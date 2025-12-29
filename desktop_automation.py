import os
import shutil
from pathlib import Path
import argparse
import time
from classifier import classify_file

DESKTOP = Path.home() / "Desktop"
TARGET_FOLDERS = ["University Docs", "Technical Work", "Capstone Work"]


def ensure_target_folders(base: Path = DESKTOP):
    for f in TARGET_FOLDERS:
        (base / f).mkdir(exist_ok=True)


def is_target_file(p: Path, base: Path) -> bool:
    # Only consider top-level files (not inside target folders)
    if p.is_file() and p.parent == base:
        return True
    return False


def move_files(base: Path = DESKTOP, dry_run: bool = False):
    ensure_target_folders(base)
    moved = []
    for p in base.iterdir():
        if not is_target_file(p, base):
            continue
        # skip hidden files
        if p.name.startswith("~") or p.name.startswith('.'):
            continue
        cat = classify_file(str(p))
        dest_dir = base / cat
        dest = dest_dir / p.name
        if dest.exists():
            # if exact file exists, skip
            try:
                if p.samefile(dest):
                    continue
            except Exception:
                pass
            # make unique
            n = 1
            while dest.exists():
                dest = dest_dir / f"{p.stem}_dup{n}{p.suffix}"
                n += 1
        if dry_run:
            print(f"Would move {p} -> {dest}")
        else:
            shutil.move(str(p), str(dest))
            moved.append((p, dest))
            print(f"Moved {p.name} -> {cat}")
    return moved


def run_once(base: Path = DESKTOP, dry_run=False):
    moved = move_files(base, dry_run=dry_run)
    return moved


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Dry run")
    parser.add_argument("--base", type=str, default=str(DESKTOP), help="Base folder to scan (default: Desktop)")
    args = parser.parse_args()
    base = Path(args.base)
    if not base.exists():
        print(f"Base path {base} does not exist")
        raise SystemExit(1)
    print(f"Scanning base: {base} (dry_run={args.dry})")
    run_once(base=base, dry_run=args.dry)
