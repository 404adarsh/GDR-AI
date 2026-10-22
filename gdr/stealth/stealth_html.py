"""Mobile-first, OLED Pure Black Teleprompter HTML for GDR Stealth Meeting & Interview Copilot.
Accessible at http://<LAN_IP>:8844/stealth on smartphones and tablets.
100% self-contained with zero external dependencies, works offline.
"""

STEALTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>GDR AI | Stealth Copilot (OLED Teleprompter)</title>
  <meta name="theme-color" content="#000000">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <style>
    :root {
      --bg: #000000;
      --card-bg: #0a0a0c;
      --card-border: #1f2430;
      --cyan: #00f0ff;
      --cyan-glow: rgba(0, 240, 255, 0.25);
      --green: #10b981;
      --green-glow: rgba(16, 185, 129, 0.25);
      --purple: #a855f7;
      --yellow: #f59e0b;
      --red: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding-bottom: 70px;
    }

    /* Sticky Header */
    header {
      position: sticky; top: 0; z-index: 50;
      background: rgba(0, 0, 0, 0.95);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--card-border);
      padding: 10px 14px;
      display: flex; align-items: center; justify-content: space-between;
    }
    .brand {
      display: flex; align-items: center; gap: 8px;
    }
    .brand-title {
      font-size: 13px; font-weight: 800; letter-spacing: 1px; color: var(--cyan);
      text-transform: uppercase;
    }
    .status-pill {
      display: flex; align-items: center; gap: 5px;
      background: #111; border: 1px solid var(--card-border);
      padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: 600;
    }
    .dot {
      width: 7px; height: 7px; border-radius: 50%; background: var(--green);
      box-shadow: 0 0 6px var(--green);
    }
    .dot.pulse { animation: blink 1.2s infinite; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

    /* Action Bar */
    .action-bar {
      padding: 10px 14px;
      display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 8px;
      background: #050507; border-bottom: 1px solid #14161f;
    }
    .btn-solve {
      background: linear-gradient(135deg, #00b4d8, #0077b6);
      color: #fff; border: none; border-radius: 8px;
      padding: 10px; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;
      display: flex; align-items: center; justify-content: center; gap: 6px;
      cursor: pointer; box-shadow: 0 2px 10px rgba(0,180,216,0.3);
      transition: all 0.15s ease;
    }
    .btn-solve:active { transform: scale(0.97); }
    .btn-toggle {
      background: #12131a; border: 1px solid var(--card-border);
      color: var(--text-muted); border-radius: 8px;
      padding: 10px 6px; font-size: 11px; font-weight: 600;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
      cursor: pointer; transition: all 0.15s ease;
    }
    .btn-toggle.active {
      background: rgba(16, 185, 129, 0.15); border-color: var(--green);
      color: var(--green); box-shadow: 0 0 8px var(--green-glow);
    }

    /* Main Container */
    main {
      padding: 12px 14px;
      display: flex; flex-direction: column; gap: 12px;
      flex: 1;
    }

    /* Cards */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px;
      position: relative;
    }
    .card-title {
      font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px;
      margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;
    }
    .card-title.cyan { color: var(--cyan); }
    .card-title.green { color: var(--green); }
    .card-title.purple { color: var(--purple); }
    .card-title.yellow { color: var(--yellow); }

    .btn-copy {
      background: transparent; border: 1px solid #2a2e3d; color: #a1a1aa;
      padding: 2px 6px; border-radius: 4px; font-size: 10px; cursor: pointer;
    }
    .btn-copy:active { background: #222; }

    /* Problem Header */
    .problem-name {
      font-size: 16px; font-weight: 700; color: #fff; line-height: 1.3;
      margin-bottom: 4px;
    }
    .problem-time {
      font-size: 10px; color: var(--text-muted);
    }

    /* Say This First (Teleprompter Hero) */
    .say-box {
      background: linear-gradient(180deg, rgba(0, 240, 255, 0.08) 0%, rgba(0, 240, 255, 0.02) 100%);
      border-left: 3px solid var(--cyan);
      padding: 12px;
      border-radius: 6px;
      font-size: 14px;
      line-height: 1.5;
      font-weight: 500;
      color: #e0f2fe;
    }

    /* Approach Box */
    .approach-text {
      font-size: 12px; line-height: 1.5; color: #d1d5db; white-space: pre-line;
    }

    /* Code Box */
    .code-container {
      background: #040405; border: 1px solid #181920; border-radius: 6px;
      padding: 10px; overflow-x: auto;
    }
    pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11.5px; line-height: 1.45; color: #a5f3fc;
      margin: 0; white-space: pre;
    }

    /* Edge Cases */
    .edge-text {
      font-size: 12px; line-height: 1.5; color: #fde047; white-space: pre-line;
    }

    /* Bottom Prompt Bar */
    .bottom-bar {
      position: fixed; bottom: 0; left: 0; right: 0;
      background: #000000; border-top: 1px solid var(--card-border);
      padding: 8px 12px; display: flex; gap: 8px; z-index: 50;
    }
    .prompt-input {
      flex: 1; background: #0d0e12; border: 1px solid #222633;
      color: #fff; padding: 10px 12px; border-radius: 8px; font-size: 13px;
      outline: none;
    }
    .prompt-input:focus { border-color: var(--cyan); }
    .btn-send {
      background: #1e293b; border: 1px solid #334155; color: #fff;
      padding: 0 14px; border-radius: 8px; font-weight: 700; font-size: 12px;
      cursor: pointer;
    }
    .btn-send:active { background: var(--cyan); color: #000; }

    /* Screen Guide Modal */
    .guide-box {
      font-size: 11px; line-height: 1.4; color: #94a3b8;
      background: #06070a; border: 1px dashed #262938; padding: 8px 10px; border-radius: 6px;
    }
  </style>
</head>
<body>

  <!-- Sticky Header -->
  <header>
    <div class="brand">
      <div class="brand-title">🕵️ GDR Stealth Copilot</div>
    </div>
    <div class="status-pill">
      <div id="status-dot" class="dot"></div>
      <span id="status-text">Connected</span>
    </div>
  </header>

  <!-- Action Bar -->
  <div class="action-bar">
    <button class="btn-solve" onclick="triggerSolve()">
      ⚡ SOLVE NOW
    </button>
    <button id="btn-autowatch" class="btn-toggle" onclick="toggleAutoWatch()">
      <span>👁️ Auto</span>
      <span id="lbl-autowatch" style="font-size:9px;">OFF</span>
    </button>
    <button id="btn-whisper" class="btn-toggle" onclick="toggleWhisper()">
      <span>🎧 Whisper</span>
      <span id="lbl-whisper" style="font-size:9px;">OFF</span>
    </button>
  </div>

  <!-- Content -->
  <main>
    <!-- Meeting Invisibility Notice -->
    <div class="guide-box">
      🔒 <strong>100% Invisible to Google Meet:</strong> This phone display is a separate physical device. Participants on Google Meet screen share cannot see your phone.
    </div>

    <!-- Question Title -->
    <div class="card">
      <div class="card-title cyan">
        <span>Question Detected</span>
        <span id="sol-time" class="problem-time">Ready</span>
      </div>
      <div id="sol-question" class="problem-name">Waiting for question on screen...</div>
    </div>

    <!-- 1. Say This First -->
    <div class="card" style="border-color: rgba(0,240,255,0.3);">
      <div class="card-title cyan">
        <span>🗣️ Say This First (Spoken Points)</span>
        <button class="btn-copy" onclick="copyText('sol-say')">Copy</button>
      </div>
      <div id="sol-say" class="say-box">
        Copilot ready. As soon as you solve or a problem appears, your high-IQ spoken opening will show up right here.
      </div>
    </div>

    <!-- 2. Optimal Approach & Big-O -->
    <div class="card">
      <div class="card-title green">
        <span>💡 Optimal Approach & Big-O</span>
        <button class="btn-copy" onclick="copyText('sol-approach')">Copy</button>
      </div>
      <div id="sol-approach" class="approach-text">
        Optimal data structures, intuition, and Time/Space complexity will appear here.
      </div>
    </div>

    <!-- 3. Solution Code -->
    <div class="card">
      <div class="card-title purple">
        <span>💻 Solution Code</span>
        <button class="btn-copy" onclick="copyCode()">Copy Code</button>
      </div>
      <div class="code-container">
        <pre><code id="sol-code"># Production code snippet will appear here
def solve():
    pass</code></pre>
      </div>
    </div>

    <!-- 4. Edge Cases -->
    <div class="card">
      <div class="card-title yellow">
        <span>⚠️ Edge Cases & Interviewer Traps</span>
        <button class="btn-copy" onclick="copyText('sol-edges')">Copy</button>
      </div>
      <div id="sol-edges" class="edge-text">
        • Null or empty inputs
        • Single element edge case
        • Boundary limits
      </div>
    </div>
  </main>

  <!-- Bottom Prompt Bar -->
  <div class="bottom-bar">
    <input type="text" id="manual-prompt" class="prompt-input" placeholder="Type question or keyword..." onkeypress="handleKey(event)">
    <button class="btn-send" onclick="sendManualPrompt()">Solve</button>
  </div>

  <script>
    let lastTimestamp = null;
    let autowatchState = false;
    let whisperState = false;

    // Prevent phone screen from sleeping
    async function requestWakeLock() {
      try {
        if ('wakeLock' in navigator) {
          await navigator.wakeLock.request('screen');
        }
      } catch (e) {}
    }
    requestWakeLock();
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') requestWakeLock();
    });

    async function pollLatest() {
      try {
        const res = await fetch('/api/stealth/latest');
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();
        
        document.getElementById('status-dot').style.background = '#10b981';
        document.getElementById('status-dot').classList.remove('pulse');
        document.getElementById('status-text').textContent = 'Connected';

        if (data.timestamp && data.timestamp !== lastTimestamp) {
          lastTimestamp = data.timestamp;
          renderSolution(data);
        }
      } catch (err) {
        document.getElementById('status-dot').style.background = '#ef4444';
        document.getElementById('status-text').textContent = 'Offline';
      }
    }

    async function pollStatus() {
      try {
        const res = await fetch('/api/stealth/status');
        if (res.ok) {
          const s = await res.json();
          autowatchState = !!s.autowatch_enabled;
          whisperState = !!s.whisper_enabled;
          updateToggleUI();
        }
      } catch (e) {}
    }

    function updateToggleUI() {
      const btnAuto = document.getElementById('btn-autowatch');
      const lblAuto = document.getElementById('lbl-autowatch');
      if (autowatchState) {
        btnAuto.classList.add('active');
        lblAuto.textContent = 'ON';
      } else {
        btnAuto.classList.remove('active');
        lblAuto.textContent = 'OFF';
      }

      const btnWhisp = document.getElementById('btn-whisper');
      const lblWhisp = document.getElementById('lbl-whisper');
      if (whisperState) {
        btnWhisp.classList.add('active');
        lblWhisp.textContent = 'ON';
      } else {
        btnWhisp.classList.remove('active');
        lblWhisp.textContent = 'OFF';
      }
    }

    function renderSolution(data) {
      if (data.question) document.getElementById('sol-question').textContent = data.question;
      if (data.talking_points) document.getElementById('sol-say').textContent = data.talking_points;
      if (data.approach) document.getElementById('sol-approach').textContent = data.approach;
      if (data.code) document.getElementById('sol-code').textContent = data.code;
      if (data.edge_cases) document.getElementById('sol-edges').textContent = data.edge_cases;
      if (data.timestamp) {
        const dt = new Date(data.timestamp);
        document.getElementById('sol-time').textContent = dt.toLocaleTimeString();
      }
    }

    async function triggerSolve(prompt = null) {
      document.getElementById('status-dot').classList.add('pulse');
      document.getElementById('status-text').textContent = 'Solving...';
      try {
        const res = await fetch('/api/stealth/solve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt })
        });
        const data = await res.json();
        renderSolution(data);
        lastTimestamp = data.timestamp;
      } catch (e) {
        alert('Error triggering screen solve: ' + e);
      } finally {
        document.getElementById('status-dot').classList.remove('pulse');
        document.getElementById('status-text').textContent = 'Connected';
      }
    }

    async function toggleAutoWatch() {
      autowatchState = !autowatchState;
      updateToggleUI();
      try {
        await fetch('/api/stealth/autowatch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: autowatchState })
        });
      } catch (e) {}
    }

    async function toggleWhisper() {
      whisperState = !whisperState;
      updateToggleUI();
      try {
        await fetch('/api/stealth/whisper', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: whisperState })
        });
      } catch (e) {}
    }

    function sendManualPrompt() {
      const inp = document.getElementById('manual-prompt');
      const val = inp.value.trim();
      if (!val) return;
      inp.value = '';
      triggerSolve(val);
    }

    function handleKey(e) {
      if (e.key === 'Enter') sendManualPrompt();
    }

    function copyText(id) {
      const txt = document.getElementById(id).textContent;
      navigator.clipboard.writeText(txt);
      showFeedback('Copied text!');
    }

    function copyCode() {
      const code = document.getElementById('sol-code').textContent;
      navigator.clipboard.writeText(code);
      showFeedback('Copied code!');
    }

    function showFeedback(msg) {
      const originalText = document.getElementById('status-text').textContent;
      document.getElementById('status-text').textContent = msg;
      setTimeout(() => {
        document.getElementById('status-text').textContent = originalText;
      }, 1500);
    }

    // Polling intervals
    setInterval(pollLatest, 2000);
    setInterval(pollStatus, 4000);
    pollLatest();
    pollStatus();
  </script>
</body>
</html>
"""

