"""EA SPORTS UFC 4 — Windows Native Launcher Server
Lightweight, zero-dependency REST & SSE server providing backend services
for the modern UFC 4 desktop application.
"""
import os
import sys
import json
import queue
import threading
import subprocess
import socketserver
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT_DIR, "web")
USER_DIR = os.path.join(ROOT_DIR, "user")
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
SETTINGS_FILE = os.path.join(USER_DIR, "launcher_settings.json")
DEFAULT_GAME_PATH = os.path.join(ROOT_DIR, "..", "EA Sports UFC 4", "CUSA14209-merged")
if not os.path.exists(DEFAULT_GAME_PATH):
    DEFAULT_GAME_PATH = os.path.join(ROOT_DIR, "EA Sports UFC 4", "CUSA14209-merged")

os.makedirs(USER_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

class LauncherState:
    def __init__(self):
        self.game_process = None
        self.log_subscribers = []
        self.subscribers_lock = threading.Lock()
        self._gpu_name = None
        self._gamepads = None
        # Start hardware detection in background so server binds immediately
        threading.Thread(target=self._init_hardware, daemon=True).start()

    def _init_hardware(self):
        self._gpu_name = self.detect_gpu()
        self._gamepads = self.detect_gamepads()

    @property
    def gpu_name(self):
        if self._gpu_name is None:
            return self.detect_gpu()
        return self._gpu_name

    @property
    def gamepads(self):
        if self._gamepads is None:
            return self.detect_gamepads()
        return self._gamepads

    def detect_gpu(self):
        caps_exe = os.path.join(ROOT_DIR, "bin", "bb-gpu-capabilities.exe")
        if os.path.exists(caps_exe):
            try:
                res = subprocess.run([caps_exe], cwd=ROOT_DIR, capture_output=True, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    if "GPU scene scaling:" in line:
                        return line.split("GPU scene scaling:")[1].replace("supports live presets", "").strip()
            except Exception:
                pass
        return "NVIDIA GeForce RTX 4060 Laptop GPU"

    def detect_gamepads(self):
        pads = []
        caps_exe = os.path.join(ROOT_DIR, "bin", "bb-gpu-capabilities.exe")
        if os.path.exists(caps_exe):
            try:
                res = subprocess.run([caps_exe, "--gamepads"], cwd=ROOT_DIR, capture_output=True, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        pads.append({"guid": parts[0], "name": parts[1]})
            except Exception:
                pass
        return pads

    def broadcast_log(self, text, kind="log", code=None):
        payload = json.dumps({"type": kind, "text": text, "code": code})
        msg = f"data: {payload}\n\n"
        with self.subscribers_lock:
            dead = []
            for q in self.log_subscribers:
                try:
                    q.put_nowait(msg)
                except Exception:
                    dead.append(q)
            for d in dead:
                self.log_subscribers.remove(d)

STATE = LauncherState()

class LauncherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass # Silence normal HTTP request noise

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.send_json({
                "gpu": STATE.gpu_name,
                "gamepads": STATE.detect_gamepads(),
                "game_path": os.path.abspath(DEFAULT_GAME_PATH),
                "is_running": STATE.game_process is not None and STATE.game_process.poll() is None,
                "settings": self.load_settings()
            })
            return

        elif path == "/api/logs/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q = queue.Queue(maxsize=1000)
            with STATE.subscribers_lock:
                STATE.log_subscribers.append(q)

            try:
                # Send welcome message
                self.wfile.write(b"data: {\"type\":\"log\",\"text\":\"[Connected to live UFC 4 session stream]\\n\"}\n\n")
                self.wfile.flush()
                while True:
                    msg = q.get()
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with STATE.subscribers_lock:
                    if q in STATE.log_subscribers:
                        STATE.log_subscribers.remove(q)
            return

        elif path.startswith("/assets/"):
            filename = os.path.basename(path)
            asset_path = os.path.join(DEFAULT_GAME_PATH, "sce_sys", filename)
            if os.path.exists(asset_path):
                self.send_response(200)
                if filename.endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                elif filename.endswith(".dds"):
                    self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                with open(asset_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            req_data = {}

        if path == "/api/settings":
            self.save_settings(req_data)
            self.send_json({"ok": True})
            return

        elif path == "/api/rescan_pads":
            STATE.gamepads = STATE.detect_gamepads()
            self.send_json({"gamepads": STATE.gamepads})
            return

        elif path == "/api/launch":
            err = self.launch_game(req_data)
            if err:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(err.encode("utf-8"))
            else:
                self.send_json({"ok": True})
            return

        elif path == "/api/stop":
            if STATE.game_process and STATE.game_process.poll() is None:
                STATE.game_process.terminate()
            self.send_json({"ok": True})
            return

        elif path == "/api/open_logs":
            if sys.platform == "win32":
                os.startfile(LOGS_DIR)
            self.send_json({"ok": True})
            return

        elif path == "/api/clear_cache":
            cache_dir = os.path.join(USER_DIR, "cache")
            if os.path.exists(cache_dir):
                import shutil
                try:
                    shutil.rmtree(cache_dir)
                except Exception:
                    pass
            self.send_json({"ok": True})
            return

        elif path == "/api/rebuild_patches":
            patches_script = os.path.join(ROOT_DIR, "scripts", "patches.py")
            res = subprocess.run([sys.executable, patches_script, "--app-version", "28.00", "--title-id", "CUSA14209", "--out", "out", "--patches-dir", "patches"],
                                 cwd=ROOT_DIR, capture_output=True, text=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(res.stdout.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_settings(self, settings):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass

    def launch_game(self, s):
        if STATE.game_process and STATE.game_process.poll() is None:
            return "Game is already running"

        env = os.environ.copy()

        # Framerate & Presentation
        env["BB_FLIP_RATE"] = "0"
        env["BB_VBLANK_HZ"] = "480"
        env["BB_FPS_LIMIT"] = str(s.get("fps", "60"))
        env["BB_PRESENT_MODE"] = s.get("present_mode", "Mailbox")
        env["BB_FULLSCREEN"] = str(s.get("fullscreen", "1"))

        # Graphics & Display
        res_mode = s.get("resolution", "1080p")
        neo = s.get("neo_mode", False) or res_mode in ["1080p", "1440p", "4k"]
        env["BB_NEO"] = "1" if neo else "0"

        if res_mode == "1440p":
            env["BB_INTERNAL_WIDTH"] = "2560"
            env["BB_INTERNAL_HEIGHT"] = "1440"
        elif res_mode == "4k":
            env["BB_INTERNAL_WIDTH"] = "3840"
            env["BB_INTERNAL_HEIGHT"] = "2160"
        elif res_mode == "900p":
            env["BB_INTERNAL_WIDTH"] = "1600"
            env["BB_INTERNAL_HEIGHT"] = "900"

        sharpness_map = {"0": "0", "1": "2000", "2": "1000", "3": "200"}
        sharpness_val = str(s.get("sharpness", "2"))
        if sharpness_val != "0":
            env["BB_RCAS"] = "1"
            env["BB_RCAS_ATTENUATION"] = sharpness_map.get(sharpness_val, "1000")
        else:
            env["BB_RCAS"] = "0"

        env["BB_FSR1"] = "1" if s.get("upscaler") == "1" else "0"

        # Memory & Stability (UFC 3 / UFC 4 optimal profile)
        env["BB_BP5264"] = "1"
        env["BB_BP_RECONV"] = "1"
        env["BB_Z16S8_AS_D16"] = "1"
        env["BB_DRIVER_PIPELINE_CACHE"] = "1" if s.get("pipeline_cache", True) else "0"
        env["BB_PIPELINE_CACHE"] = "1"
        env["BB_READBACKS"] = "2" if s.get("readbacks", True) else "1"
        env["BB_READBACK_LINEAR"] = "1"
        env["BB_GPU_WRITE_TWINS"] = "0"
        env["BB_WRITE_WINDOW"] = "1" if s.get("write_windows", True) else "0"
        env["BB_WRITE_STEP"] = "1"
        env["BB_PREUPLOAD"] = "1" if s.get("preupload", True) else "0"
        env["BB_COPY_GPU_BUFFERS"] = "1"
        env["BB_DIRECT_MEMORY_ACCESS"] = "1"
        env["BB_INPLACE_TEXTURES"] = "1"
        env["BB_GARLIC_READS_VRAM"] = "1"
        env["BB_WRITE_TRACKING"] = "1"
        env["BB_UFC3_BIND_IDLE"] = "1"

        if s.get("skip_movies", True):
            clip = os.path.join(ROOT_DIR, "share", "skip_movie.mkv")
            env["BB_SKIP_MOVIES"] = "1"
            env["BB_SKIP_MOVIE_FILE"] = clip

        if s.get("controller"):
            env["BB_GAMEPAD"] = s["controller"]
        if s.get("player_name"):
            env["BB_USER_NAME"] = s["player_name"]
        if s.get("language"):
            env["BB_LANGUAGE"] = s["language"]

        game_bin = os.path.join(ROOT_DIR, "bin", "sacredfire-game.exe")
        boot_linked = os.path.join(ROOT_DIR, "out", "boot-linked.bin")
        import_names = os.path.join(ROOT_DIR, "out", "import_names.txt")
        content_bin = os.path.join(ROOT_DIR, "out", "content.bin")
        patches_bin = os.path.join(ROOT_DIR, "out", "patches.bin")
        app0_dir = os.path.abspath(DEFAULT_GAME_PATH)

        cmd = [
            game_bin,
            boot_linked,
            "--import-names", import_names,
            "--content-profile", content_bin,
            "--patches", patches_bin,
            "--app0", app0_dir,
            "--user", "user",
            "--timeout", "0"
        ]

        try:
            log_path = os.path.join(LOGS_DIR, "latest.log")
            log_file = open(log_path, "w", encoding="utf-8", errors="replace")
            log_file.write(f"=== EA SPORTS UFC 4 Session ===\nCommand: {' '.join(cmd)}\n\n")
            log_file.flush()

            proc = subprocess.Popen(
                cmd,
                cwd=ROOT_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
            STATE.game_process = proc

            def monitor_output():
                for line in proc.stdout:
                    log_file.write(line)
                    log_file.flush()
                    STATE.broadcast_log(line)
                proc.wait()
                log_file.write(f"\n[Session Exited with code {proc.returncode}]\n")
                log_file.close()
                STATE.broadcast_log("", kind="exit", code=proc.returncode)
                STATE.game_process = None

            t = threading.Thread(target=monitor_output, daemon=True)
            t.start()
            return None
        except Exception as e:
            return str(e)

def run_server():
    port = 44209
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), LauncherHandler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), LauncherHandler)
        port = server.server_address[1]

    port_file = os.path.join(USER_DIR, "launcher_port.txt")
    with open(port_file, "w") as f:
        f.write(str(port))
    print(f"UFC 4 Launcher server active at http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if STATE.game_process and STATE.game_process.poll() is None:
            STATE.game_process.terminate()

if __name__ == "__main__":
    run_server()
