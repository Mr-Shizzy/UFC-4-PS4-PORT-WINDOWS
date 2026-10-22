@echo off
title EA SPORTS UFC 4 - Windows Native Port
cd /d "%~dp0"

echo ===================================================
echo   EA SPORTS UFC 4 - Windows Native Port (x86-64)
echo ===================================================
echo Starting game runtime with Vulkan...
echo.

rem Frame rate & smooth frame-pacing (Uncaps 30 FPS console lock, smooth 60 FPS presentation)
set BB_FLIP_RATE=0
set BB_VBLANK_HZ=480
set BB_FPS_LIMIT=60
set BB_PRESENT_MODE=Mailbox

rem Rendering and shader backport fixes for character textures
set BB_BP5264=1
set BB_BP_RECONV=1
set BB_Z16S8_AS_D16=1
set BB_DRIVER_PIPELINE_CACHE=1
set BB_PIPELINE_CACHE=1

rem Fighter hair smoothing & anti-dithering (Vulkan Alpha-to-Coverage)
set BB_ALPHA_TO_MASK=coverage

rem Non-NVIDIA / Intel Arc / AMD RDNA LDS memory barrier safety (uncomment if using Intel Arc A580/B580 or AMD RX)
rem set BB_INTEL_FIXES=1
rem set BB_INTEL_LDS_BARRIERS=1
rem set BB_NAN_GUARD=1
rem set BB_FLATTEN_WG=1
rem set BB_LDS_DIVERGENT=1
rem set BB_SUBGROUP32=1

rem Optional graphics & resolution enhancements:
rem set BB_NEO=1
rem set BB_RCAS=1

rem Memory management, write windows & micro-stutter fixes (EA Ignite engine)
set BB_READBACKS=2
set BB_READBACK_LINEAR=1
set BB_GPU_WRITE_TWINS=0
set BB_WRITE_WINDOW=1
set BB_WRITE_STEP=1
set BB_PREUPLOAD=1
set BB_COPY_GPU_BUFFERS=1

rem Texture streaming, memory readback & material rendering fixes (fixes black fighter textures)
set BB_DIRECT_MEMORY_ACCESS=1
set BB_INPLACE_TEXTURES=1
set BB_GARLIC_READS_VRAM=1
set BB_WRITE_TRACKING=1
rem Keep worker thread bind idle active (backward-compatible runtime flag)
set BB_UFC3_BIND_IDLE=1

rem Career mode, Create-A-Fighter stability & memory garbage collection
set BB_UI_BACKPRESSURE=1
set BB_APPEARANCE_BACKPRESSURE=1
set BB_DEPTH_AS_COLOR_REUSE=1
set BB_GC_STALE_SECONDS=60

rem Run game with real-time UTF-8 tee logging to logs\latest.log
python -u scripts\run_with_log.py bin\sacredfire-game.exe out\boot-linked.bin --import-names out\import_names.txt --content-profile out\content.bin --patches out\patches.bin --app0 "e:\Downloads\UFC4\EA Sports UFC 4\CUSA14209-merged" --user user --timeout 0 %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Game exited with code %ERRORLEVEL%.
    pause
)
