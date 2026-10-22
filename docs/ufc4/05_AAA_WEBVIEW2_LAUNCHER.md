# 05. AAA WebView2 Desktop Launcher Architecture

Rather than a generic Win32 dialog or third-party script, the UFC 4 native port features an integrated standalone desktop application.

---

## 1. Subsystem Architecture

```
┌────────────────────────────────────────────────────────┐
│                      UFC4.exe                          │
│  Native C++ Win32 Host (ufc4_standalone.cpp)           │
│  - Finds Python, starts local background server        │
│  - Embeds Microsoft Edge WebView2 control (x64)        │
│  - Edge App Mode fallback if WebView2 runtime absent   │
└──────────────────────────┬─────────────────────────────┘
                           │ Loads http://127.0.0.1:44209
┌──────────────────────────▼─────────────────────────────┐
│                 Modern Dark Frontend                   │
│  web/index.html · web/style.css · web/app.js           │
│  - Real-time GPU & Gamepad detection display           │
│  - Segments: Target FPS, Resolution, Display mode      │
│  - Live Console tab with SSE stream viewer             │
└──────────────────────────┬─────────────────────────────┘
                           │ REST API & Server-Sent Events
┌──────────────────────────▼─────────────────────────────┐
│              scripts/launcher_server.py                │
│  Python Local Server (Bound to port 44209)             │
│  - /api/status: Hardware & settings query              │
│  - /api/launch: Spawn sacredfire-game.exe with env     │
│  - /api/browse_game_dir: Native Windows folder picker  │
│  - /api/logs/stream: Real-time stdout/stderr streaming │
└────────────────────────────────────────────────────────┘
```

---

## 2. Key Features & Endpoints

### Native Windows Folder Picker (`/api/browse_game_dir`)
When the user clicks **Browse...**, the server invokes a PowerShell `FolderBrowserDialog` modal, updates `launcher_settings.json`, and reflects the new path in the UI without requiring manual file path editing.

### Real-Time Live Console (`/api/logs/stream`)
Uses HTML5 Server-Sent Events (SSE). The Python server captures game process output through `scripts/run_with_log.py` and streams it directly into the embedded web terminal in real-time.

### Graceful Termination (`/api/stop`)
Sends `WM_CLOSE` / `SIGTERM` followed by a clean process join, ensuring Vulkan driver pipeline caches are flushed to disk without corruption.
