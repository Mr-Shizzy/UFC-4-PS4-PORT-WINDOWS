#!/usr/bin/env python3
"""Package prebuilt UFC 4 Windows Native Port into a distributable release ZIP."""
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT.parent / "UFC4Native-ufc4-v0.1.0-windows-x86_64.zip"

INCLUDE_FILES = [
    "UFC4.exe",
    "WebView2Loader.dll",
    "run_game.bat",
    "README.md",
    "LICENSE",
]

INCLUDE_DIRS = [
    "bin",
    "patches",
    "scripts",
    "share",
    "web",
    "tools",
]

EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.obj",
    "*.res",
    "*.pdb",
    "*.log",
    "*.tmp",
]

def should_exclude(path_str):
    for pat in EXCLUDE_PATTERNS:
        if pat.startswith("*.") and path_str.endswith(pat[1:]):
            return True
        if pat in path_str:
            return True
    return False

def build_package():
    print(f"Creating release archive: {OUTPUT_ZIP}")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add root files
        for f in INCLUDE_FILES:
            src = ROOT / f
            if src.exists():
                arcname = f"UFC4Native/{f}"
                print(f"  Adding file: {f}")
                zf.write(src, arcname)

        # Add directories
        for d in INCLUDE_DIRS:
            src_dir = ROOT / d
            if not src_dir.exists():
                continue
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    full_path = Path(root) / file
                    rel_to_root = full_path.relative_to(ROOT)
                    if should_exclude(str(rel_to_root)):
                        continue
                    arcname = f"UFC4Native/{rel_to_root}"
                    zf.write(full_path, arcname)

    size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"Release package ready: {OUTPUT_ZIP} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    build_package()
