# 01. Architecture & Runtime Design

## 1. The Native Execution Model
Unlike traditional emulators (such as RPCS3 for the PlayStation 3's Cell Broadband Engine), this project is a **native compatibility layer**:
* The PlayStation 4 console uses an **AMD Jaguar x86-64 CPU**.
* The game executable (`eboot.bin`) is already compiled in standard 64-bit x86 machine instructions.
* These instructions execute directly on your PC processor at native hardware clock speeds with **zero CPU instruction translation overhead**.

## 2. Core Subsystems

### A. The Host Runtime (`src/`)
Replaces proprietary Sony Orbis OS (FreeBSD-derived) syscalls with native Windows equivalents:
* **Threading & Sync (`runtime_thread.c`, `runtime_mutex.c`, `runtime_sema.c`):** Implemented using high-performance Windows SRWLOCKs (Slim Reader/Writer locks), high-resolution multimedia timers (`timeBeginPeriod(1)`), and thread priority boosting.
* **Memory Management (`runtime_memory.c`):** Maps 40-bit virtual address spaces using `VirtualAlloc` without high-entropy ASLR restrictions.
* **File System (`runtime_file.c`):** Transparently translates virtual paths (`/app0/`, `/temp0/`, `/savedata/`) to local directories.
* **Audio (`runtime_ajm.c`, `runtime_audio.c`):** Handles Sony ATRAC9 streams via `LibAtrac9` and MP3 streams via `minimp3`.
* **Input (`runtime_pad.c`):** Connects DualShock 4, DualSense, Xbox, and generic controllers via **SDL3**.

### B. Vulkan Graphics Translation (`gpu/`)
The PS4 GPU uses low-level GNM and GNMX APIs targeting AMD GCN architecture.
* The GPU pipeline (derived from **shadPS4**) decodes PM4 command buffers on dedicated worker threads.
* AMD GCN shader bytecodes are recompiled into **SPIR-V** on-the-fly and submitted directly to the **Vulkan 1.3 / 1.4** driver.
* Asynchronous compute and graphics submissions (`BB_ASYNC_SUBMIT=1`) allow multiple Vulkan recording workers to feed the GPU concurrently.
