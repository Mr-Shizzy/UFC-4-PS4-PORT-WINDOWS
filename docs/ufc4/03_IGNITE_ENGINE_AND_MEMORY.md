# 03. EA Ignite Engine & Memory Coherence

EA SPORTS UFC 4 is built on the **EA Ignite** engine. Understanding how Ignite manages memory between the CPU and GPU is essential for eliminating crashes, stutter, and graphical artifacts.

---

## 1. Dynamic Vertex & Bone Buffers
In Ignite, dynamic fighter meshes (skeletal bone matrices, facial blendshapes, cloth deformation, and blood/sweat splatters) are computed by the CPU and streamed to the GPU every frame using discardable memory locks (`Map(WRITE_DISCARD)`).

### The Micro-Stutter & Black Texture Problem
* On PS4, CPU and GPU share unified memory (Garlic/Onion bus).
* On PC, dynamic buffers share 4KB virtual memory pages with small GPU render outputs (e.g., 408-byte shader bindings).
* Without optimization, every CPU write to a bone matrix forces the PC to wait for the GPU to finish, download the page from VRAM (readback stall), and re-upload it. This causes severe micro-stutters and drops FPS to 20–30.
* If readbacks fail or are misaligned, textures turn pitch black (**Issue #4375**).

---

## 2. The "Write Windows" Solution (`BB_WRITE_WINDOW=1`)
To solve this, the runtime implements **Write Windows**:
1. When CPU begins writing to dynamic buffers, the host marks the memory page as open.
2. CPU writes proceed using standard instructions without blocking for the GPU.
3. Upon GPU command submission (`SubmitGfx`/`SubmitAsc`), only the modified words are uploaded to VRAM, leaving GPU-owned bytes untouched.
4. **Performance Impact:** Reduces readbacks from ~380/s to under 80/s, boosting fight framerates from **60 FPS to 110–140+ FPS**!

---

## 3. Critical Memory Configuration Flags

| Environment Variable | Recommended Value | Technical Purpose |
| :--- | :--- | :--- |
| `BB_WRITE_WINDOW` | `1` | Enables fast CPU/GPU write window tracking. |
| `BB_WRITE_STEP` | `1` | Tracks individual word changes via CPU trap flags. |
| `BB_READBACKS` | `2` | Precise readbacks mode for character rendering. |
| `BB_READBACK_LINEAR` | `1` | Essential for UFC 4; fixes black textures on fighters & octagon. |
| `BB_DIRECT_MEMORY_ACCESS`| `1` | Direct host access to mapped allocations. |
| `BB_GARLIC_READS_VRAM` | `1` | Permits fast host read access to VRAM memory pools. |
| `BB_DEPTH_AS_COLOR_REUSE`| `1` | Reuses shadow depth buffers converted to color; prevents Career menu lag. |
| `BB_GC_STALE_SECONDS` | `60` | Frees overwritten textures unused for 60s; prevents long-session memory leaks. |
