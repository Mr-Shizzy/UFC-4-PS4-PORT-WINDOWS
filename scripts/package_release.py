#!/usr/bin/env python3
"""Package prebuilt UFC 4 Windows Native Port into a distributable release ZIP."""
import argparse
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_VERSION = "0.1.1"

INCLUDE_FILES = [
    "UFC4.exe",
    "WebView2Loader.dll",
    "run_game.bat",
    "README.md",
    "LICENSE",
]

OPTIONAL_FILES = [
    "out/patches.bin",
    "out/import_names.txt",
    "out/content.bin",
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

def build_package(version=DEFAULT_VERSION):
    output_zip = ROOT.parent / f"UFC4Native-ufc4-v{version}-windows-x86_64.zip"
    print(f"Creating release archive: {output_zip}")
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add root files
        for f in INCLUDE_FILES:
            src = ROOT / f
            if src.exists():
                arcname = f"UFC4Native/{f}"
                print(f"  Adding file: {f}")
                zf.write(src, arcname)

        # Add optional precompiled files (e.g. patches.bin)
        for f in OPTIONAL_FILES:
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

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"Release package ready: {output_zip} ({size_mb:.2f} MB)")
    return output_zip

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package UFC 4 Windows Port Release")
    parser.add_argument("--version", default=DEFAULT_VERSION, help=f"Release version (default: {DEFAULT_VERSION})")
    args = parser.parse_args()
    build_package(args.version)
