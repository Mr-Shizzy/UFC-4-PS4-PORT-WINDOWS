# 04. Stability Patches & Null-Safety

UFC 4 relies on online services (EA DirtySDK, telemetry, PSN matchmaking) and multi-threaded dispatchers that would crash in an offline environment without specific patches.

---

## 1. Dual-Baked XML Patches (`patches/UFC4.xml`)
The port uses 46 community and engine stability patches compiled by `scripts/patches.py` into `out/patches.bin`:

### A. DirtySDK Telemetry & HTTP Clean Offline Fallback
* **Addresses:** `0x0177cdd0`, `0x017232c1`
* **Purpose:** The game's `SimThread` checks for network status. When offline, uninitialized HTTP context pointers cause null-pointer dereferences. The patch forces clean offline status (`0xffffffff`), allowing the engine to skip telemetry without crashing.

### B. Corner & Fighter Dispatch Null-Safety
* **Addresses:** `0xb338e7`, `0xb42f73`, `0xb434f3`
* **Purpose:** Protects blue/red corner fighter initialization. In offline exhibition modes, unassigned corner structures are replaced with safe trampolines.

### C. 60 FPS / Unlimited Framerate Unlock
* **Mechanism:** The PS4 game queries its internal present interval function at guest `0x1182a0` and enforces a 30 Hz lock.
* **Bypass:** The runtime overrides `BB_FLIP_RATE=0` and feeds a 480 Hz virtual vblank, unlocking 60, 120, 144, 240, or uncapped FPS.

---

## 2. Engine Backpressure Flags

### `BB_UI_BACKPRESSURE=1`
* **Problem:** In Career mode, rapid menu navigation triggers up to 8 UI scene builds between consecutive rendering frames, crashing the `UI Update` worker thread.
* **Fix:** Forces the UI builder to wait up to 250 ms for the next frame flip before pushing new scene graphs.

### `BB_APPEARANCE_BACKPRESSURE=1`
* **Problem:** In Create-A-Fighter (Fighter Editor), rapidly adjusting body, facial, or hair sliders exhausts the allocated appearance memory pool, resulting in a heap corruption crash.
* **Fix:** Restricts allocation rate, waiting up to 250 ms for expired appearance entries to be reclaimed.
