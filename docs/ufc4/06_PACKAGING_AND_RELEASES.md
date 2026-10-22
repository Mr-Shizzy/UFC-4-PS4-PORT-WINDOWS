# 06. Packaging & Release Workflow

This project adheres to professional open-source standards by strictly separating **source code** from **distribution binaries**.

---

## 1. Git Repository (Pure Source Code)
The Git repository contains only source code, build scripts, web assets, and documentation.

The following are strictly ignored in `.gitignore`:
* Executable binaries (`UFC4.exe`, `WebView2Loader.dll`, `bin/*.exe`, `bin/*.dll`)
* Offline generated game images (`out/boot-linked.bin`, `out/eboot.elf`, `out/patches.bin`)
* User data, runtime caches, and logs (`user/cache/`, `user/log/`, `logs/`)
* Local machine / AI agent notes (`AGENTS.md`, `CLAUDE.md`, `*GUIDE*.md`)

---

## 2. Automated Release Packager (`scripts/package_release.py`)
To build a release zip for end-users:
```bash
python scripts/package_release.py
```

### What Goes into the Release Bundle:
* `UFC4.exe` (Standalone Launcher)
* `WebView2Loader.dll`
* `bin/` (`sacredfire-game.exe`, `bb-gpu-capabilities.exe`, `SDL3.dll`, etc.)
* `patches/` (`UFC4.xml`)
* `scripts/` (Preparation and launcher server scripts)
* `share/` (`aerolib.inl`, `skip_movie.mkv`)
* `web/` (HTML/CSS/JS frontend)
* `tools/` (`gen_import_names.py`, `check_coverage.py`)
* `README.md`, `LICENSE`, `run_game.bat`

**Output:** `UFC4Native-ufc4-v0.1.0-windows-x86_64.zip` (~9.85 MB).
