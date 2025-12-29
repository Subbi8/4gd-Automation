# desktop_automation.py — Line-by-line explanation

This document explains each line and logical block in `desktop_automation.py`. Use it when talking through the local filesystem automation (or when running the Drive-synced folder approach).

---

## Purpose (one-line)
`desktop_automation.py` scans a base folder (default: Desktop), classifies top-level files using `classifier.classify_file`, and moves them into 3 target folders: `University Docs`, `Technical Work`, `Capstone Work`.

---

## File header and imports

```python
import os
import shutil
from pathlib import Path
import argparse
import time
from classifier import classify_file
```

- `shutil` is used for file moves (`shutil.move`).
- `argparse` allows CLI flags (`--base`, `--dry`).
- `time` is imported for historical reasons (not used in the main flow here, left for instrumentation if desired).
- `from classifier import classify_file` imports the main classification function.

---

```python
DESKTOP = Path.home() / "Desktop"
TARGET_FOLDERS = ["University Docs", "Technical Work", "Capstone Work"]
```

- `DESKTOP` is the default base folder scanned.
- `TARGET_FOLDERS` lists the canonical categories and folder names the script will create and use.

---

## ensure_target_folders

```python
def ensure_target_folders(base: Path = DESKTOP):
    for f in TARGET_FOLDERS:
        (base / f).mkdir(exist_ok=True)
```

- Creates the folder structure under the provided `base` path. `exist_ok=True` avoids errors if the folders already exist.

---

## is_target_file

```python
def is_target_file(p: Path, base: Path) -> bool:
    # Only consider top-level files (not inside target folders)
    if p.is_file() and p.parent == base:
        return True
    return False
```

- Ensures the script operates only on *top-level* files in `base` and will not recurse into subfolders. This prevents accidental movement of files already in category folders.

---

## move_files

```python
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
```

Detailed behavior:
- Calls `ensure_target_folders` to create the destinations.
- Iterates `base.iterdir()` to get top-level entries.
- Skips non-target files and hidden files beginning with `~` or `.`.
- Calls `classify_file` to get the category and computes `dest_dir` and `dest` path.
- If the destination file already exists, the script attempts to avoid overwriting: it checks `samefile()` (if possible), else iteratively appends `_dup1`, `_dup2`, etc., until an unused name is found.
- If `dry_run` is True, the script prints planned moves rather than performing them.
- On actual runs, `shutil.move` performs the move and the script logs the operation.

---

## run_once and CLI

```python
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
```

- CLI options allow scanning arbitrary local folders via `--base` and previewing with `--dry`.
- The script checks that `base` exists before running.

---

## Presentation tips
- Explain idempotency: if a file is already in the target folder, it is left untouched.
- Demonstrate `--dry` first during a live demo so the panel can see planned changes without touching files.
- Explain duplicate handling (_dupX suffix generation) to reassure about safety.

---

If you want, I can produce a one-slide summary of `desktop_automation.py` or add small unit tests to assert behavior for duplicates and `--dry` mode.