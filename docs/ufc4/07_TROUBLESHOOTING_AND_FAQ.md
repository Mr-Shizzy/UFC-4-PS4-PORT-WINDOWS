# 07. Troubleshooting & Known Bugs

This guide documents known issues reported across the emulation community (shadPS4 / SacredFire) and their verified solutions.

---

### Issue 1: Game Freezes on First Loading Frame (shadPS4 #4534)
* **Symptom:** Audio plays and background threads run, but the screen stays stuck on the first loading image.
* **Cause:** PS4 Pro mode (`BB_NEO=1`) can stall the frame presentation loop on certain GPU drivers when rendering at 1080p.
* **Fix:** In the launcher settings, keep **PS4 Pro Mode (NEO)** unchecked for standard 1080p play. Pro mode should only be used for experimental 1440p/4K patches.

---

### Issue 2: Black Screen / Invisible Fighters in the Octagon (shadPS4 #4375)
* **Symptom:** Menus render normally, but upon entering a fight, character models and the canvas render completely black.
* **Cause:** The engine reads back images rendered in a linear format from GPU memory.
* **Fix:** Ensure `BB_READBACK_LINEAR=1` and `BB_READBACKS=2` are active. (Both are locked on by default in `launcher_server.py`).

---

### Issue 3: Fighter Vertex Explosion / Stretched Polygons (shadPS4 #4944)
* **Symptom:** Character bodies explode into stretched brown polygons during matches.
* **Cause:** GPU/CPU race condition on shared bone matrix pages.
* **Fix:** Ensure `BB_WRITE_WINDOW=1`, `BB_COPY_GPU_BUFFERS=1`, and `BB_DIRECT_MEMORY_ACCESS=1` are enabled.

---

### Issue 4: Sound Effects or Commentary Missing After Crash
* **Symptom:** Music plays in menus, but in-game punch sounds and commentary are silent.
* **Cause:** An improper shutdown (closing via Alt+F4 or killing the terminal) leaves audio state flags set to recovery mode.
* **Fix:** Start the game, enter an exhibition match, pause and use **Quit to Main Menu**, then press **STOP GAME** in the launcher. Relaunch cleanly.

---

### Issue 5: Controller Disconnect / Reconnect
* **Symptom:** Unplugging a gamepad freezes the input loop.
* **Fix:** The bundled `SDL3.dll` runtime supports hot-plugging. If a controller is not detected, click the **Rescan** button in the launcher dashboard.
