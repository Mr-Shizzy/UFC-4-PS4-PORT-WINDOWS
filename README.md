# EA SPORTS UFC 4 — Windows Native Port (x86-64)

**EA SPORTS UFC 4** (PlayStation 4, `CUSA14209`, update **v28.00**) running as a **native x86-64** program on Windows.

This is **not a slow CPU emulator**: the game's original PS4 x86-64 code runs directly on your PC processor at native speeds. A specialized host runtime replaces the proprietary Orbis OS libraries, and an advanced graphics renderer derived from **shadPS4** translates PlayStation 4 GNM/GNMX draw calls and shaders to **Vulkan 1.3 / 1.4**.

Built upon the native port lineage of **SacredFire** and **bbport**, adapted for EA SPORTS UFC 4 on the EA Ignite engine.

> **No game files are included.** You must provide your own legally dumped copy of UFC 4 (`CUSA14209`) and its v28.00 update. This fan project is not affiliated with, endorsed by, or sponsored by Electronic Arts, Sony Interactive Entertainment, or the UFC.

---

## Features

- **Unlocked Framerate & Smooth Frame Pacing:** Uncapped 30 FPS console limit; supports smooth **60 FPS, 120 FPS, 144 FPS, 240 FPS or Unlimited** playback.
- **Native x86-64 Execution:** Zero CPU emulation overhead.
- **Vulkan 1.3/1.4 Graphics Backend:** Real-time translation of GNM GPU commands with modern compute & graphics pipeline caching.
- **Write Windows & Fast GPU Readbacks:** High-speed memory tracking eliminating micro-stutters during strikes and camera transitions.
- **Modern Desktop Launcher (`UFC4.exe`):**
  - Standalone Windows application with embedded Microsoft Edge WebView2.
  - AAA Dark UI with real-time hardware detection (GPU & controllers).
  - One-click launch with live session console log viewer.
  - Built-in graphics toggles: **PS4 Pro Mode (NEO)**, **AMD FSR 3.1**, **RCAS Sharpening**, and custom FPS limits.
- **Controller Support:** Native DualShock 4, DualSense, Xbox and generic XInput/DirectInput gamepad support via SDL3.
- **Automated Update Merging:** `scripts/merge_update.py` links the base game (`CUSA14209`) and update files using NTFS hard links (no duplicate disk space used).

---

## System Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating System** | 64-bit Windows 10 (1903+) or Windows 11 | 64-bit Windows 11 |
| **Processor (CPU)** | x86-64 CPU with AVX2, BMI1, MOVBE (Intel Haswell 4th gen+ or AMD Ryzen) | 6-core / 12-thread modern CPU (Intel 12th+ gen, Ryzen 5000+) |
| **Graphics (GPU)** | Vulkan 1.3 capable GPU with 6 GB VRAM | NVIDIA RTX 3060 / AMD RX 6700 XT (8 GB+ VRAM) |
| **Memory (RAM)** | 16 GB RAM | 16 GB – 32 GB RAM |
| **Storage** | NTFS drive with space for game dump | Fast NVMe SSD |
| **Game Dump** | PS4 `CUSA14209` base game + `28.00` update dump | Decrypted dump of base + patch |

---

## Quick Start (Playing)

1. **Download the latest release:** Download the pre-built archive `UFC4Native-windows-x86_64.zip` from [Releases](../../releases).
2. **Extract:** Extract the zip to any folder on your drive (e.g. `E:\Games\UFC4Native`).
3. **Dump Game Files:** Place your dumped `CUSA14209` and update `CUSA14209-patch` adjacent to each other.
4. **Launch:** Run **`UFC4.exe`**, select your game directory using the browse button, and press **Launch Game**.

---

## Building from Source

To compile the native launcher and runtime tools from source:

### Prerequisites
- Windows 10/11 x86-64
- Clang 18+ or MSVC (Visual Studio 2022 C++)
- CMake 3.25+
- Vulkan SDK 1.3+
- Python 3.10+

### Build Steps
```bash
# Prepare game binary and generate stubs
python scripts/prepare.py --game "/path/to/CUSA14209-merged"
python scripts/link_modules.py --game "/path/to/CUSA14209-merged"
python tools/gen_import_names.py --aerolib share/aerolib.inl
python scripts/gen_patches.py

# Build launcher
rc /fo packaging/windows/ufc4.res packaging/windows/ufc4.rc
cl /O2 /EHsc packaging/windows/ufc4_standalone.cpp packaging/windows/ufc4.res /link /SUBSYSTEM:WINDOWS /OUT:UFC4.exe
```

---

## Credits & Acknowledgments

- **[GNSB](https://github.com/GNSB/UFC-3-PS4-PORT-LINUX-WINDOWS)** — author of the UFC 3 native port, whose codebase and Ignite engine memory analysis served as the foundational baseline for this UFC 4 port.
- **[SacredFire](https://github.com/T3CHNOLOG1C/SacredFire)** — base runtime, GNM translator and Windows packaging.
- **[bbport](https://github.com/deadinside28/bloodborne_pc)** — the original native PS4 port architecture for PC.
- **[shadPS4](https://github.com/shadps4-emu/shadPS4)** — renderer architecture, SPIR-V recompiler, and `aerolib.inl` symbol database.
- **[illusion](https://github.com/illusionyy/PS-Game-Patch)** — game patch format and community FPS unlock techniques.

---

## License

This project is licensed under the **GNU General Public License v2.0 or later** (GPL-2.0-or-later). See the [`LICENSE`](LICENSE) file for details. Third-party library licenses are located in [`licenses/`](licenses/).
