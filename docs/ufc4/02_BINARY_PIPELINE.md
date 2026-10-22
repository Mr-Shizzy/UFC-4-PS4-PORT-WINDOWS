# 02. Binary Pipeline & Symbol Resolution

The offline binary preparation stage converts a retail PS4 dump into a bootable PC memory image without dynamic patching during gameplay.

---

## Step 1: Game Identification & Merge
1. **Input:** Decrypted base game `CUSA14209` and update `CUSA14209-patch` (v28.00).
2. **Merge Tool:** `scripts/merge_update.py` merges the update files over the base game into `CUSA14209-merged` using NTFS hard links (no duplicate disk space consumed).
3. **Verification:** `scripts/game_check.py` validates `param.sfo` (Title ID `CUSA14209`, version `28.00`) and checks the SHA-256 hash of `eboot.bin`'s loaded image (`83cfbe26711d6759556bba42a835e52450ec58117fe0a2fad33edfcd6c46981f`).

---

## Step 2: Segment Extraction & TLS Patching (`scripts/prepare.py`)
1. Parses the PS4 ELF/SELF headers, identifying loadable segments (`PT_LOAD`).
2. Scans for Thread Local Storage (TLS) accesses:
   * PS4 uses `fs:[0]` for thread-control-block (TCB) loads.
   * `prepare.py` redirects these to the Windows TEB TLS slot (`gs:[0x1480 + 8*slot]`).

---

## Step 3: Module Linking (`scripts/link_modules.py`)
1. Links the game's `eboot.bin` with bundled system libraries:
   * `sce_module/libc.prx` (Standard C library)
   * `sce_module/libSceFios2.prx` (File I/O streaming subsystem)
2. Combines them into a single contiguous flat image: `out/boot-linked.bin` (~57.8 MB).
3. Produces `out/link.json` detailing exported NIDs and unresolved imported symbols.

---

## Step 4: Symbol Resolution (`tools/gen_import_names.py`)
1. PS4 dynamic libraries obfuscate function names into 64-bit/32-bit **NIDs** (Numeric Identifiers).
2. `gen_import_names.py` matches imported NIDs against `share/aerolib.inl` (171,520 reverse-engineered symbols from shadPS4).
3. Generates `out/import_names.txt` (636 resolved symbols for UFC 4 SDK 7.50).
4. `tools/check_coverage.py` confirms that all critical engine APIs are resolved by host HLE handlers.
