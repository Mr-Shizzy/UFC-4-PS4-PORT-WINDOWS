/* ===================================================
   EA SPORTS UFC 4 — Launcher Frontend Logic
   =================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const btnPlay = document.getElementById('btn-play');
  const btnStop = document.getElementById('btn-stop');
  const playText = document.getElementById('play-text');
  const terminal = document.getElementById('terminal-output');
  const consoleStatus = document.getElementById('console-status');
  const sessionStatus = document.getElementById('session-status');
  const gpuNameDisplay = document.getElementById('gpu-name-display');
  const padStatusDisplay = document.getElementById('pad-status-display');
  const padIcon = document.getElementById('pad-icon');

  const selController = document.getElementById('sel-controller');
  const inpPlayerName = document.getElementById('inp-player-name');
  const selLanguage = document.getElementById('sel-language');
  const inpGamePath = document.getElementById('inp-game-path');

  const selPresentMode = document.getElementById('sel-present-mode');
  const selSharpness = document.getElementById('sel-sharpness');
  const selUpscaler = document.getElementById('sel-upscaler');

  const chkWriteWindows = document.getElementById('chk-write-windows');
  const chkPreupload = document.getElementById('chk-preupload');
  const chkPreciseReadbacks = document.getElementById('chk-precise-readbacks');
  const chkPipelineCache = document.getElementById('chk-pipeline-cache');
  const chkSkipMovies = document.getElementById('chk-skip-movies');
  const chkNeoMode = document.getElementById('chk-neo-mode');
  const chkShowFps = document.getElementById('chk-show-fps');

  let currentSettings = {
    fps: "60",
    resolution: "1080p",
    fullscreen: "1",
    player_name: "Player 1",
    language: "1",
    controller: "",
    present_mode: "Mailbox",
    sharpness: "2",
    upscaler: "0",
    write_windows: true,
    preupload: true,
    readbacks: true,
    pipeline_cache: true,
    skip_movies: true,
    neo_mode: false,
    show_fps: true
  };

  let logEventSource = null;
  let isGameRunning = false;

  // Initialize
  initTabs();
  initSegmentControls();
  fetchStatus();

  // Tab Navigation
  function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    const panes = document.querySelectorAll('.tab-pane');

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetId = tab.getAttribute('data-tab');
        tabs.forEach(t => t.classList.remove('active'));
        panes.forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add('active');
      });
    });
  }

  // Quick Action Segment Controls
  function initSegmentControls() {
    // FPS Segments
    document.querySelectorAll('#fps-segments .seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#fps-segments .seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentSettings.fps = btn.getAttribute('data-fps');
        saveSettings();
      });
    });

    // Resolution Segments
    document.querySelectorAll('#res-segments .seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#res-segments .seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentSettings.resolution = btn.getAttribute('data-res');
        chkNeoMode.checked = (currentSettings.resolution === '1440p' || currentSettings.resolution === '4k');
        saveSettings();
      });
    });

    // Display Mode Segments
    document.querySelectorAll('#display-segments .seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#display-segments .seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentSettings.fullscreen = btn.getAttribute('data-fullscreen');
        saveSettings();
      });
    });
  }

  // Fetch status from server
  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) return;
      const data = await res.json();

      if (data.gpu) {
        gpuNameDisplay.textContent = data.gpu;
      }
      if (data.game_path) {
        inpGamePath.value = data.game_path;
      }

      // Populate gamepads
      updateGamepadsList(data.gamepads || []);

      // Populate saved settings if any
      if (data.settings) {
        applySettings(data.settings);
      }

      // Check if game is already running
      if (data.is_running) {
        setGameRunningState(true);
      }
    } catch (err) {
      console.warn('Status fetch error:', err);
    }
  }

  function updateGamepadsList(gamepads) {
    selController.innerHTML = '<option value="">Any connected gamepad (or Keyboard)</option>';
    if (gamepads.length > 0) {
      gamepads.forEach(pad => {
        const opt = document.createElement('option');
        opt.value = pad.guid;
        opt.textContent = `${pad.name} (${pad.guid.substring(0, 8)}...)`;
        selController.appendChild(opt);
      });
      padStatusDisplay.textContent = gamepads[0].name;
      padIcon.classList.add('green-pulse');
    } else {
      padStatusDisplay.textContent = 'Keyboard Only';
      padIcon.classList.remove('green-pulse');
    }
  }

  function applySettings(s) {
    currentSettings = { ...currentSettings, ...s };

    // Selectors
    inpPlayerName.value = currentSettings.player_name || 'Player 1';
    selLanguage.value = currentSettings.language || '1';
    selPresentMode.value = currentSettings.present_mode || 'Mailbox';
    selSharpness.value = currentSettings.sharpness || '2';
    selUpscaler.value = currentSettings.upscaler || '0';

    // Toggles
    chkWriteWindows.checked = currentSettings.write_windows ?? true;
    chkPreupload.checked = currentSettings.preupload ?? true;
    chkPreciseReadbacks.checked = currentSettings.readbacks ?? true;
    chkPipelineCache.checked = currentSettings.pipeline_cache ?? true;
    chkSkipMovies.checked = currentSettings.skip_movies ?? true;
    chkNeoMode.checked = currentSettings.neo_mode ?? false;
    chkShowFps.checked = currentSettings.show_fps ?? true;

    // Segment active states
    document.querySelectorAll('#fps-segments .seg-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-fps') === currentSettings.fps);
    });
    document.querySelectorAll('#res-segments .seg-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-res') === currentSettings.resolution);
    });
    document.querySelectorAll('#display-segments .seg-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-fullscreen') === currentSettings.fullscreen);
    });
  }

  async function saveSettings() {
    try {
      currentSettings.player_name = inpPlayerName.value;
      currentSettings.language = selLanguage.value;
      currentSettings.controller = selController.value;
      currentSettings.present_mode = selPresentMode.value;
      currentSettings.sharpness = selSharpness.value;
      currentSettings.upscaler = selUpscaler.value;

      currentSettings.write_windows = chkWriteWindows.checked;
      currentSettings.preupload = chkPreupload.checked;
      currentSettings.readbacks = chkPreciseReadbacks.checked;
      currentSettings.pipeline_cache = chkPipelineCache.checked;
      currentSettings.skip_movies = chkSkipMovies.checked;
      currentSettings.neo_mode = chkNeoMode.checked;
      currentSettings.show_fps = chkShowFps.checked;

      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentSettings)
      });
    } catch (e) {
      console.warn('Save settings error:', e);
    }
  }

  // Change listeners for instant auto-save
  [inpPlayerName, selLanguage, selController, selPresentMode, selSharpness, selUpscaler,
   chkWriteWindows, chkPreupload, chkPreciseReadbacks, chkPipelineCache, chkSkipMovies,
   chkNeoMode, chkShowFps].forEach(el => {
    el.addEventListener('change', saveSettings);
  });

  // Rescan pads button
  document.getElementById('btn-rescan-pads').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/rescan_pads', { method: 'POST' });
      const data = await res.json();
      updateGamepadsList(data.gamepads || []);
    } catch (e) {
      console.error(e);
    }
  });

  // Launch Game
  btnPlay.addEventListener('click', async () => {
    if (isGameRunning) return;
    saveSettings();

    try {
      setGameRunningState(true);
      appendLogLine('[Launcher] Launching EA SPORTS UFC 4 with chosen configuration...\n', 'log-info');

      // Switch tab to Live Console automatically
      document.querySelector('.nav-tab[data-tab="tab-console"]').click();

      const res = await fetch('/api/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentSettings)
      });

      if (!res.ok) {
        const err = await res.text();
        appendLogLine(`[Error] Failed to launch game: ${err}\n`, 'log-err');
        setGameRunningState(false);
        return;
      }

      startLogStream();
    } catch (err) {
      appendLogLine(`[Error] Network error during launch: ${err}\n`, 'log-err');
      setGameRunningState(false);
    }
  });

  // Stop Game
  btnStop.addEventListener('click', async () => {
    try {
      appendLogLine('[Launcher] Requesting game termination...\n', 'log-warn');
      await fetch('/api/stop', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  });

  function setGameRunningState(running) {
    isGameRunning = running;
    if (running) {
      btnPlay.style.display = 'none';
      btnStop.style.display = 'flex';
      consoleStatus.textContent = 'Status: Game Running';
      consoleStatus.style.color = '#00E676';
      sessionStatus.textContent = 'In Match (Vulkan)';
      sessionStatus.style.color = '#00E676';
    } else {
      btnPlay.style.display = 'flex';
      btnStop.style.display = 'none';
      consoleStatus.textContent = 'Status: Idle';
      consoleStatus.style.color = '';
      sessionStatus.textContent = 'Idle';
      sessionStatus.style.color = '';
      if (logEventSource) {
        logEventSource.close();
        logEventSource = null;
      }
    }
  }

  // Live SSE Log Stream
  function startLogStream() {
    if (logEventSource) logEventSource.close();

    logEventSource = new EventSource('/api/logs/stream');
    logEventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'log') {
          appendLogLine(payload.text);
        } else if (payload.type === 'exit') {
          appendLogLine(`\n[Process Exited] Code: ${payload.code}\n`, payload.code === 0 ? 'log-info' : 'log-warn');
          setGameRunningState(false);
        }
      } catch (e) {
        appendLogLine(event.data + '\n');
      }
    };

    logEventSource.onerror = () => {
      // Stream ended or connection lost
      setGameRunningState(false);
    };
  }

  function appendLogLine(text, cssClass = '') {
    const span = document.createElement('span');
    span.textContent = text;
    if (cssClass) span.classList.add(cssClass);
    terminal.appendChild(span);
    terminal.scrollTop = terminal.scrollHeight;
  }

  // Console Actions
  document.getElementById('btn-copy-log').addEventListener('click', () => {
    navigator.clipboard.writeText(terminal.innerText);
    const orig = document.getElementById('btn-copy-log').textContent;
    document.getElementById('btn-copy-log').textContent = 'Copied!';
    setTimeout(() => document.getElementById('btn-copy-log').textContent = orig, 1500);
  });

  document.getElementById('btn-clear-log').addEventListener('click', () => {
    terminal.innerHTML = '<span class="log-info">[Console Cleared]</span>\n';
  });

  document.getElementById('btn-open-log-dir').addEventListener('click', () => {
    fetch('/api/open_logs', { method: 'POST' });
  });

  document.getElementById('btn-clear-cache').addEventListener('click', async () => {
    if (confirm('Clear shader cache? On next launch shaders will be recompiled.')) {
      await fetch('/api/clear_cache', { method: 'POST' });
      alert('Shader cache cleared.');
    }
  });

  document.getElementById('btn-rebuild-patches').addEventListener('click', async () => {
    appendLogLine('[Launcher] Rebuilding patches.bin...\n', 'log-info');
    document.querySelector('.nav-tab[data-tab="tab-console"]').click();
    const res = await fetch('/api/rebuild_patches', { method: 'POST' });
    const txt = await res.text();
    appendLogLine(txt + '\n', 'log-info');
  });
});
