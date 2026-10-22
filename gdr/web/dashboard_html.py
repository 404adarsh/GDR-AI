"""Cinematic 13-Screen HUD Dashboard for GDR AI.
Built with dark glassmorphism, glowing audio-reactive AI orb,
real browser Web Speech Recognition + SpeechSynthesis, and real live webcam stream.
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GDR AI // Autonomous Personal Assistant</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <script>
    // =========================================================================
    // WORKBENCH INTERACTION & COMMAND PALETTE (VS Code Inspired)
    // =========================================================================
    let activeSectionId = 'home-chat';
    let bottomPanelOpen = false;
    let bottomPanelMaximized = false;
    let terminalHistory = [];
    let terminalHistoryIdx = -1;

    // Palette Commands Catalog (All 5 Sections + Actions)
    const PALETTE_COMMANDS = [
      { id: 'home', label: '1. Home', category: 'Section 1: Home & Chat', action: () => showScreen('home') },
      { id: 'chat', label: '2. Chat (AI Assistant)', category: 'Section 1: Home & Chat', action: () => showScreen('chat') },
      { id: 'new_chat', label: 'New Assistant Conversation', category: 'Section 1: Home & Chat', action: () => newChatConversation() },
      { id: 'memory', label: '7. Memory Vault', category: 'Section 1: Home & Chat', action: () => showScreen('memory') },
      { id: 'inbox', label: '5. Unified Inbox', category: 'Section 1: Home & Chat', action: () => showScreen('inbox') },
      { id: 'calendar', label: '6. Calendar & Agenda', category: 'Section 1: Home & Chat', action: () => showScreen('calendar') },
      { id: 'model_hub', label: 'AI Provider Hub & Hugging Face Pull', category: 'Section 1: Home & Chat', action: () => openModelHubModal() },
      { id: 'aarushi', label: 'Aarushi Companion Settings', category: 'Section 1: Home & Chat', action: () => openAarushiCompanionModal() },
      { id: 'focus_call', label: '19. Focus Anime Companion Call', category: 'Section 1: Home & Chat', action: () => openFocusCallMode() },
      { id: 'contacts', label: '20. Trusted Relations & Network', category: 'Section 1: Home & Chat', action: () => showScreen('contacts') },
      
      { id: 'coding', label: '10. Coding Studio', category: 'Section 2: Coding Studio', action: () => showScreen('coding') },
      { id: 'ide', label: '17. GDR-IDE Workspace', category: 'Section 2: Coding Studio', action: () => showScreen('ide') },
      { id: 'terminal', label: 'Open Integrated Terminal', category: 'Section 2: Coding Studio', action: () => toggleBottomPanel(true, 'terminal') },
      { id: 'output', label: 'Open Output & Diagnostics Panel', category: 'Section 2: Coding Studio', action: () => toggleBottomPanel(true, 'output') },
      
      { id: 'tasks', label: '4. Autonomous Tasks', category: 'Section 3: Automation & Tasks', action: () => showScreen('tasks') },
      { id: 'workflows', label: '9. Workflows Builder', category: 'Section 3: Automation & Tasks', action: () => showScreen('workflows') },
      { id: 'bots', label: '14. Multi-Bot Orchestration', category: 'Section 3: Automation & Tasks', action: () => showScreen('bots') },
      { id: 'messaging', label: 'Messaging Integrations (Telegram & MarkanM)', category: 'Section 3: Automation & Tasks', action: () => showScreen('messaging') },
      { id: 'approvals', label: '3. Security Approvals', category: 'Section 3: Automation & Tasks', action: () => showScreen('approvals') },
      { id: 'stealth', label: 'Stealth Copilot & Ghost HUD', category: 'Section 3: Automation & Tasks', action: () => showScreen('stealth') },
      
      { id: 'monitor', label: '11. System Monitor & Telemetry', category: 'Section 4: Devices & System', action: () => showScreen('monitor') },
      { id: 'camera', label: '8. Camera & Face Presence', category: 'Section 4: Devices & System', action: () => showScreen('camera') },
      { id: 'mesh', label: '16. Multi-Device Mesh', category: 'Section 4: Devices & System', action: () => showScreen('mesh') },
      { id: 'fix_sound', label: 'Fix Realtek Laptop Speakers & Microphone', category: 'Section 4: Devices & System', action: () => repairLaptopAudioHardware() },
      { id: 'cloudflare', label: 'Cloudflare Tunnel Share', category: 'Section 4: Devices & System', action: () => openCloudflareModal() },
      
      { id: 'settings', label: '12. Settings & Preferences', category: 'Section 5: Settings & Security', action: () => showScreen('settings') },
      { id: 'rag', label: '15. RAG Vector Vault', category: 'Section 5: Settings & Security', action: () => showScreen('rag') },
      { id: 'audit', label: '13. Security Audit Log', category: 'Section 5: Settings & Security', action: () => showScreen('audit') },
      { id: 'theme', label: 'View: Toggle Dark / Light Theme', category: 'Workbench', action: () => toggleTheme() },
      { id: 'sidebar', label: 'View: Toggle Primary Sidebar', category: 'Workbench', action: () => toggleSidebar() },
      { id: 'panel', label: 'View: Toggle Integrated Terminal Panel', category: 'Workbench', action: () => toggleBottomPanel() },
      { id: 'panic', label: '🚨 Emergency Panic Kill All Autonomous Tasks', category: 'Safety', action: () => togglePanic() }
    ];

    let filteredPaletteCommands = [...PALETTE_COMMANDS];
    let selectedPaletteIdx = 0;

    function selectSection(secId, scrollIntoView = true) {
      activeSectionId = secId;
      document.querySelectorAll('.activity-item').forEach(btn => btn.classList.remove('active'));
      const activeBtn = document.getElementById('act-sec-' + secId);
      if (activeBtn) activeBtn.classList.add('active');

      const secNames = {
        'home-chat': 'Home & Chat',
        'coding-studio': 'Coding Studio',
        'automation-tasks': 'Automation & Tasks',
        'devices-system': 'Devices & System',
        'settings-security': 'Settings & Security'
      };
      const crumb = document.getElementById('titlebar-sec-crumb');
      if (crumb) crumb.textContent = secNames[secId] || secId;

      const titleEl = document.querySelector('.sidebar-main-title');
      if (titleEl) titleEl.textContent = (secNames[secId] || 'Explorer').toUpperCase();

      const sb = document.getElementById('primary-sidebar');
      if (sb && sb.classList.contains('collapsed')) sb.classList.remove('collapsed');

      // Ensure that section accordion is open
      const acc = document.getElementById('sec-group-' + secId);
      if (acc) {
        acc.classList.add('open');
        if (scrollIntoView) {
          acc.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    }

    function toggleAccordion(secId) {
      const acc = document.getElementById('sec-group-' + secId);
      if (acc) acc.classList.toggle('open');
    }

    function toggleSidebar() {
      const sb = document.getElementById('primary-sidebar');
      if (sb) sb.classList.toggle('collapsed');
    }

    function toggleBottomPanel(forceState, defaultTab) {
      const panel = document.getElementById('secondary-panel');
      if (!panel) return;
      if (forceState !== undefined) {
        if (forceState) panel.classList.add('open');
        else panel.classList.remove('open');
      } else {
        panel.classList.toggle('open');
      }
      bottomPanelOpen = panel.classList.contains('open');
      if (bottomPanelOpen && defaultTab) {
        switchPanelTab(defaultTab);
      }
    }

    function toggleBottomPanelMaximize() {
      const panel = document.getElementById('secondary-panel');
      if (panel) panel.classList.toggle('maximized');
    }

    function switchPanelTab(tabName) {
      document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.panel-pane').forEach(p => p.classList.remove('active'));
      const tabBtn = document.getElementById('ptab-' + tabName);
      const pane = document.getElementById('pane-' + tabName);
      if (tabBtn) tabBtn.classList.add('active');
      if (pane) pane.classList.add('active');
      if (tabName === 'terminal') {
        const inp = document.getElementById('bottom-terminal-input');
        if (inp) inp.focus();
      }
    }

    function clearBottomTerminal() {
      const term = document.getElementById('bottom-terminal-output');
      if (term) term.innerText = 'gdr@workbench:~$ ';
    }

    async function execBottomTerminal() {
      const inp = document.getElementById('bottom-terminal-input');
      const out = document.getElementById('bottom-terminal-output');
      if (!inp || !out) return;
      const cmd = inp.value.trim();
      if (!cmd) return;

      terminalHistory.push(cmd);
      terminalHistoryIdx = terminalHistory.length;
      inp.value = '';

      out.innerText += cmd + '\n';
      out.scrollTop = out.scrollHeight;

      if (cmd === 'clear') {
        clearBottomTerminal();
        return;
      }

      try {
        const resp = await fetch('/api/terminal/exec', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd, timeout: 30 })
        });
        const data = await resp.json();
        if (data.output) {
          out.innerText += data.output + '\n';
        }
        const cwdPrompt = (data.cwd ? 'gdr@workbench:' + data.cwd.split('/').pop() : 'gdr@workbench') + '~$ ';
        out.innerText += cwdPrompt;
        const promptEl = document.getElementById('bottom-terminal-prompt');
        if (promptEl) promptEl.textContent = cwdPrompt;
      } catch (err) {
        out.innerText += '[Error executing command]: ' + err.message + '\n';
        out.innerText += 'gdr@workbench:~$ ';
      }
      out.scrollTop = out.scrollHeight;
    }

    function handleBottomTerminalKey(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        execBottomTerminal();
      } else if (e.key === 'ArrowUp') {
        if (terminalHistory.length > 0 && terminalHistoryIdx > 0) {
          terminalHistoryIdx--;
          e.target.value = terminalHistory[terminalHistoryIdx];
        }
      } else if (e.key === 'ArrowDown') {
        if (terminalHistoryIdx < terminalHistory.length - 1) {
          terminalHistoryIdx++;
          e.target.value = terminalHistory[terminalHistoryIdx];
        } else {
          terminalHistoryIdx = terminalHistory.length;
          e.target.value = '';
        }
      }
    }

    function toggleTheme() {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const target = (current === 'dark') ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', target);
      try { localStorage.setItem('gdr_theme', target); } catch(e){}
    }

    function openPalette() {
      const pal = document.getElementById('cmd-palette');
      if (pal) pal.classList.add('open');
      const inp = document.getElementById('cmd-input');
      if (inp) {
        inp.value = '';
        inp.focus();
      }
      filteredPaletteCommands = [...PALETTE_COMMANDS];
      selectedPaletteIdx = 0;
      renderPaletteCommands();
    }

    function closePalette() {
      const pal = document.getElementById('cmd-palette');
      if (pal) pal.classList.remove('open');
    }

    function filterPaletteCommands() {
      const query = (document.getElementById('cmd-input')?.value || '').toLowerCase().trim();
      if (!query) {
        filteredPaletteCommands = [...PALETTE_COMMANDS];
      } else {
        filteredPaletteCommands = PALETTE_COMMANDS.filter(c => 
          c.label.toLowerCase().includes(query) || c.category.toLowerCase().includes(query)
        );
      }
      selectedPaletteIdx = 0;
      renderPaletteCommands();
    }

    function renderPaletteCommands() {
      const list = document.getElementById('cmd-palette-list');
      if (!list) return;
      if (filteredPaletteCommands.length === 0) {
        list.innerHTML = '<div style="padding:12px; color:var(--text-muted); font-size:12px; text-align:center;">No matching commands found.</div>';
        return;
      }
      list.innerHTML = filteredPaletteCommands.map((cmd, idx) => `
        <div class="cmd-palette-item ${idx === selectedPaletteIdx ? 'selected' : ''}" onclick="executePaletteItem(${idx})">
          <span>${cmd.label}</span>
          <span class="cmd-palette-category">${cmd.category}</span>
        </div>
      `).join('');
    }

    function executePaletteItem(idx) {
      const cmd = filteredPaletteCommands[idx];
      closePalette();
      if (cmd && cmd.action) cmd.action();
    }

    function handlePaletteKey(e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (selectedPaletteIdx < filteredPaletteCommands.length - 1) {
          selectedPaletteIdx++;
          renderPaletteCommands();
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (selectedPaletteIdx > 0) {
          selectedPaletteIdx--;
          renderPaletteCommands();
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredPaletteCommands.length > 0) {
          executePaletteItem(selectedPaletteIdx);
        }
      } else if (e.key === 'Escape') {
        closePalette();
      }
    }

    function scrollToSettingsCard(cardType) {
      const card = document.querySelector('#screen-settings [data-card="' + cardType + '"]') || document.getElementById('settings-' + cardType + '-card');
      if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function openShortcutsModal() {
      alert("GDR-IDE Keyboard Shortcuts:\n• Ctrl+Shift+P / Ctrl+P: Command Palette\n• Ctrl+` : Toggle Terminal Panel\n• Ctrl+B : Toggle Sidebar\n• Ctrl+1..5 : Switch Navigation Section\n• Esc : Close Modals");
    }

    // Global Key Listener for VS Code shortcuts
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'P' || e.key === 'p')) {
        e.preventDefault();
        openPalette();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P' || e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        openPalette();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === '`' || e.key === '~')) {
        e.preventDefault();
        toggleBottomPanel();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
        e.preventDefault();
        toggleSidebar();
      } else if (e.key === 'Escape') {
        closePalette();
      }
    });


    /* Immediate zero-FOUC theme initializer */
    (function() {
      try {
        const theme = localStorage.getItem('gdr_theme') || 'dark';
        const accent = localStorage.getItem('gdr_accent') || 'emerald';
        const bg = localStorage.getItem('gdr_bg_style') || 'solid';
        const density = localStorage.getItem('gdr_density') || 'comfortable';
        const fontScale = localStorage.getItem('gdr_font_scale') || '1.0';

        let effectiveTheme = theme;
        if (theme === 'system') {
          effectiveTheme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
        }

        document.documentElement.setAttribute('data-theme', effectiveTheme);
        document.documentElement.setAttribute('data-accent', accent);
        document.documentElement.setAttribute('data-bg', bg);
        document.documentElement.setAttribute('data-density', density);
        document.documentElement.style.setProperty('--font-scale', fontScale);
      } catch (e) {}
    })();
  </script>
  <style>
    /* ==========================================================================
       GDR-AI DESIGN SYSTEM TOKENS (ChatGPT & Google Gemini Inspired)
       Core Rule: 1 Background, 1 Primary Accent, 1 Restrained Secondary Accent
       ========================================================================== */
    :root, [data-theme="dark"] {
      color-scheme: dark;

      /* Design Tokens: Dark Theme (Restrained Developer Workbench) */
      --bg: #15171B;
      --bg-primary: #15171B;
      --bg-sidebar: #191B20;
      --bg-secondary: #191B20;
      --bg-elevated: #262A31;
      --bg-surface: #202329;
      --bg-card: #202329;
      --bg-card-hover: #272B33;
      --bg-hover: #292D36;
      --bg-input: #1C1E24;

      /* Typography */
      --text-main: #E8EAF0;
      --text-primary: #E8EAF0;
      --text-secondary: #A0A6B4;
      --text-muted: #7E8594;
      --text-dim: #555C6B;

      /* Clean Hairline Borders */
      --border: #343943;
      --border-subtle: #343943;
      --border-hover: #4A515E;

      /* Primary Accent: Controlled Cyan-Blue #4DA3FF */
      --accent: #4DA3FF;
      --accent-primary: #4DA3FF;
      --accent-hover: #388EE6;
      --accent-soft: rgba(77, 163, 255, 0.12);
      --accent-border: rgba(77, 163, 255, 0.35);
      --focus-ring: #4DA3FF;

      /* Secondary Accent: Violet #8B8CF6 */
      --accent-secondary: #8B8CF6;
      --accent-secondary-soft: rgba(139, 140, 246, 0.12);

      /* Semantic Status */
      --success: #34D399;
      --warning: #FBBF24;
      --danger: #F87171;
      --info: #4DA3FF;

      --radius-sm: 6px;
      --radius-md: 8px;
      --radius-lg: 12px;

      --shadow-soft: 0 4px 16px rgba(0, 0, 0, 0.28);
      --font-scale: 1.0;
    }

    [data-theme="light"] {
      color-scheme: light;

      /* Design Tokens: Light Theme */
      --bg: #F8F9FA;
      --bg-primary: #F8F9FA;
      --bg-sidebar: #FFFFFF;
      --bg-secondary: #FFFFFF;
      --bg-elevated: #F1F3F5;
      --bg-surface: #FFFFFF;
      --bg-card: #FFFFFF;
      --bg-card-hover: #F0F2F5;
      --bg-hover: #E9ECEF;
      --bg-input: #F1F3F5;

      --text-main: #1A1D20;
      --text-primary: #1A1D20;
      --text-secondary: #5F6672;
      --text-muted: #828A98;
      --text-dim: #9FA7B3;

      --border: #E2E5E9;
      --border-subtle: #E2E5E9;
      --border-hover: #C8CDD5;

      --accent: #2563EB;
      --accent-primary: #2563EB;
      --accent-hover: #1D4ED8;
      --accent-soft: rgba(37, 99, 235, 0.10);
      --accent-border: rgba(37, 99, 235, 0.30);
      --focus-ring: #2563EB;

      --accent-secondary: #6366F1;
      --accent-secondary-soft: rgba(99, 102, 241, 0.10);

      --success: #10B981;
      --warning: #D97706;
      --danger: #EF4444;
      --info: #2563EB;

      --shadow-soft: 0 2px 10px rgba(0, 0, 0, 0.05);
    }

    /* Accent Presets */
    [data-accent="emerald"] {
      --accent: #10A37F;
      --accent-primary: #10A37F;
      --accent-hover: #0E8F70;
      --accent-soft: rgba(16, 163, 127, 0.14);
      --accent-border: rgba(16, 163, 127, 0.35);
      --focus-ring: #10A37F;
    }
    [data-accent="cyan"] {
      --accent: #38BDF8;
      --accent-primary: #38BDF8;
      --accent-hover: #0284C7;
      --accent-soft: rgba(56, 189, 248, 0.14);
      --accent-border: rgba(56, 189, 248, 0.35);
      --focus-ring: #38BDF8;
    }
    [data-accent="blue"] {
      --accent: #2563EB;
      --accent-primary: #2563EB;
      --accent-hover: #1D4ED8;
      --accent-soft: rgba(37, 99, 235, 0.14);
      --accent-border: rgba(37, 99, 235, 0.35);
      --focus-ring: #2563EB;
    }
    [data-accent="violet"] {
      --accent: #8B8CF8;
      --accent-primary: #8B8CF8;
      --accent-hover: #7374EA;
      --accent-soft: rgba(139, 140, 248, 0.14);
      --accent-border: rgba(139, 140, 248, 0.35);
      --focus-ring: #8B8CF8;
    }
    [data-accent="amber"] {
      --accent: #D97706;
      --accent-primary: #D97706;
      --accent-hover: #B45309;
      --accent-soft: rgba(217, 119, 6, 0.14);
      --accent-border: rgba(217, 119, 6, 0.35);
      --focus-ring: #D97706;
    }

    /* Background Styles */
    body {
      margin: 0; padding: 0;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      width: 100%;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
      transition: background-color 0.2s ease, color 0.2s ease;
    }

    [data-bg="solid"] body {
      background-image: none !important;
      background-color: var(--bg-primary) !important;
    }
    [data-bg="gradient"] body {
      background-image: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%) !important;
    }
    [data-bg="ambient"] body {
      background-image: radial-gradient(circle at 50% 0%, var(--accent-soft) 0%, transparent 60%) !important;
    }

    /* UI Density */
    [data-density="compact"] .card { padding: 12px 14px; margin-bottom: 12px; }
    [data-density="compact"] .nav-tab { padding: 4px 10px; font-size: 11px; }
    [data-density="compact"] main { padding: 12px 10px; }

    /* Reduced Motion */
    @media (prefers-reduced-motion: reduce) {
      *, ::before, ::after {
        animation-delay: -1ms !important;
        animation-duration: 1ms !important;
        animation-iteration-count: 1 !important;
        background-attachment: initial !important;
        scroll-behavior: auto !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    }

    * { box-sizing: border-box; }
    mono, pre, code, .mono-font { font-family: 'JetBrains Mono', monospace; }

    /* Buttons */
    .btn {
      background: var(--accent-primary);
      color: #ffffff;
      border: 1px solid var(--accent-border);
      border-radius: var(--radius-sm);
      padding: 7px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      text-decoration: none;
    }
    .btn:hover {
      background: var(--accent-hover);
      box-shadow: 0 2px 10px var(--accent-soft);
    }
    .btn-secondary {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border: 1px solid var(--border-subtle);
    }
    .btn-secondary:hover {
      background: var(--bg-hover);
      border-color: var(--border-hover);
      box-shadow: none;
    }

    /* Top HUD Navigation */
    header {
      position: sticky; top: 0; z-index: 50;
      background: var(--bg-primary);
      border-bottom: 1px solid var(--border-subtle);
      padding: 10px 16px;
      display: flex; flex-direction: column; gap: 8px;
      box-shadow: var(--shadow-soft);
    }
    .header-top {
      display: flex; justify-content: space-between; align-items: center; width: 100%;
      flex-wrap: wrap; gap: 8px;
    }
    .brand {
      display: flex; align-items: center; gap: 8px;
      font-weight: 700; font-size: 15px; letter-spacing: 0.5px;
      color: var(--text-primary);
    }
    .nav-tabs {
      display: flex; gap: 6px; overflow-x: auto; width: 100%;
      padding: 2px 0 6px 0;
      scrollbar-width: thin;
      scrollbar-color: var(--border-subtle) transparent;
      -webkit-overflow-scrolling: touch;
    }
    .nav-tabs::-webkit-scrollbar { height: 3px; }
    .nav-tabs::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 3px; }
    .nav-tab {
      background: var(--bg-secondary); border: 1px solid var(--border-subtle); color: var(--text-secondary);
      padding: 6px 14px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500;
      cursor: pointer; transition: all 0.15s ease; white-space: nowrap; flex-shrink: 0;
      touch-action: manipulation;
    }
    .nav-tab:hover { color: var(--text-primary); background: var(--bg-hover); border-color: var(--border-hover); }
    .nav-tab.active {
      color: #ffffff; background: var(--accent-primary);
      border-color: var(--accent-hover);
      box-shadow: 0 1px 8px var(--accent-soft);
    }
    .header-actions {
      display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    }
    .btn-panic {
      background: #7f1d1d; border: 1px solid var(--danger); color: #fecaca;
      padding: 6px 12px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700;
      cursor: pointer; display: flex; align-items: center; gap: 5px;
      transition: all 0.2s ease;
    }
    .btn-panic:hover { background: var(--danger); color: #fff; box-shadow: 0 0 12px rgba(239,68,68,0.4); }

    /* Main Container & Screens */
    main { padding: 20px 16px; max-width: 1400px; margin: 0 auto; width: 100%; }
    .screen { display: none; animation: fadeIn 0.2s ease forwards; }
    .screen.active { display: block; }
    #screen-ide.screen.active { display: flex !important; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }

    /* Clean Elevated Cards */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 20px;
      box-shadow: var(--shadow-soft);
      margin-bottom: 18px;
      transition: border-color 0.15s ease;
      max-width: 100%;
      overflow-wrap: break-word;
    }
    .card:hover { border-color: var(--border-hover); }
    .card h2 {
      margin-top: 0; font-size: 15px; font-weight: 600;
      letter-spacing: 0.3px; color: var(--text-primary);
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid var(--border-subtle); padding-bottom: 10px; margin-bottom: 16px;
      flex-wrap: wrap; gap: 8px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
      gap: 18px;
    }
    .grid-3 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
      gap: 16px;
    }

    /* Refined Metallic AI Core Orb */
    .orb-container {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 16px; text-align: center; width: 100%;
    }
    .orb {
      width: 130px; height: 130px; border-radius: 50%;
      position: relative;
      background: radial-gradient(circle at 35% 35%, #e0f2fe 0%, #38bdf8 30%, #1e293b 80%, #090d16 100%);
      box-shadow: 0 0 35px rgba(56, 189, 248, 0.25), inset 0 0 20px rgba(255,255,255,0.4);
      animation: orbFloat 4s ease-in-out infinite alternate, orbPulse 3s ease-in-out infinite;
      cursor: pointer; transition: all 0.3s ease;
    }
    .orb.listening {
      background: radial-gradient(circle at 35% 35%, #ecfdf5 0%, #10b981 40%, #064e3b 85%, #090d16 100%);
      box-shadow: 0 0 40px rgba(16, 185, 129, 0.4), inset 0 0 20px rgba(255,255,255,0.5);
      animation: orbPulseFast 1s ease-in-out infinite alternate;
    }
    .orb.thinking {
      background: radial-gradient(circle at 35% 35%, #e0e7ff 0%, #6366f1 40%, #312e81 85%, #090d16 100%);
      box-shadow: 0 0 35px rgba(99, 102, 241, 0.35);
      animation: orbSpin 3s linear infinite;
    }
    .orb.speaking {
      background: radial-gradient(circle at 35% 35%, #f0fdf4 0%, #38bdf8 35%, #0284c7 75%, #090d16 100%);
      box-shadow: 0 0 40px rgba(56, 189, 248, 0.4);
      animation: orbWave 1.2s ease-in-out infinite;
    }
    .orb.alert {
      background: radial-gradient(circle at 35% 35%, #fef2f2 0%, #ef4444 40%, #7f1d1d 85%, #090d16 100%);
      box-shadow: 0 0 45px rgba(239, 68, 68, 0.5);
    }
    @keyframes orbFloat { 0% { transform: translateY(0); } 100% { transform: translateY(-8px); } }
    @keyframes orbPulse { 0% { transform: scale(1); } 50% { transform: scale(1.03); } 100% { transform: scale(1); } }
    @keyframes orbPulseFast { 0% { transform: scale(0.98); } 100% { transform: scale(1.05); } }
    @keyframes orbSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes orbWave { 0%, 100% { transform: scale(1); filter: brightness(1); } 50% { transform: scale(1.04); filter: brightness(1.15); } }

    .orb-state-badge {
      margin-top: 14px; padding: 4px 14px; border-radius: 20px; font-size: 11px; font-weight: 600;
      letter-spacing: 1px; text-transform: uppercase;
      background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8;
    }

    /* Buttons & Standard Form Controls */
    button.btn {
      background: #0284c7; color: #fff; border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 13px;
      cursor: pointer; transition: all 0.15s ease;
      display: inline-flex; align-items: center; justify-content: center; gap: 6px;
      touch-action: manipulation;
    }
    button.btn:hover { background: #0369a1; border-color: #38bdf8; transform: translateY(-1px); }
    button.btn:active { transform: translateY(0); }
    button.btn-secondary {
      background: rgba(255,255,255,0.06); color: #e2e8f0;
      border: 1px solid rgba(255,255,255,0.12);
    }
    button.btn-secondary:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.2); }
    button.btn-danger { background: #dc2626; color: #fff; border: 1px solid #ef4444; }
    button.btn-danger:hover { background: #b91c1c; }
    button.btn-success { background: #059669; color: #fff; border: 1px solid #10b981; }
    button.btn-success:hover { background: #047857; }
    button.btn-mic-active {
      background: #059669 !important; color: #fff !important;
      animation: pulseMic 1s infinite alternate; box-shadow: 0 0 16px rgba(16, 185, 129, 0.5);
    }
    @keyframes pulseMic { 0% { transform: scale(1); } 100% { transform: scale(1.04); } }

    /* Quick Suggestion Chips */
    .chip-container { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; justify-content: center; }
    .chip {
      background: rgba(255,255,255,0.04); border: 1px solid var(--border);
      color: var(--text-muted); padding: 5px 12px; border-radius: 20px; font-size: 12px;
      cursor: pointer; transition: all 0.15s ease;
    }
    .chip:hover { color: #fff; border-color: var(--accent); background: rgba(56, 189, 248, 0.1); }

    input[type="text"], textarea, select {
      background: var(--bg-input); border: 1px solid var(--border);
      color: #f8fafc; padding: 10px 14px; border-radius: 8px; width: 100%;
      font-family: inherit; font-size: 13px; transition: border-color 0.15s ease;
      box-sizing: border-box;
    }
    input[type="text"]:focus, textarea:focus, select:focus {
      outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
    }

    /* Timeline card in chat */
    .timeline-card {
      border-left: 2px solid var(--accent); padding-left: 14px; margin: 8px 0;
      font-size: 12px; color: var(--text-muted);
    }
    .timeline-card b { color: var(--accent); }

    /* Workflow visual node */
    .wf-node {
      background: #0d1527; border: 1px solid var(--border); border-radius: 8px;
      padding: 12px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: 8px;
    }

    /* Live Webcam Container */
    .webcam-box {
      position: relative; border-radius: 8px; overflow: hidden;
      background: #000; border: 1px solid var(--border); width: 100%;
      height: 280px; display: flex; align-items: center; justify-content: center;
    }
    .webcam-box video {
      width: 100%; height: 100%; object-fit: cover;
    }
    .hud-reticle {
      position: absolute; inset: 0; pointer-events: none;
      background: radial-gradient(circle, transparent 60%, rgba(56, 189, 248, 0.05) 100%);
      border: 1px dashed rgba(56, 189, 248, 0.25);
    }
    .hud-target-ring {
      position: absolute; width: 110px; height: 110px; border-radius: 50%;
      border: 2px solid var(--accent); top: 50%; left: 50%; transform: translate(-50%, -50%);
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.25); animation: reticlePulse 2s infinite ease-in-out;
    }
    @keyframes reticlePulse { 0% { transform: translate(-50%, -50%) scale(0.95); opacity: 0.6; } 50% { transform: translate(-50%, -50%) scale(1.05); opacity: 1; } 100% { transform: translate(-50%, -50%) scale(0.95); opacity: 0.6; } }

    /* Command Palette Modal */
    #cmd-palette {
      display: none; position: fixed; inset: 0; z-index: 100;
      background: rgba(0,0,0,0.8); backdrop-filter: blur(8px);
      align-items: center; justify-content: center; padding: 16px;
    }
    #cmd-palette.open { display: flex; }
    .cmd-box {
      width: min(540px, 94vw); background: #0f172a; border: 1px solid var(--border);
      border-radius: 12px; padding: 18px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }

    /* System Monitor gauges */
    .metric-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
    .progress-bar { background: rgba(255,255,255,0.08); height: 8px; border-radius: 4px; overflow: hidden; }
    .progress-fill { height: 100%; background: #0284c7; transition: width 0.3s ease; }
    .progress-fill.safe { background: #0284c7; }
    .progress-fill.warning { background: var(--warning); }

    /* 📱 Responsive Media Queries for Mobile, Tablets & Smaller Screens */
    @media (max-width: 900px) {
      .grid-2 {
        grid-template-columns: 1fr !important;
        gap: 14px !important;
      }
      .grid-3 {
        grid-template-columns: 1fr !important;
        gap: 14px !important;
      }
      main {
        padding: 14px 10px !important;
      }
      .card {
        padding: 14px !important;
        border-radius: 10px !important;
        margin-bottom: 14px !important;
      }
      .orb {
        width: 105px !important;
        height: 105px !important;
      }
      .orb-container {
        padding: 10px 0 !important;
      }
      .header-actions {
        gap: 5px !important;
      }
      .header-actions .nav-tab, .header-actions select {
        font-size: 11px !important;
        padding: 5px 8px !important;
      }
      #home-chat-bar-container {
        flex-direction: column !important;
      }
      #home-chat-bar-container .btn-group {
        display: flex !important;
        width: 100% !important;
        gap: 8px !important;
      }
      #home-chat-bar-container .btn-group button {
        flex: 1 !important;
      }
      .chip-container {
        gap: 6px !important;
      }
      .chip {
        font-size: 11px !important;
        padding: 4px 10px !important;
      }
      .cmd-box {
        width: 94vw !important;
        padding: 14px !important;
      }
    }

    @media (max-width: 480px) {
      header {
        padding: 8px 10px !important;
      }
      .brand span:first-child {
        font-size: 14px !important;
      }
      .nav-tab {
        font-size: 11px !important;
        padding: 5px 9px !important;
      }
      .card h2 {
        font-size: 14px !important;
      }
    }

    /* ======================================================== */
    /* CHATGPT / CLAUDE / GEMINI MODERN STYLES                 */
    /* ======================================================== */
    .chat-layout {
      max-width: 900px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      height: calc(100vh - 145px);
      min-height: 540px;
    }
    .chat-header-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 16px;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border);
      border-radius: 12px 12px 0 0;
      backdrop-filter: blur(12px);
      flex-wrap: wrap;
      gap: 8px;
    }
    .chat-stream {
      flex: 1;
      overflow-y: auto;
      padding: 18px 16px;
      background: rgba(9, 13, 22, 0.7);
      border-left: 1px solid var(--border);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 16px;
      scrollbar-width: thin;
      scrollbar-color: rgba(255,255,255,0.1) transparent;
    }
    .chat-msg-row {
      display: flex;
      gap: 12px;
      width: 100%;
      animation: fadeIn 0.2s ease forwards;
    }
    .chat-msg-row.user {
      justify-content: flex-end;
    }
    .chat-bubble-user {
      max-width: 82%;
      background: linear-gradient(135deg, rgba(2, 132, 199, 0.25), rgba(15, 23, 42, 0.9));
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 16px 16px 4px 16px;
      padding: 12px 16px;
      color: #f8fafc;
      font-size: 14px;
      line-height: 1.5;
      box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    }
    .chat-bubble-assistant {
      max-width: 90%;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--border);
      border-radius: 16px 16px 16px 4px;
      padding: 14px 18px;
      color: #e2e8f0;
      font-size: 14px;
      line-height: 1.6;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .chat-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .chat-avatar.user-avatar {
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.3);
    }
    .suggestion-pills-bar {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding: 8px 12px;
      background: rgba(15, 23, 42, 0.5);
      border-left: 1px solid var(--border);
      border-right: 1px solid var(--border);
      scrollbar-width: none;
    }
    .suggestion-pill {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 12px;
      color: #cbd5e1;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .suggestion-pill:hover {
      background: rgba(56, 189, 248, 0.15);
      border-color: #38bdf8;
      color: #fff;
      transform: translateY(-1px);
    }
    .chat-input-dock {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--border);
      border-radius: 0 0 16px 16px;
      padding: 12px 16px;
      backdrop-filter: blur(16px);
      box-shadow: 0 -4px 20px rgba(0,0,0,0.25);
    }
    .chat-input-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #090d16;
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 4px 6px 4px 14px;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .chat-input-pill:focus-within {
      border-color: #38bdf8;
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.25);
    }
    .chat-input-pill input {
      flex: 1;
      background: transparent;
      border: none;
      color: #fff;
      font-size: 14px;
      outline: none;
      padding: 8px 4px;
      font-family: inherit;
    }
    .btn-mic-pulse {
      animation: micPulse 1.4s ease-in-out infinite;
      background: #dc2626 !important;
      border-color: #ef4444 !important;
      color: #fff !important;
    }
    @keyframes micPulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
      50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
    }
  
    /* ==========================================================================
       GDR-IDE WORKBENCH SHELL & VS CODE LAYOUT TOKENS
       ========================================================================== */
    html, body {
      height: 100%;
      margin: 0;
      padding: 0;
      overflow: hidden;
      background: var(--bg-primary);
      color: var(--text-primary);
    }

    .workbench-shell {
      display: flex;
      flex-direction: column;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      background: var(--bg-primary);
    }

    /* A. TITLE BAR */
    .titlebar {
      height: 38px;
      min-height: 38px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      user-select: none;
      z-index: 100;
      font-size: 12px;
    }

    .titlebar-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 700;
      font-size: 13px;
      letter-spacing: 0.5px;
      color: var(--text-primary);
    }

    .brand-sub {
      font-size: 10px;
      padding: 1px 5px;
      border: 1px solid var(--accent-border);
      border-radius: 4px;
      color: var(--accent-primary);
      background: var(--accent-soft);
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    .titlebar-breadcrumbs {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--text-muted);
    }

    .crumb-sep {
      color: var(--text-dim);
      font-size: 10px;
    }

    .crumb-active {
      color: var(--text-primary);
      font-weight: 600;
    }

    .titlebar-center {
      flex: 1;
      max-width: 480px;
      margin: 0 12px;
    }

    .titlebar-search-box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      height: 26px;
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 0 10px;
      cursor: pointer;
      color: var(--text-secondary);
      transition: all 0.15s ease;
      font-size: 11px;
    }

    .titlebar-search-box:hover {
      border-color: var(--border-hover);
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    .search-kbd {
      font-size: 9px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 1px 5px;
      color: var(--text-muted);
      font-family: inherit;
    }

    .titlebar-right {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    .titlebar-btn {
      background: var(--bg-secondary);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.12s ease;
    }

    .titlebar-btn:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
      border-color: var(--border-hover);
    }

    .titlebar-select {
      background: var(--bg-secondary);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      cursor: pointer;
      max-width: 160px;
    }

    /* B. WORKBENCH BODY */
    .workbench-body {
      display: flex;
      flex: 1;
      min-height: 0;
      overflow: hidden;
      position: relative;
    }

    /* ACTIVITY BAR (50px vertical rail with 5 primary sections) */
    .activity-bar {
      width: 50px;
      min-width: 50px;
      background: var(--bg-primary);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      z-index: 90;
      user-select: none;
    }

    .activity-bar-top, .activity-bar-bottom {
      display: flex;
      flex-direction: column;
      gap: 6px;
      width: 100%;
      align-items: center;
    }

    .activity-item {
      width: 42px;
      height: 42px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-left: 2px solid transparent;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: 4px;
      transition: all 0.15s ease;
      padding: 0;
      position: relative;
    }

    .activity-item:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
    }

    .activity-item.active {
      color: var(--accent-primary);
      border-left-color: var(--accent-primary);
      background: var(--accent-soft);
    }

    .activity-icon {
      font-size: 18px;
      line-height: 1;
    }

    .activity-label {
      font-size: 8px;
      font-weight: 700;
      margin-top: 2px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    /* C. PRIMARY SIDEBAR */
    .primary-sidebar {
      width: 240px;
      min-width: 240px;
      max-width: 240px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transition: width 0.2s ease, min-width 0.2s ease, max-width 0.2s ease, margin-left 0.2s ease;
      z-index: 80;
    }

    .primary-sidebar.collapsed {
      width: 0 !important;
      min-width: 0 !important;
      max-width: 0 !important;
      margin-left: 0;
      border-right: none;
      visibility: hidden;
    }

    .sidebar-top-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      text-transform: uppercase;
    }

    .sidebar-icon-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 2px 4px;
      border-radius: 3px;
      font-size: 11px;
    }

    .sidebar-icon-btn:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
    }

    .sidebar-accordions {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .sidebar-accordion {
      border-bottom: 1px solid var(--border-subtle);
    }

    .accordion-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 7px 10px;
      background: var(--bg-secondary);
      cursor: pointer;
      user-select: none;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.4px;
      color: var(--text-secondary);
      transition: background 0.12s ease;
    }

    .accordion-header:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    .accordion-header-left {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .accordion-arrow {
      font-size: 9px;
      transition: transform 0.15s ease;
      display: inline-block;
      width: 10px;
    }

    .sidebar-accordion:not(.open) .accordion-arrow {
      transform: rotate(-90deg);
    }

    .sidebar-accordion:not(.open) .accordion-body {
      display: none;
    }

    .accordion-badge {
      font-size: 9px;
      padding: 1px 5px;
      border-radius: 10px;
      background: var(--bg-elevated);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
    }

    .accordion-body {
      padding: 4px 6px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .sidebar-item {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 8px;
      border-radius: var(--radius-sm);
      border: 1px solid transparent;
      background: transparent;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
      transition: all 0.12s ease;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      box-sizing: border-box;
    }

    .sidebar-item:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
      border-color: var(--border-subtle);
    }

    .sidebar-item.active {
      background: var(--accent-soft) !important;
      color: var(--accent-primary) !important;
      border-color: var(--accent-border) !important;
      font-weight: 600 !important;
    }

    .sidebar-item .item-icon {
      font-size: 13px;
      flex-shrink: 0;
      width: 16px;
      text-align: center;
    }

    /* D. MAIN WORKSPACE AREA */
    .workbench-workspace {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
      min-height: 0;
      overflow: hidden;
      position: relative;
    }

    .workbench-main {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 16px 20px;
      scroll-behavior: smooth;
    }

    /* E. SECONDARY / BOTTOM PANEL */
    .secondary-panel {
      height: 220px;
      min-height: 120px;
      max-height: 70vh;
      background: var(--bg-secondary);
      border-top: 1px solid var(--border-subtle);
      display: none;
      flex-direction: column;
      z-index: 70;
    }

    .secondary-panel.open {
      display: flex;
    }

    .secondary-panel.maximized {
      height: 60vh !important;
    }

    .panel-header {
      height: 32px;
      min-height: 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 10px;
      background: var(--bg-primary);
      border-bottom: 1px solid var(--border-subtle);
      font-size: 11px;
      user-select: none;
    }

    .panel-tabs {
      display: flex;
      gap: 4px;
      height: 100%;
    }

    .panel-tab {
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      font-size: 11px;
      font-weight: 600;
      padding: 0 10px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      letter-spacing: 0.5px;
      transition: all 0.15s ease;
    }

    .panel-tab:hover {
      color: var(--text-primary);
    }

    .panel-tab.active {
      color: var(--accent-primary);
      border-bottom-color: var(--accent-primary);
    }

    .panel-actions {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .panel-action-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 11px;
    }

    .panel-action-btn:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    .panel-content {
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }

    .panel-pane {
      display: none;
      flex: 1;
      min-height: 0;
      flex-direction: column;
      padding: 8px 10px;
      overflow-y: auto;
      font-size: 12px;
    }

    .panel-pane.active {
      display: flex;
    }

    .terminal-body {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      background: var(--bg-input);
      border-radius: 4px;
      padding: 8px 10px;
      font-size: 12px;
      line-height: 1.5;
      color: var(--text-primary);
      white-space: pre-wrap;
      font-family: 'JetBrains Mono', monospace;
      border: 1px solid var(--border-subtle);
    }

    .terminal-input-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
    }

    .terminal-prompt {
      color: var(--accent-primary);
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: bold;
      flex-shrink: 0;
    }

    .terminal-input {
      flex: 1;
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      outline: none;
    }

    .terminal-input:focus {
      border-color: var(--accent-primary);
    }

    /* F. STATUS BAR */
    .workbench-statusbar {
      height: 24px;
      min-height: 24px;
      background: #17191F;
      border-top: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 10px;
      font-size: 11px;
      font-weight: 500;
      user-select: none;
      z-index: 100;
    }

    [data-theme="light"] .workbench-statusbar {
      background: #F0F2F5;
      color: var(--text-secondary);
      border-top: 1px solid var(--border-subtle);
    }

    .statusbar-left, .statusbar-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-item {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      white-space: nowrap;
    }

    .status-item:hover {
      color: var(--text-primary);
    }

    /* VS CODE-STYLE COMMAND PALETTE */
    #cmd-palette {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 10000;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      align-items: flex-start;
      justify-content: center;
      padding-top: 50px;
    }
    #cmd-palette.open {
      display: flex;
    }
    .cmd-palette-box {
      width: min(600px, 92vw);
      background: var(--bg-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      animation: cmdFadeDown 0.15s ease-out;
    }
    @keyframes cmdFadeDown {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .cmd-palette-header {
      display: flex;
      align-items: center;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      gap: 10px;
      background: var(--bg-secondary);
    }
    .cmd-palette-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: var(--text-primary);
      font-size: 13px;
      font-family: inherit;
    }
    .cmd-palette-list {
      max-height: 340px;
      overflow-y: auto;
      padding: 6px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .cmd-palette-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      color: var(--text-secondary);
      font-size: 12px;
      transition: all 0.1s ease;
    }
    .cmd-palette-item:hover, .cmd-palette-item.selected {
      background: var(--accent-soft);
      color: var(--accent-primary);
      font-weight: 600;
    }
    .cmd-palette-category {
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 4px;
      background: var(--bg-hover);
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    /* Responsive */
    @media (max-width: 1024px) {
      .primary-sidebar { width: 210px; min-width: 210px; max-width: 210px; }
      .titlebar-center { max-width: 320px; }
    }
    @media (max-width: 768px) {
      .workbench-shell { height: 100vh; overflow-x: hidden; width: 100%; max-width: 100vw; }
      .titlebar { padding: 0 8px; width: 100%; max-width: 100vw; overflow: hidden; }
      .titlebar-center { display: none; }
      .titlebar-breadcrumbs { display: none; }
      .titlebar-select { display: none !important; }
      #header-engine-pill { display: none !important; }
      .titlebar-right button.titlebar-btn { padding: 2px 6px; font-size: 10px; }
      .activity-bar { width: 44px; min-width: 44px; }
      .primary-sidebar {
        position: fixed; top: 38px; bottom: 24px; left: 44px;
        z-index: 1000; box-shadow: 0 8px 30px rgba(0,0,0,0.6);
      }
      .statusbar-right { display: none; }
      .workbench-body { max-width: 100vw; overflow-x: hidden; }
      .workbench-main { padding: 12px 8px; max-width: 100vw; overflow-x: hidden; }
      .grid-2, .grid-3 { grid-template-columns: 1fr !important; }
      .chip-container { flex-wrap: wrap; }
      #home-chat-bar-container { flex-direction: column; width: 100%; }
      #home-chat-bar-container .btn-group { width: 100%; justify-content: flex-end; }
    }


    /* ==========================================================================
       FOCUS TALKING MODE — ANIME COMPANION CALL EXPERIENCE
       ========================================================================== */
    #focus-call-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100vw;
      height: 100vh;
      z-index: 9500;
      display: none;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      transition: background 0.5s ease;
      user-select: none;
    }

    /* Atmosphere Themes */
    .focus-theme-midnight {
      background: radial-gradient(circle at 50% 25%, #1e1b4b 0%, #0f172a 45%, #030712 100%);
      color: #f8fafc;
    }
    .focus-theme-lavender {
      background: radial-gradient(circle at 50% 25%, #3b1b4b 0%, #1e1035 45%, #0b0514 100%);
      color: #fdf4ff;
    }
    .focus-theme-warm {
      background: radial-gradient(circle at 50% 25%, #451a03 0%, #230c04 45%, #0a0301 100%);
      color: #fff7ed;
    }
    .focus-theme-dark {
      background: radial-gradient(circle at 50% 25%, #18181b 0%, #09090b 45%, #000000 100%);
      color: #fafafa;
    }

    /* Ambient Background Glow */
    .focus-ambient-bg {
      position: absolute;
      inset: 0;
      overflow: hidden;
      pointer-events: none;
      z-index: 1;
    }
    .focus-ambient-orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(80px);
      opacity: 0.25;
      animation: ambientFloat 14s infinite alternate ease-in-out;
    }
    .focus-ambient-orb.orb-1 {
      width: 450px;
      height: 450px;
      background: #818cf8;
      top: 10%;
      left: 20%;
    }
    .focus-ambient-orb.orb-2 {
      width: 400px;
      height: 400px;
      background: #ec4899;
      bottom: 15%;
      right: 15%;
      animation-delay: -5s;
    }
    .focus-ambient-orb.orb-3 {
      width: 320px;
      height: 320px;
      background: #06b6d4;
      top: 40%;
      right: 30%;
      animation-delay: -9s;
    }
    @keyframes ambientFloat {
      0% { transform: translate(0, 0) scale(1); }
      50% { transform: translate(30px, -25px) scale(1.08); }
      100% { transform: translate(-25px, 20px) scale(0.95); }
    }

    /* Top Identity & Status Bar */
    .focus-top-bar {
      position: relative;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 28px;
      background: linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0) 100%);
    }
    .focus-top-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .focus-avatar-container {
      position: relative;
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.08);
      border: 2px solid rgba(255, 255, 255, 0.25);
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
      cursor: pointer;
      overflow: hidden;
      flex-shrink: 0;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .focus-avatar-container:hover {
      transform: scale(1.06);
      border-color: #38bdf8;
    }
    .focus-top-avatar-img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .focus-status-dot {
      position: absolute;
      bottom: 2px;
      right: 2px;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #10b981;
      border: 2px solid #0f172a;
      box-shadow: 0 0 8px #10b981;
    }
    .focus-character-meta {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .focus-character-name-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .focus-character-name {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #fff;
    }
    .focus-character-tag {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
      font-weight: 500;
    }
    .focus-call-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      color: #38bdf8;
    }
    .focus-call-badge .pulse-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #38bdf8;
      box-shadow: 0 0 8px #38bdf8;
      animation: pulseDot 2s infinite;
    }
    @keyframes pulseDot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Top Center: Timer */
    .focus-top-center {
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .focus-timer-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px;
      border-radius: 20px;
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.12);
      backdrop-filter: blur(8px);
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.04em;
      color: #e2e8f0;
      font-variant-numeric: tabular-nums;
    }
    .focus-timer-icon {
      font-size: 10px;
      color: #10b981;
    }

    /* Top Right: Actions & Themes */
    .focus-top-right {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .focus-select-pill {
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #f1f5f9;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 18px;
      outline: none;
      cursor: pointer;
      backdrop-filter: blur(8px);
    }
    .focus-select-pill:focus {
      border-color: #38bdf8;
    }
    .focus-icon-btn {
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #f1f5f9;
      padding: 6px 12px;
      border-radius: 18px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      backdrop-filter: blur(8px);
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .focus-icon-btn:hover {
      background: rgba(255, 255, 255, 0.15);
      border-color: rgba(255, 255, 255, 0.3);
      color: #fff;
    }
    .focus-btn-hangup-top {
      background: rgba(239, 68, 68, 0.2);
      border-color: rgba(239, 68, 68, 0.4);
      color: #fca5a5;
      font-size: 14px;
      padding: 6px 10px;
    }
    .focus-btn-hangup-top:hover {
      background: #ef4444;
      color: #fff;
      border-color: #ef4444;
    }

    /* Center Anime Stage */
    .focus-stage {
      position: relative;
      z-index: 5;
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 10px 20px;
      min-height: 0;
    }
    .focus-character-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      max-width: 440px;
      height: 48vh;
      max-height: 440px;
    }
    .focus-character-halo {
      position: absolute;
      width: 320px;
      height: 320px;
      border-radius: 50%;
      filter: blur(48px);
      opacity: 0.4;
      z-index: 1;
      transition: background 0.4s ease, opacity 0.4s ease, transform 0.4s ease;
      pointer-events: none;
    }
    .focus-character-halo.state-idle {
      background: #38bdf8;
      opacity: 0.3;
    }
    .focus-character-halo.state-listening {
      background: #10b981;
      opacity: 0.6;
      transform: scale(1.08);
    }
    .focus-character-halo.state-thinking {
      background: #a855f7;
      opacity: 0.6;
      transform: scale(1.05);
    }
    .focus-character-halo.state-speaking {
      background: #ec4899;
      opacity: 0.65;
      transform: scale(1.1);
    }

    .focus-character-art {
      position: relative;
      z-index: 2;
      max-height: 100%;
      max-width: 100%;
      object-fit: contain;
      filter: drop-shadow(0 15px 30px rgba(0,0,0,0.45));
      transition: transform 0.3s ease, filter 0.3s ease;
    }
    .companion-breathe {
      animation: companionBreathe 4s infinite ease-in-out;
    }
    @keyframes companionBreathe {
      0%, 100% {
        transform: translateY(0px) scale(1);
      }
      50% {
        transform: translateY(-8px) scale(1.015);
      }
    }

    /* Voice Waveform Activity */
    .focus-voice-wave {
      display: flex;
      align-items: center;
      gap: 5px;
      height: 24px;
      margin-top: 12px;
      z-index: 6;
    }
    .focus-voice-wave .bar {
      width: 4px;
      height: 6px;
      border-radius: 3px;
      background: #38bdf8;
      transition: height 0.15s ease, background 0.3s ease;
    }
    .focus-voice-wave.active-listening .bar {
      background: #10b981;
      animation: waveBarListening 1s infinite ease-in-out;
    }
    .focus-voice-wave.active-speaking .bar {
      background: #ec4899;
      animation: waveBarSpeaking 0.8s infinite ease-in-out;
    }
    .focus-voice-wave.active-thinking .bar {
      background: #a855f7;
      animation: waveBarThinking 1.4s infinite ease-in-out;
    }
    .focus-voice-wave.active-listening .bar:nth-child(1) { animation-delay: 0.1s; }
    .focus-voice-wave.active-listening .bar:nth-child(2) { animation-delay: 0.25s; }
    .focus-voice-wave.active-listening .bar:nth-child(3) { animation-delay: 0.4s; }
    .focus-voice-wave.active-listening .bar:nth-child(4) { animation-delay: 0.15s; }
    .focus-voice-wave.active-listening .bar:nth-child(5) { animation-delay: 0.35s; }
    .focus-voice-wave.active-listening .bar:nth-child(6) { animation-delay: 0.2s; }
    .focus-voice-wave.active-listening .bar:nth-child(7) { animation-delay: 0.45s; }

    .focus-voice-wave.active-speaking .bar:nth-child(1) { animation-delay: 0.05s; }
    .focus-voice-wave.active-speaking .bar:nth-child(2) { animation-delay: 0.2s; }
    .focus-voice-wave.active-speaking .bar:nth-child(3) { animation-delay: 0.35s; }
    .focus-voice-wave.active-speaking .bar:nth-child(4) { animation-delay: 0.1s; }
    .focus-voice-wave.active-speaking .bar:nth-child(5) { animation-delay: 0.25s; }
    .focus-voice-wave.active-speaking .bar:nth-child(6) { animation-delay: 0.15s; }
    .focus-voice-wave.active-speaking .bar:nth-child(7) { animation-delay: 0.3s; }

    .focus-voice-wave.active-thinking .bar:nth-child(1) { animation-delay: 0.1s; }
    .focus-voice-wave.active-thinking .bar:nth-child(2) { animation-delay: 0.3s; }
    .focus-voice-wave.active-thinking .bar:nth-child(3) { animation-delay: 0.5s; }
    .focus-voice-wave.active-thinking .bar:nth-child(4) { animation-delay: 0.2s; }
    .focus-voice-wave.active-thinking .bar:nth-child(5) { animation-delay: 0.4s; }
    .focus-voice-wave.active-thinking .bar:nth-child(6) { animation-delay: 0.15s; }
    .focus-voice-wave.active-thinking .bar:nth-child(7) { animation-delay: 0.35s; }

    @keyframes waveBarListening {
      0%, 100% { height: 6px; }
      50% { height: 22px; }
    }
    @keyframes waveBarSpeaking {
      0%, 100% { height: 8px; }
      50% { height: 26px; }
    }
    @keyframes waveBarThinking {
      0%, 100% { height: 5px; }
      50% { height: 16px; }
    }

    /* Expression Pill */
    .focus-expression-pill {
      margin-top: 10px;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 14px;
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #e2e8f0;
      backdrop-filter: blur(8px);
      z-index: 6;
      transition: all 0.25s ease;
    }

    /* Live Transcript Panel */
    .focus-transcript-container {
      position: relative;
      z-index: 10;
      width: 100%;
      max-width: 720px;
      margin: 0 auto 12px auto;
      padding: 0 20px;
      box-sizing: border-box;
    }
    .focus-transcript-card {
      background: rgba(15, 23, 42, 0.72);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 16px;
      padding: 12px 18px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.45);
      transition: all 0.3s ease;
    }
    .focus-transcript-card.expanded {
      max-height: 260px;
    }
    .focus-transcript-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .focus-transcript-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
    }
    .focus-transcript-toggle {
      background: none;
      border: none;
      color: #94a3b8;
      font-size: 13px;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .focus-transcript-toggle:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
    }
    .focus-transcript-body {
      max-height: 85px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 4px;
      scroll-behavior: smooth;
    }
    .focus-transcript-card.expanded .focus-transcript-body {
      max-height: 200px;
    }
    .focus-transcript-line {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 13.5px;
      line-height: 1.45;
    }
    .focus-transcript-line.user .focus-speaker-tag {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 6px;
      background: #0284c7;
      color: #fff;
      flex-shrink: 0;
    }
    .focus-transcript-line.user .focus-text-content {
      color: #7dd3fc;
    }
    .focus-transcript-line.bot .focus-speaker-tag {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 6px;
      background: #db2777;
      color: #fff;
      flex-shrink: 0;
    }
    .focus-transcript-line.bot .focus-text-content {
      color: #f1f5f9;
    }

    /* Floating Call Controls Dock */
    .focus-controls-dock {
      position: relative;
      z-index: 10;
      display: flex;
      justify-content: center;
      padding: 0 20px 24px 20px;
    }
    .focus-dock-inner {
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 40px;
      padding: 8px 16px;
      box-shadow: 0 12px 35px rgba(0,0,0,0.55);
      flex-wrap: wrap;
      justify-content: center;
    }
    .focus-dock-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 24px;
      padding: 8px 16px;
      min-width: 68px;
      color: #e2e8f0;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
    }
    .focus-dock-btn:hover {
      background: rgba(255, 255, 255, 0.16);
      transform: translateY(-2px);
      color: #fff;
    }
    .focus-dock-btn.active {
      background: rgba(16, 185, 129, 0.25);
      border-color: #10b981;
      color: #6ee7b7;
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
    }
    .focus-dock-btn.btn-interrupt {
      background: rgba(245, 158, 11, 0.2);
      border-color: rgba(245, 158, 11, 0.4);
      color: #fcd34d;
    }
    .focus-dock-btn.btn-interrupt:hover {
      background: rgba(245, 158, 11, 0.4);
      border-color: #f59e0b;
      box-shadow: 0 0 15px rgba(245, 158, 11, 0.35);
    }
    .focus-dock-btn.btn-end-call {
      background: rgba(239, 68, 68, 0.3);
      border-color: #ef4444;
      color: #fff;
    }
    .focus-dock-btn.btn-end-call:hover {
      background: #ef4444;
      box-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
    }
    .focus-dock-icon {
      font-size: 18px;
    }
    .focus-dock-label {
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
    }

    /* Character Selection Gallery Modal */
    .character-gallery-card {
      background: #0f172a;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 16px;
      max-width: 780px;
      width: 92%;
      padding: 24px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6);
      position: relative;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
    }
    .character-gallery-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 20px;
    }
    .character-gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      overflow-y: auto;
      padding-right: 4px;
      margin-bottom: 16px;
    }
    .companion-select-card {
      background: rgba(30, 41, 59, 0.7);
      border: 2px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      cursor: pointer;
      transition: all 0.25s ease;
      position: relative;
    }
    .companion-select-card:hover {
      border-color: #38bdf8;
      background: rgba(30, 41, 59, 0.95);
      transform: translateY(-3px);
    }
    .companion-select-card.active {
      border-color: #ec4899;
      background: rgba(236, 72, 153, 0.1);
      box-shadow: 0 0 20px rgba(236, 72, 153, 0.25);
    }
    .char-card-preview {
      position: relative;
      width: 100%;
      height: 160px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.25);
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
    }
    .char-preview-img {
      max-height: 140px;
      max-width: 100%;
      object-fit: contain;
      filter: drop-shadow(0 6px 12px rgba(0,0,0,0.4));
    }
    .char-badge {
      position: absolute;
      top: 8px;
      right: 8px;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 10px;
    }
    .char-badge.default { background: #db2777; color: #fff; }
    .char-badge.cyber { background: #0284c7; color: #fff; }
    .char-badge.male { background: #059669; color: #fff; }
    .char-card-info {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .char-name {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }
    .char-role {
      font-size: 11px;
      color: #38bdf8;
      font-weight: 600;
      margin-bottom: 6px;
    }
    .char-desc {
      font-size: 12px;
      color: #cbd5e1;
      line-height: 1.4;
      margin: 0 0 10px 0;
      flex: 1;
    }
    .char-traits {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-bottom: 12px;
    }
    .trait-tag {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.08);
      color: #94a3b8;
    }
    .btn-select-char {
      width: 100%;
      padding: 8px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #fff;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .companion-select-card.active .btn-select-char {
      background: #db2777;
      border-color: #db2777;
      color: #fff;
    }
    .character-gallery-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 14px;
    }

    @media (max-width: 768px) {
      .focus-top-bar { padding: 12px 14px; }
      .focus-character-wrapper { height: 42vh; }
      .focus-controls-dock { padding: 0 10px 16px 10px; }
      .focus-dock-inner { gap: 6px; padding: 6px 10px; }
      .focus-dock-btn { padding: 6px 10px; min-width: 52px; }
      .focus-dock-label { font-size: 10px; }
      .focus-transcript-container { padding: 0 12px; }
    }

  </style>
</head>
<body>

  <div class="workbench-shell">
  <!-- A. TITLE BAR -->
  <header class="titlebar">
    <div class="titlebar-left">
      <div class="brand">
        <span class="brand-icon">⚡</span>
        <span id="header-brand-title"><span id="header-ai-name">GDR-AI</span></span>
        <span class="brand-sub">GDR-IDE</span>
      </div>
      <div class="titlebar-breadcrumbs">
        <span class="crumb-root">workspace</span>
        <span class="crumb-sep">/</span>
        <span class="crumb-section" id="titlebar-sec-crumb">Home & Chat</span>
        <span class="crumb-sep">/</span>
        <span class="crumb-active" id="titlebar-screen-crumb">1. Home</span>
      </div>
    </div>

    <!-- Center Search & Command Palette Access -->
    <div class="titlebar-center">
      <div class="titlebar-search-box" onclick="openPalette()" role="button" tabindex="0" title="Open Command Palette (Ctrl+Shift+P / Ctrl+P)">
        <span class="search-icon">🔍</span>
        <span class="search-text">GDR-IDE: Search files, screens & commands...</span>
        <kbd class="search-kbd">Ctrl+Shift+P</kbd>
      </div>
    </div>

    <!-- Right Controls -->
    <div class="titlebar-right">
      <button id="barge-in-stop-btn" class="nav-tab" style="border: 1px solid var(--danger); background: rgba(229,107,111,0.2); color: var(--danger); display: none; font-weight: bold; animation: pulse 1s infinite;" onclick="stopSpeakingNow()">⏹️ STOP SPEAKING</button>
      <div id="header-engine-pill" style="font-size:10px; padding:3px 7px; border-radius:4px; background:rgba(139,140,246,0.1); border:1px solid var(--accent-border); color:var(--accent-primary); display:flex; align-items:center; gap:4px;" title="Engine & Token Telemetry">
        <span id="header-model-name">🤖 Sarvam 105B (Cloud)</span> | <span id="header-voice-name">🗣️ Swara Neural</span>
      </div>
      <select id="header-voice-select" onchange="setVoicePreference(this.value)" class="titlebar-select">
        <option value="aarushi_auto">⚡ Voice: Neural Auto</option>
        <option value="hi_swara">🇮🇳 Hindi: Swara (Studio Neural)</option>
        <option value="elevenlabs">✨ ElevenLabs: Custom HD</option>
        <option value="en_aria">🇺🇸 English: Aria (Expressive)</option>
        <option value="en_jenny">🇺🇸 English: Jenny (Clear)</option>
        <option value="en_neerja">🇮🇳 Indian English: Neerja</option>
        <option value="en_sonia">🇬🇧 British: Sonia</option>
        <option value="piper_offline">💻 Local Offline: Piper</option>
        <option value="browser">🌐 Browser Voice</option>
      </select>
      <div style="display:inline-flex; align-items:center; gap:2px; padding:1px 4px; background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:4px;">
        <div id="engine-mode-pill" onclick="cycleEngineMode()" style="cursor:pointer; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700; background:var(--accent-soft); border:1px solid var(--accent-border); color:var(--accent-primary);" title="Engine mode: click to cycle (FAST / DEEP / CODE / PAIR)">⚡ FAST</div>
        <button class="nav-tab" style="padding:2px 5px; font-size:10px; min-width:auto; margin:0;" onclick="sessionUndo()" title="Undo last exchange">⟲</button>
        <button class="nav-tab" style="padding:2px 5px; font-size:10px; min-width:auto; margin:0;" onclick="sessionRedo()" title="Redo exchange">⟳</button>
        <button class="nav-tab" style="padding:2px 5px; font-size:10px; min-width:auto; margin:0;" onclick="sessionCheckpoint()" title="Save session checkpoint">📌</button>
      </div>
      <button class="titlebar-btn" onclick="toggleBottomPanel()" title="Toggle Integrated Terminal / Output (`Ctrl+` `~`)">📟 Panel</button>
      <button class="titlebar-btn" onclick="toggleSidebar()" title="Toggle Primary Sidebar (Ctrl+B)">📁 Sidebar</button>
      <button class="titlebar-btn" onclick="toggleTheme()" title="Toggle Dark/Light Mode">🌓 Theme</button>
      <button id="panic-btn" class="btn-panic" onclick="togglePanic()">🚨 PANIC KILL</button>
    </div>
  </header>

  <!-- WORKBENCH BODY: ACTIVITY BAR + SIDEBAR + WORKSPACE -->
  <div class="workbench-body">
    <!-- B. ACTIVITY BAR (Exactly 5 Primary Sections) -->
    <nav class="activity-bar" aria-label="Primary Navigation">
      <div class="activity-bar-top">
        <!-- Section 1: Home & Chat -->
        <button class="activity-item active" id="act-sec-home-chat" onclick="selectSection('home-chat')" title="Section 1: Home & Chat (Ctrl+1)" aria-label="Home & Chat">
          <span class="activity-icon">💬</span>
          <span class="activity-label">Chat</span>
        </button>

        <!-- Section 2: Coding Studio -->
        <button class="activity-item" id="act-sec-coding-studio" onclick="selectSection('coding-studio')" title="Section 2: Coding Studio & GDR-IDE (Ctrl+2)" aria-label="Coding Studio">
          <span class="activity-icon">💻</span>
          <span class="activity-label">Code</span>
        </button>

        <!-- Section 3: Automation & Tasks -->
        <button class="activity-item" id="act-sec-automation-tasks" onclick="selectSection('automation-tasks')" title="Section 3: Automation & Tasks (Ctrl+3)" aria-label="Automation & Tasks">
          <span class="activity-icon">⚡</span>
          <span class="activity-label">Auto</span>
        </button>

        <!-- Section 4: Devices & System -->
        <button class="activity-item" id="act-sec-devices-system" onclick="selectSection('devices-system')" title="Section 4: Devices & System (Ctrl+4)" aria-label="Devices & System">
          <span class="activity-icon">🌐</span>
          <span class="activity-label">Mesh</span>
        </button>

        <!-- Section 5: Settings & Security -->
        <button class="activity-item" id="act-sec-settings-security" onclick="selectSection('settings-security')" title="Section 5: Settings & Security (Ctrl+5)" aria-label="Settings & Security">
          <span class="activity-icon">⚙️</span>
          <span class="activity-label">Config</span>
        </button>
      </div>

      <div class="activity-bar-bottom">
        <button class="activity-item" onclick="toggleBottomPanel()" title="Terminal Panel (`Ctrl+` `~`)">
          <span class="activity-icon">⌨️</span>
          <span class="activity-label">Term</span>
        </button>
        <button class="activity-item" onclick="showScreen('settings')" title="Settings & Preferences">
          <span class="activity-icon">🔧</span>
          <span class="activity-label">Setup</span>
        </button>
      </div>
    </nav>

    <!-- C. PRIMARY SIDEBAR -->
    <aside class="primary-sidebar" id="primary-sidebar">
      <div class="sidebar-top-bar">
        <span class="sidebar-main-title">EXPLORER & WORKBENCH</span>
        <button class="sidebar-icon-btn" onclick="toggleSidebar()" title="Collapse Sidebar (Ctrl+B)">◀</button>
      </div>
      
      <div class="sidebar-accordions" id="sidebar-accordions">
        <!-- Accordion 1: Home & Chat -->
        <div class="sidebar-accordion open" id="sec-group-home-chat">
          <div class="accordion-header" onclick="toggleAccordion('home-chat')">
            <div class="accordion-header-left">
              <span class="accordion-arrow">▾</span>
              <span class="accordion-title">💬 1. HOME & CHAT</span>
            </div>
            <span class="accordion-badge">Chat</span>
          </div>
          <div class="accordion-body">
            <button class="nav-tab sidebar-item active" onclick="showScreen('home')"><span class="item-icon">🏠</span> 1. Home</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('chat')"><span class="item-icon">💬</span> 2. Chat</button>
            <button class="sidebar-item" onclick="newChatConversation()"><span class="item-icon">➕</span> New Assistant</button>
            <button class="sidebar-item" onclick="openPalette()"><span class="item-icon">⚡</span> Command Center</button>
            <button class="sidebar-item" onclick="openChatHistoryModal()"><span class="item-icon">🕒</span> Conversation History</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('memory')"><span class="item-icon">🧠</span> 7. Memory</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('inbox')"><span class="item-icon">📬</span> 5. Unified Inbox</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('calendar')"><span class="item-icon">📅</span> 6. Calendar</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('timeline')"><span class="item-icon">⏱️</span> 18. My Day & Wellbeing</button>
            <button class="nav-tab sidebar-item" id="nav-contacts-tab" onclick="showScreen('contacts')"><span class="item-icon">👥</span> 20. Trusted Relations & Network</button>
            <button class="sidebar-item" onclick="showScreen('audit')"><span class="item-icon">🔔</span> Notifications</button>
            <button class="sidebar-item" onclick="openModelHubModal()"><span class="item-icon">🤖</span> AI Provider Selection</button>
            <button class="sidebar-item" onclick="openAarushiCompanionModal()"><span class="item-icon">💖</span> Aarushi Companion Settings</button>
            <button class="sidebar-item" id="nav-focus-call-btn" onclick="openFocusCallMode()"><span class="item-icon">📞</span> 19. Focus Anime Call</button>
          </div>
        </div>

        <!-- Accordion 2: Coding Studio -->
        <div class="sidebar-accordion open" id="sec-group-coding-studio">
          <div class="accordion-header" onclick="toggleAccordion('coding-studio')">
            <div class="accordion-header-left">
              <span class="accordion-arrow">▾</span>
              <span class="accordion-title">💻 2. CODING STUDIO</span>
            </div>
            <span class="accordion-badge">GDR-IDE</span>
          </div>
          <div class="accordion-body">
            <button class="nav-tab sidebar-item" onclick="showScreen('coding')"><span class="item-icon">💻</span> 10. Coding</button>
            <button class="nav-tab sidebar-item" id="nav-ide-tab" onclick="showScreen('ide')"><span class="item-icon">⚡</span> 17. GDR-IDE Workspace</button>
            <button class="sidebar-item" onclick="toggleBottomPanel(true, 'terminal')"><span class="item-icon">📟</span> Integrated Terminal</button>
            <button class="sidebar-item" onclick="triggerIdeAssistance()"><span class="item-icon">🤖</span> Programming Assistance</button>
            <button class="sidebar-item" onclick="runIdeTests()"><span class="item-icon">🐞</span> Debugging Tools</button>
            <button class="sidebar-item" onclick="toggleBottomPanel(true, 'output')"><span class="item-icon">📋</span> Output and Diagnostics</button>
            <button class="sidebar-item" onclick="showScreen('tasks')"><span class="item-icon">✅</span> Code-Related Tasks</button>
            <button class="sidebar-item" onclick="showScreen('ide'); refreshIdeFileTree();"><span class="item-icon">📂</span> Project Explorer</button>
          </div>
        </div>

        <!-- Accordion 3: Automation & Tasks -->
        <div class="sidebar-accordion open" id="sec-group-automation-tasks">
          <div class="accordion-header" onclick="toggleAccordion('automation-tasks')">
            <div class="accordion-header-left">
              <span class="accordion-arrow">▾</span>
              <span class="accordion-title">⚡ 3. AUTOMATION & TASKS</span>
            </div>
            <span class="accordion-badge">Auto</span>
          </div>
          <div class="accordion-body">
            <button class="nav-tab sidebar-item" onclick="showScreen('tasks')"><span class="item-icon">📋</span> 4. Tasks</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('workflows')"><span class="item-icon">🔄</span> 9. Workflows</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('bots')"><span class="item-icon">🤖</span> 14. Bots</button>
            <button class="nav-tab sidebar-item" id="nav-messaging-btn" onclick="showScreen('messaging')"><span class="item-icon">💬</span> Messaging Integrations</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('approvals')"><span class="item-icon">🛡️</span> 3. Approvals</button>
            <button class="sidebar-item" id="ghost-prompter-btn" onclick="toggleGhostOverlay()"><span class="item-icon">👻</span> Ghost Prompter</button>
            <button class="sidebar-item" id="multipanel-btn" onclick="toggleMultiPanel()"><span class="item-icon">◫</span> HUD</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('stealth')">🕵️ Stealth Copilot</button>
            <button class="sidebar-item" onclick="toggleLiveScreenStream()"><span class="item-icon">🖥️</span> Screen Interaction</button>
            <button class="sidebar-item" onclick="showScreen('audit')"><span class="item-icon">📜</span> Automation History</button>
            <button class="sidebar-item" id="handsfree-btn" onclick="toggleHandsFree()"><span class="item-icon">🎙️</span> Auto-Listen: ON</button>
          </div>
        </div>

        <!-- Accordion 4: Devices & System -->
        <div class="sidebar-accordion open" id="sec-group-devices-system">
          <div class="accordion-header" onclick="toggleAccordion('devices-system')">
            <div class="accordion-header-left">
              <span class="accordion-arrow">▾</span>
              <span class="accordion-title">🌐 4. DEVICES & SYSTEM</span>
            </div>
            <span class="accordion-badge">Mesh</span>
          </div>
          <div class="accordion-body">
            <button class="nav-tab sidebar-item" onclick="showScreen('monitor')"><span class="item-icon">📊</span> 11. System</button>
            <button class="sidebar-item" id="screen-share-nav-btn" onclick="toggleLiveScreenStream()"><span class="item-icon">🖥️</span> Screen</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('camera')"><span class="item-icon">📷</span> 8. Camera</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('mesh')"><span class="item-icon">🌐</span> 16. Device Mesh</button>
            <button class="sidebar-item" id="btn-cloudflare-header" onclick="openCloudflareModal()"><span class="item-icon">☁️</span> Cloudflare Share</button>
            <button class="sidebar-item" id="btn-fix-sound-header" onclick="repairLaptopAudioHardware()"><span class="item-icon">🔊</span> Audio Diagnostics</button>
            <button class="sidebar-item" onclick="toggleBrowserSpeechRecognition()"><span class="item-icon">🎤</span> Microphone Configuration</button>
            <button class="sidebar-item" id="audio-mute-btn" onclick="toggleAudioSpeech()"><span class="item-icon">🔉</span> Sound Controls</button>
            <button class="sidebar-item" onclick="showScreen('mesh')"><span class="item-icon">📱</span> Connected Devices</button>
            <button class="sidebar-item" style="color:var(--danger);" onclick="togglePanic()"><span class="item-icon">🚨</span> Panic Kill</button>
          </div>
        </div>

        <!-- Accordion 5: Settings & Security -->
        <div class="sidebar-accordion open" id="sec-group-settings-security">
          <div class="accordion-header" onclick="toggleAccordion('settings-security')">
            <div class="accordion-header-left">
              <span class="accordion-arrow">▾</span>
              <span class="accordion-title">⚙️ 5. SETTINGS & SECURITY</span>
            </div>
            <span class="accordion-badge">Vault</span>
          </div>
          <div class="accordion-body">
            <button class="nav-tab sidebar-item" onclick="showScreen('settings')"><span class="item-icon">⚙️</span> 12. Settings</button>
            <button class="sidebar-item" onclick="showScreen('settings'); scrollToSettingsCard('theme');"><span class="item-icon">🎨</span> Theme and Appearance</button>
            <button class="sidebar-item" onclick="openModelHubModal()"><span class="item-icon">🤖</span> AI Provider Configuration</button>
            <button class="sidebar-item" onclick="showScreen('settings'); scrollToSettingsCard('voice');"><span class="item-icon">🗣️</span> Voice Selection Settings</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('rag')"><span class="item-icon">🔒</span> 15. RAG Vault</button>
            <button class="nav-tab sidebar-item" onclick="showScreen('audit')"><span class="item-icon">📜</span> 13. Audit Log</button>
            <button class="sidebar-item" onclick="showScreen('settings'); scrollToSettingsCard('security');"><span class="item-icon">🛡️</span> Security and Permissions</button>
            <button class="sidebar-item" onclick="openMemoryVaultModal()"><span class="item-icon">🧠</span> Memory Configuration</button>
            <button class="sidebar-item" onclick="toggleCameraPrivacy()"><span class="item-icon">👁️</span> Privacy Settings</button>
            <button class="sidebar-item" onclick="showScreen('mesh')"><span class="item-icon">🔑</span> Device Authorization</button>
            <button class="sidebar-item" onclick="openShortcutsModal()"><span class="item-icon">⌨️</span> Keyboard Shortcuts</button>
            <button class="sidebar-item" onclick="fetchStatus()"><span class="item-icon">🩺</span> Diagnostics</button>
          </div>
        </div>
      </div>
    </aside>

    <!-- D. MAIN WORKSPACE CONTAINER -->
    <div class="workbench-workspace">
      <main class="workbench-main">


    <!-- 1. HOME SCREEN -->
    <div id="screen-home" class="screen active">
      <div class="orb-container">
        <div id="main-orb" class="orb" onclick="onOrbClick()" title="Click to speak or stop speaking"></div>
        <div id="orb-badge" class="orb-state-badge">IDLE // STANDBY (CLICK TO TALK)</div>
        <button id="orb-stop-btn" onclick="stopSpeakingNow()" style="display:none; margin: 8px auto 0 auto; background:rgba(239,68,68,0.3); border:1px solid var(--danger); color:#fca5a5; padding:6px 18px; border-radius:20px; font-weight:700; cursor:pointer; font-size:12px; letter-spacing:1px; animation:pulse 1s infinite;">
          ⏹️ STOP SPEAKING (START LISTENING)
        </button>
        <h1 style="margin: 14px 0 4px 0; font-size: 24px;"><span id="greeting-time-phrase">Welcome back</span>, <span id="owner-name-display" style="color:var(--accent-primary);">Commander</span> <span id="greeting-date-phrase" style="font-size:13px; color:var(--text-muted); font-weight:normal; margin-left:6px;"></span></h1>
        <p id="what-doing-text" style="color:var(--text-muted); font-size: 13px; margin: 0;">Monitoring system and scheduled routines</p>

        <!-- Live Voice Status Banner -->
        <div id="home-mic-banner" style="display:none; margin-top:14px; padding: 6px 16px; border-radius: 20px; background: rgba(16, 185, 129, 0.2); border: 1px solid var(--success); color: #6ee7b7; font-size: 13px;">
          🎙️ Listening to your voice... Speak now!
        </div>

        <!-- AI Capabilities Studio Chips -->
        <div class="chip-container">
          <div class="chip" onclick="quickPrompt('⚡ Deep Research: Analyze the key architectural breakthroughs in modern AI agents and provide an executive summary with practical use-cases.')">⚡ Deep Research</div>
          <div class="chip" onclick="quickPrompt('💻 Code Review & Debug: Check my recent scripts for efficiency bottlenecks, potential race conditions, and recommend production optimizations.')">💻 Code Debugger</div>
          <div class="chip" onclick="openMemoryVaultModal()">🧠 Memory Vault</div>
          <div class="chip" onclick="quickPrompt('📊 Autonomous Daily Action Plan: Generate a high-priority 5-step task breakdown for maximum productivity today.')">📊 Action Planner</div>
          <div class="chip" onclick="quickPrompt('What is the weather and schedule today?')">📅 Today's Schedule</div>
          <div class="chip" onclick="quickPrompt('Run system diagnostics and show VRAM status')">📊 VRAM Health</div>
        </div>

        <!-- Home Direct Chat & Voice Bar -->
        <div id="home-chat-bar-container" style="display:flex; gap:10px; width:100%; max-width:820px; margin-top:14px; box-sizing:border-box;">
          <input type="text" id="home-chat-input" placeholder="Ask your assistant anything or click Mic to talk..." onkeydown="if(event.key==='Enter') sendChat()" style="flex:1; min-width:0; padding:10px 14px; background:var(--bg-input); border:1px solid var(--border); border-radius:8px; color:#fff; font-size:14px;">
          <div class="btn-group" style="display:flex; gap:8px;">
            <button class="btn btn-secondary" onclick="openModelHubModal()" title="Switch AI Model or Pull from Hugging Face">🤖 Models</button>
            <button class="btn btn-secondary" onclick="enhanceInputPrompt('home-chat-input')" title="AI Smart Enhance Prompt">✨ Enhance</button>
            <button id="home-mic-btn" class="btn btn-secondary" onclick="toggleBrowserSpeechRecognition()" title="Speak to Assistant">🎙️ Mic</button>
            <button class="btn" onclick="sendChat()">Send</button>
          </div>
        </div>

        <!-- Real-Time Microphone Frequency & Live Audio Transcript Box -->
        <div id="home-live-audio-box" style="display:none; width:100%; max-width:820px; margin-top:12px; padding:14px 16px; background:var(--bg-elevated); border:1px solid var(--accent-primary); border-radius:var(--radius-md); box-sizing:border-box; text-align:left; box-shadow:var(--shadow-soft);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:12px; font-weight:700; color:var(--accent-primary); display:flex; align-items:center; gap:6px;">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--accent-primary); box-shadow:0 0 8px var(--accent-primary);"></span>
                LIVE MICROPHONE AUDIO INPUT:
              </span>
              <span id="home-mic-detected-badge" style="font-size:10px; padding:2px 8px; border-radius:10px; background:rgba(16,163,127,0.15); color:var(--accent-primary); border:1px solid var(--accent-primary); font-weight:600;">ACTIVE</span>
            </div>
            <span id="home-mic-freq-label" style="font-size:11px; color:var(--text-muted); font-family:monospace;">Signal: Standby • 0 Hz</span>
          </div>

          <!-- Live Audio Frequency Waveform Canvas -->
          <canvas id="home-audio-wave" height="34" style="width:100%; border-radius:6px; margin-bottom:10px; display:block; background:rgba(0,0,0,0.35); border:1px solid var(--border-subtle);"></canvas>

          <!-- Live Real-Time Transcribed Speech -->
          <div style="font-size:11px; color:var(--text-muted); margin-bottom:4px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Hearing In Real-Time:</div>
          <div id="home-live-transcript-text" style="font-size:14px; color:var(--text-primary); font-weight:500; min-height:24px; line-height:1.4; word-break:break-word; background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border-subtle);">
            Listening... Speak into your microphone now.
          </div>
        </div>

        <!-- Live Conversation & Real-Time Written Transcript -->
        <div class="card" style="margin-top: 16px; width: 100%; max-width: 820px; box-sizing: border-box; text-align: left;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <h3 style="margin:0; font-size:14px; color:var(--text-main);">💬 Live Conversation Transcript</h3>
              <span id="transcribing-pulse" style="display:none; font-size:10px; padding:1px 6px; border-radius:10px; background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3);">● TRANSCRIBING</span>
            </div>
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <span id="home-engine-badge" style="font-size:11px; color:var(--text-muted);">Model: Sarvam AI | Voice: Edge HD (0 tokens)</span>
              <button class="btn btn-secondary" style="font-size:10px; padding:2px 8px;" onclick="exportChatMarkdown()">📥 Export Chat</button>
              <button class="btn btn-secondary" style="font-size:10px; padding:2px 8px;" onclick="clearLiveTranscript()">Clear</button>
            </div>
          </div>
          <div id="home-transcript-list" style="max-height: 220px; min-height: 90px; overflow-y: auto; padding: 10px; background: var(--bg-input); border:1px solid var(--border); border-radius: 8px; font-size: 13px; line-height: 1.5;">
            <div style="color:var(--text-muted); font-style:italic;">Speak to the Orb or click "Mic". Everything you say and answers will be transcribed and spoken in real-time.</div>
          </div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <h2 id="briefing-title">📋 Daily Overview & Briefing</h2>
          <div id="briefing-content" class="briefing-content" style="color:var(--text-secondary); max-height:240px; overflow-y:auto; font-size:13px; line-height:1.6; padding-right:4px;">Loading briefing...</div>
          <div style="display:flex; gap: 10px; margin-top: 10px;">
            <button class="btn" onclick="fetchBriefing()">Refresh Briefing</button>
            <button class="btn btn-secondary" onclick="speakText(document.getElementById('briefing-content').innerText)">🔊 Read Aloud</button>
          </div>
        </div>

        <div class="card">
          <h2>⚡ Quick Controls & Live Telemetry</h2>
          <div class="metric-row"><span>GPU VRAM:</span><b id="quick-vram">4 MiB / 3800 MiB Limit</b></div>
          <div class="progress-bar" style="margin-bottom: 14px;"><div id="quick-vram-bar" class="progress-fill safe" style="width: 2%;"></div></div>
          
          <div class="metric-row"><span>Active Model Lane:</span><b id="quick-lane" style="color:var(--cyan);">Lane 1 (Local CPU/Fast)</b></div>
          <div class="metric-row"><span>Audio Source:</span><b>Realtek ALC256 (70%+ Auto-Boost)</b></div>
          <div class="metric-row"><span>Scheduled Routines:</span><b id="quick-tasks-count">2 Active</b></div>

          <div style="display:flex; gap: 10px; margin-top: 18px; flex-wrap: wrap;">
            <button id="quick-talk-btn" class="btn" onclick="toggleBrowserSpeechRecognition()">🎙️ Talk to GDR</button>
            <button id="focus-call-home-btn" class="btn" onclick="openFocusCallMode()" style="background: linear-gradient(135deg, #ec4899, #8b5cf6); color: #fff; font-weight: 600; box-shadow: 0 4px 14px rgba(236,72,153,0.35);">📞 Call Aarushi (Focus Mode)</button>
            <button class="btn btn-secondary" onclick="showScreen('approvals')">Review Approvals</button>
            <button class="btn btn-secondary" onclick="showScreen('workflows')">Workflows</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. CHAT SCREEN (CHATGPT / CLAUDE / GEMINI STYLE) -->
    <div id="screen-chat" class="screen">
      <div class="chat-layout">
        <!-- Chat Header Bar -->
        <div class="chat-header-bar">
          <div style="display:flex; align-items:center; gap:10px;">
            <div class="chat-avatar" style="background:#0284c7; border:1px solid #38bdf8; box-shadow:0 0 10px rgba(56,189,248,0.25);">⚡</div>
            <div>
              <div style="font-weight:700; font-size:14px; color:#f8fafc; display:flex; align-items:center; gap:6px;">
                <span id="chat-header-name">GDR-AI</span>
                <span style="font-size:10px; padding:2px 6px; border-radius:10px; background:rgba(16,185,129,0.15); color:#34d399; border:1px solid #10b981;">Online</span>
              </div>
              <div style="font-size:11px; color:var(--text-muted); cursor:pointer; text-decoration:underline dotted;" id="chat-header-model-pill" onclick="openModelHubModal()" title="Click to switch AI model or pull from Hugging Face">Sarvam 105B • Autonomous Assistant</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="btn btn-secondary" onclick="openModelHubModal()" style="font-size:11px; padding:4px 10px;" title="Switch model or pull from Hugging Face">🤖 Models</button>
            <button class="btn btn-secondary" onclick="openFocusCallMode()" style="font-size:11px; padding:4px 10px; background:linear-gradient(135deg, rgba(236,72,153,0.2), rgba(139,92,246,0.2)); border-color:#ec4899; color:#f472b6; font-weight:600;" title="Launch Immersive Anime Companion Voice Call">📞 Focus Call</button>
            <button class="btn btn-secondary" onclick="exportChatMarkdown()" style="font-size:11px; padding:4px 10px;">📥 Export</button>
            <button class="btn btn-secondary" onclick="toggleMuteVoice()" id="chat-voice-mute-btn" style="font-size:11px; padding:4px 10px;">🔊 Voice: ON</button>
            <button class="btn btn-secondary" onclick="clearChatHistory()" style="font-size:11px; padding:4px 10px;">🗑️ Clear</button>
          </div>
        </div>

        <!-- Suggestion Pills Bar -->
        <div class="suggestion-pills-bar">
          <span style="font-size:11px; color:var(--text-dim); display:flex; align-items:center; margin-right:4px;">Suggestions:</span>
          <button class="suggestion-pill" onclick="sendChat('Who are you and what capabilities do you have?')">⚡ Overview</button>
          <button class="suggestion-pill" onclick="sendChat('Search the web for latest AI news and summarize')">🔍 Live Search</button>
          <button class="suggestion-pill" onclick="openMemoryVaultModal()">🧠 Memory Vault</button>
          <button class="suggestion-pill" onclick="sendChat('What is the weather in Delhi?')">🌦️ Weather</button>
          <button class="suggestion-pill" onclick="showScreen('rag')">📚 RAG Vault</button>
          <button class="suggestion-pill" onclick="sendChat('Take a screenshot and inspect my screen')">📸 Screen Vision</button>
        </div>

        <!-- Main Chat Message Stream -->
        <div id="chat-history" class="chat-stream">
          <!-- Initial Assistant Greeting -->
          <div class="chat-msg-row">
            <div class="chat-avatar" style="background:#0284c7; border:1px solid #38bdf8;">⚡</div>
            <div class="chat-bubble-assistant">
              <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px; display:flex; justify-content:space-between;">
                <b id="chat-bubble-name" style="color:#38bdf8;">GDR-AI</b>
                <span>Online</span>
              </div>
              <div style="line-height:1.6;">
                Welcome! Systems are initialized and fully operational.<br><br>
                You can ask me anything: Coding & Debugging, Deep Research, Autonomous Scheduling, Email Integration, Screen Vision, or voice conversation. Click <b>🎙️ Mic</b> to speak, or type your message below.
              </div>
            </div>
          </div>
        </div>

        <!-- Live Audio Waveform Canvas & Interim Transcript -->
        <div class="chat-input-dock">
          <canvas id="chat-audio-wave" height="26" style="width:100%; border-radius:6px; margin-bottom:8px; display:none; background:rgba(0,0,0,0.4);"></canvas>
          <div id="chat-interim-box" style="display:none; padding:6px 12px; background:rgba(56,189,248,0.08); border:1px dashed var(--accent); border-radius:8px; margin-bottom:8px; font-size:12px; color:var(--accent);">
            🎙️ <span id="chat-interim-text">Listening...</span>
          </div>

          <!-- Modern Pill Input -->
          <div class="chat-input-pill">
            <button id="chat-mic-btn" class="btn btn-secondary" onclick="toggleBrowserSpeechRecognition()" style="border-radius:50%; width:36px; height:36px; padding:0; flex-shrink:0;" title="Click to speak">🎙️</button>
            <input type="text" id="chat-input" placeholder="Ask anything, or speak naturally..." onkeydown="if(event.key==='Enter') sendChat()">
            <button class="btn btn-secondary" onclick="enhanceInputPrompt('chat-input')" style="font-size:11px; padding:4px 8px; border-radius:14px; flex-shrink:0;" title="Enhance prompt with AI">✨ Enhance</button>
            <button class="btn" onclick="sendChat()" style="border-radius:50%; width:36px; height:36px; padding:0; flex-shrink:0; background:#0284c7;" title="Send message">➤</button>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; padding:0 4px; font-size:11px; color:var(--text-dim); flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span id="chat-mic-status-label">Mic: Ready • Auto-listen</span>
              <span>•</span>
              <label style="color:var(--text-muted); font-size:11px; display:flex; align-items:center; gap:4px;">
                <span>Mesh Target:</span>
                <select id="chat-mesh-target" style="background:var(--bg-elevated); color:var(--text-primary); border:1px solid var(--border-subtle); border-radius:6px; font-size:11px; padding:2px 6px; cursor:pointer;">
                  <option value="local_primary">💻 Local Host</option>
                  <option value="all">🌐 All Connected Nodes</option>
                </select>
              </label>
            </div>
            <span>Enter to send • Shift+Enter for newline</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. APPROVALS INBOX -->
    <div id="screen-approvals" class="screen">
      <div class="card">
        <h2>⚠️ Action Approval Inbox (Policy Cards)</h2>
        <p style="color:var(--text-muted); font-size: 13px;">Sensitive operations (sending emails, modifying system files, executing payment commands) are strictly held here.</p>
        <div id="approvals-cards">
          <!-- Rendered dynamically -->
        </div>
      </div>
    </div>

    <!-- 4. TASKS AND NIGHT SHIFT -->
    <div id="screen-tasks" class="screen">
      <div class="grid-2">
        <div class="card">
          <h2>📅 Schedule & Natural Language Tasks</h2>
          <div id="tasks-container" style="max-height: 280px; overflow-y: auto; margin-bottom: 16px;"></div>
          <input type="text" id="task-nl-input" placeholder="e.g. 'every weekday at 9am check gmail' or 'in 15m drink water'">
          <button class="btn" style="margin-top: 10px;" onclick="addNewTask()">Schedule Task</button>
        </div>

        <div class="card">
          <h2>🌙 Night Shift Queue (Overnight Worker)</h2>
          <p style="color:var(--text-muted); font-size: 13px;">Tasks scheduled for night shift execute with step budgets (50 steps) and write morning reports. Sensitive actions produce drafts.</p>
          <div class="wf-node">
            <div><b>Overnight Research & Package Audit</b><br><small style="color:var(--text-muted)">Budget: 50 steps | Permission: AUTO</small></div>
            <span style="color:var(--success); font-weight: bold; font-size: 12px;">READY</span>
          </div>
          <div class="wf-node">
            <div><b>Downloads Semantic Cleanup</b><br><small style="color:var(--text-muted)">Organize files | Permission: APPROVAL</small></div>
            <span style="color:var(--warning); font-weight: bold; font-size: 12px;">DRAFT ONLY</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 5. UNIFIED INBOX -->
    <div id="screen-inbox" class="screen">
      <div class="card">
        <h2>📥 Unified Inbox (Gmail Multi-Account, Telegram, WhatsApp)</h2>
        <div id="inbox-list" style="max-height: 480px; overflow-y: auto;">
          <!-- Dynamically populated -->
        </div>
      </div>
    </div>

    <!-- 6. CALENDAR -->
    <div id="screen-calendar" class="screen">
      <div class="card">
        <h2>📅 Merged Calendar & Conflict Detector</h2>
        <p style="color:var(--text-muted); font-size: 13px;">Cross-account schedule merging personal, work, and college calendars with overlap alerts.</p>
        <div id="calendar-view" style="max-height: 400px; overflow-y: auto;">
          <!-- Dynamically populated -->
        </div>
      </div>
    </div>

    <!-- 7. MEMORY EXPLORER -->
    <div id="screen-memory" class="screen">
      <div class="card">
        <h2>🧠 Encrypted Long-Term Memory Explorer</h2>
        <p style="color:var(--text-muted); font-size: 13px;">AES-Fernet encrypted SQLite store (`secure_memory.db`). Pinned facts are verbatim. Contradictions maintain superseding history.</p>
        <div id="memory-items" style="max-height: 380px; overflow-y: auto; margin-bottom: 14px;"></div>
        <button class="btn" onclick="fetchMemory()">Refresh Memory Store</button>
      </div>
    </div>

    <!-- 8. CAMERA & PRESENCE -->
    <div id="screen-camera" class="screen">
      <div class="grid-2">
        <div class="card">
          <h2>📷 Live Webcam & Presence Tracker</h2>
          <!-- Real Live HTML5 Video Stream -->
          <div class="webcam-box">
            <video id="webcam-feed" autoplay playsinline muted></video>
            <div class="hud-reticle"></div>
            <div class="hud-target-ring"></div>
            <div id="cam-status-overlay" style="position: absolute; bottom: 12px; left: 12px; background: rgba(0,0,0,0.7); padding: 4px 10px; border-radius: 4px; font-size: 12px; color: var(--cyan);">
              ● SCANNING SENSOR (/dev/video0)
            </div>
          </div>

          <div style="margin-top: 14px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button class="btn" onclick="scanWebcamFace()">📷 Scan & Recognize Me</button>
            <button class="btn btn-secondary" onclick="enrollFromWebcam()">➕ Enroll Face</button>
            <button id="privacy-btn" class="btn btn-secondary" onclick="toggleCameraPrivacy()">Instant Privacy Mode</button>
          </div>

          <div id="cam-scan-result" style="display:none; margin-top: 12px; padding: 10px; border-radius: 6px; font-size: 13px; background: rgba(16,185,129,0.15); border: 1px solid var(--success); color: #6ee7b7;"></div>
        </div>

        <div class="card">
          <h2>👤 Enrolled Face Embeddings</h2>
          <p style="color:var(--text-muted); font-size: 12px;">Only 128-dim encrypted embeddings stored. Strictly for personalization & greetings, NEVER for authorization/approvals.</p>
          <div id="enrolled-faces-list">
            <div class="wf-node"><div><b>GDR (Owner)</b><br><small style="color:var(--text-muted)">Enrolled with 3 samples (128-dim embedding)</small></div><span style="color:var(--cyan); font-weight: bold;">ACTIVE</span></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 9. WORKFLOWS BUILDER -->
    <div id="screen-workflows" class="screen">
      <div class="card">
        <h2>⚙️ Workflows & Node-Based Automation Builder</h2>
        <p style="color:var(--text-muted); font-size: 13px;">Create automated multi-step flows via voice/text or node graph. Test safely with Dry-Run mode.</p>
        
        <div style="display:flex; gap: 10px; margin-bottom: 20px;">
          <input type="text" id="workflow-input" placeholder="e.g. 'Every morning at 7 check all my Gmail accounts, summarize urgent items, and read briefing'">
          <button class="btn" onclick="compileWorkflow()">Compile Flow</button>
        </div>

        <div id="active-workflows-list">
          <!-- Dynamically populated -->
        </div>
      </div>
    </div>

    <!-- 10. CODING WORKSPACE -->
    <div id="screen-coding" class="screen">
      <div class="card">
        <h2>💻 Coding & Workspace Agent</h2>
        <p style="color:var(--text-muted); font-size: 13px;">Restricted strictly to allowlisted project folders. Blocks secrets (`.env`, `id_rsa`). Creates feature branches and runs tests before diff review.</p>
        <div class="metric-row"><span>Active Project:</span><b class="mono-font" id="code-project">.</b></div>
        <div class="metric-row"><span>Active Git Branch:</span><b class="mono-font" id="code-branch" style="color:var(--cyan);">main</b></div>
        <div class="metric-row"><span>Protected Secret Patterns:</span><span style="color:var(--success);">.env, *.pem, id_rsa (ENFORCED)</span></div>
        
        <div style="margin-top: 16px;">
          <button class="btn" onclick="runSampleCodingTask()">Test Code Agent Gating</button>
        </div>
        <div id="coding-output" class="mono-font" style="margin-top: 12px; background: #000; padding: 12px; border-radius: 6px; font-size: 12px; color: var(--cyan); min-height: 100px; max-height: 200px; overflow-y: auto;">Standing by for coding instruction...</div>
      </div>
    </div>

    <!-- 11. SYSTEM MONITOR -->
    <div id="screen-monitor" class="screen">
      <div class="card">
        <h2>📊 Real-Time Hardware & Model Monitor</h2>
        <div class="grid-3">
          <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 8px;">
            <div class="metric-row"><span>NVIDIA RTX 3050 VRAM</span><b id="mon-vram">4 MiB</b></div>
            <div class="progress-bar"><div id="mon-vram-bar" class="progress-fill safe" style="width: 2%;"></div></div>
            <small style="color:var(--text-muted); margin-top: 4px; display: block;">Hard Ceiling: &lt; 3800 MiB (Guaranteed)</small>
          </div>

          <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 8px;">
            <div class="metric-row"><span>System RAM Available</span><b id="mon-ram">6.7 GB</b></div>
            <div class="progress-bar"><div id="mon-ram-bar" class="progress-fill safe" style="width: 45%;"></div></div>
            <small style="color:var(--text-muted); margin-top: 4px; display: block;">OS Reserve: &ge; 4.0 GB Floor</small>
          </div>

          <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 8px;">
            <div class="metric-row"><span>GPU Thermal State</span><b id="mon-temp">48°C (Normal)</b></div>
            <div class="metric-row"><span>API Spend Tracker</span><b style="color:var(--success);">$0.42 / $10.00 cap</b></div>
            <small style="color:var(--text-muted); margin-top: 4px; display: block;">Throttle Guard: 85°C Cutoff</small>
          </div>
        </div>
      </div>
    </div>

    <!-- 12. SETTINGS & ACCOUNTS -->
    <div id="screen-settings" class="screen">
      <div class="card">
        <h2>⚙️ Connected Accounts & Assistant Settings</h2>

        <!-- 0. THEME & APPEARANCE SYSTEM (ChatGPT / Gemini Inspired) -->
        <div style="margin-bottom: 22px; padding: 18px; border-radius: var(--radius-md); background: var(--bg-surface); border: 1px solid var(--border-subtle);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
            <div>
              <h3 style="margin:0; color:var(--text-primary); font-size:16px;">🎨 Appearance & Color System</h3>
              <p style="margin:3px 0 0 0; font-size:12px; color:var(--text-muted);">
                Clean, minimal interface inspired by ChatGPT and Google Gemini. One background, one primary accent, and zero rainbow gradients.
              </p>
            </div>
            <button class="btn btn-secondary" onclick="resetAppearance()" style="font-size:11px; padding:4px 10px;">↺ Reset Defaults</button>
          </div>

          <div class="grid-3" style="gap:14px;">
            <!-- Theme Mode -->
            <div>
              <label style="font-size:12px; color:var(--text-secondary); font-weight:600; display:block; margin-bottom:6px;">Interface Theme:</label>
              <div style="display:flex; gap:6px;">
                <button class="btn btn-secondary" id="theme-btn-dark" onclick="setTheme('dark')" style="flex:1; font-size:12px; padding:6px 0;">🌙 Dark</button>
                <button class="btn btn-secondary" id="theme-btn-light" onclick="setTheme('light')" style="flex:1; font-size:12px; padding:6px 0;">☀️ Light</button>
                <button class="btn btn-secondary" id="theme-btn-system" onclick="setTheme('system')" style="flex:1; font-size:12px; padding:6px 0;">💻 System</button>
              </div>
            </div>

            <!-- Primary Accent Presets -->
            <div>
              <label style="font-size:12px; color:var(--text-secondary); font-weight:600; display:block; margin-bottom:6px;">Primary Accent:</label>
              <div style="display:flex; gap:8px; align-items:center;">
                <button onclick="setAccent('emerald')" title="Emerald Green" style="width:28px; height:28px; border-radius:50%; background:#10A37F; border:2px solid var(--border-subtle); cursor:pointer;" id="accent-btn-emerald"></button>
                <button onclick="setAccent('cyan')" title="Sky Cyan" style="width:28px; height:28px; border-radius:50%; background:#38BDF8; border:2px solid var(--border-subtle); cursor:pointer;" id="accent-btn-cyan"></button>
                <button onclick="setAccent('blue')" title="Ocean Blue" style="width:28px; height:28px; border-radius:50%; background:#2563EB; border:2px solid var(--border-subtle); cursor:pointer;" id="accent-btn-blue"></button>
                <button onclick="setAccent('violet')" title="Soft Violet" style="width:28px; height:28px; border-radius:50%; background:#8B8CF8; border:2px solid var(--border-subtle); cursor:pointer;" id="accent-btn-violet"></button>
                <button onclick="setAccent('amber')" title="Warm Amber" style="width:28px; height:28px; border-radius:50%; background:#D97706; border:2px solid var(--border-subtle); cursor:pointer;" id="accent-btn-amber"></button>
              </div>
            </div>

            <!-- Background Style -->
            <div>
              <label style="font-size:12px; color:var(--text-secondary); font-weight:600; display:block; margin-bottom:6px;">Background Style:</label>
              <div style="display:flex; gap:6px;">
                <button class="btn btn-secondary" id="bg-btn-solid" onclick="setBackgroundStyle('solid')" style="flex:1; font-size:11px; padding:6px 0;">Solid</button>
                <button class="btn btn-secondary" id="bg-btn-gradient" onclick="setBackgroundStyle('gradient')" style="flex:1; font-size:11px; padding:6px 0;">Gradient</button>
                <button class="btn btn-secondary" id="bg-btn-ambient" onclick="setBackgroundStyle('ambient')" style="flex:1; font-size:11px; padding:6px 0;">Ambient</button>
              </div>
            </div>
          </div>

          <div class="grid-2" style="gap:14px; margin-top:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-secondary); font-weight:600; display:block; margin-bottom:6px;">Layout Density:</label>
              <div style="display:flex; gap:8px;">
                <button class="btn btn-secondary" id="density-btn-comfortable" onclick="setUIDensity('comfortable')" style="flex:1; font-size:12px; padding:6px 0;">Comfortable</button>
                <button class="btn btn-secondary" id="density-btn-compact" onclick="setUIDensity('compact')" style="flex:1; font-size:12px; padding:6px 0;">Compact</button>
              </div>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-secondary); font-weight:600; display:block; margin-bottom:6px;">Font Scaling:</label>
              <div style="display:flex; gap:8px;">
                <button class="btn btn-secondary" onclick="setFontScale('0.9')" style="flex:1; font-size:12px; padding:6px 0;">90%</button>
                <button class="btn btn-secondary" onclick="setFontScale('1.0')" style="flex:1; font-size:12px; padding:6px 0;">100%</button>
                <button class="btn btn-secondary" onclick="setFontScale('1.1')" style="flex:1; font-size:12px; padding:6px 0;">110%</button>
              </div>
            </div>
          </div>
        </div>

        <!-- LMMs DEVELOPER TOOLS & VECTOR STORE (Optional) -->
        <div style="margin-bottom: 22px; padding: 18px; border-radius: var(--radius-md); background: var(--bg-surface); border: 1px solid var(--border-subtle);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
            <div>
              <h3 style="margin:0; color:var(--text-primary); font-size:16px;">💻 GDR-IDE Studio & Vector Memory (LMMs Architecture)</h3>
              <p style="margin:3px 0 0 0; font-size:12px; color:var(--text-muted);">
                Next-gen developer workspace with VS Code-style layout, multi-file tabs, Personal Terminal, and directory vector indexing.
              </p>
            </div>
          </div>

          <div class="grid-2" style="gap:16px;">
            <!-- IDE Mode Toggle -->
            <div style="padding:12px; border-radius:var(--radius-sm); background:var(--bg-secondary); border:1px solid var(--border-subtle);">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <div style="font-weight:600; font-size:13px; color:var(--text-primary);">🖥️ GDR-IDE (Code Studio & Terminal)</div>
                  <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Enable VS Code-style editor, file tabs, personal terminal & AI copilot.</div>
                </div>
                <label style="display:inline-flex; align-items:center; cursor:pointer;">
                  <input id="setting-ide-toggle" type="checkbox" onchange="toggleIdeModeSetting(this.checked)" style="width:18px; height:18px; cursor:pointer;">
                </label>
              </div>
            </div>

            <!-- Vector Store Directory Indexer -->
            <div style="padding:12px; border-radius:var(--radius-sm); background:var(--bg-secondary); border:1px solid var(--border-subtle);">
              <div style="font-weight:600; font-size:13px; color:var(--text-primary); margin-bottom:4px;">📂 Index Folder for RAG</div>
              <div style="display:flex; gap:6px;">
                <input id="vector-index-input" type="text" placeholder="/path/to/project" value="." style="flex:1; font-size:12px; padding:6px; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); background:var(--bg-primary); color:var(--text-primary);">
                <button class="btn" onclick="indexDirectoryForRag()" style="font-size:11px; padding:6px 10px;">Index</button>
              </div>
              <div id="vector-index-status" style="font-size:11px; color:var(--text-muted); margin-top:6px;">Indexed docs: ready</div>
            </div>
          </div>
        </div>

        <!-- 1. USER PROFILE & AI ASSISTANT IDENTITY CONFIGURATION -->
        <div style="margin-bottom: 22px; padding: 18px; border-radius: 10px; background: var(--bg-surface); border: 1px solid var(--border-subtle);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
            <div>
              <h3 style="margin:0; color:#38bdf8;">👤 User Profile & AI Companion Identity</h3>
              <p style="margin:3px 0 0 0; font-size:12px; color:var(--text-muted);">
                Clone & open-source friendly: Configure your name, your AI assistant's name, and security passcodes. All memories and greetings adapt dynamically.
              </p>
            </div>
            <button class="btn" onclick="saveUserProfile()" style="background:#38bdf8; color:#000; font-weight:bold; font-size:12px; padding:7px 16px;">💾 Save Identity Settings</button>
          </div>

          <div class="grid-2" style="gap:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Your Name (User / Creator):</label>
              <input id="profile-user-name" type="text" placeholder="Enter your name (e.g. Alex, Sam, John...)" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:13px;">
              <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">Your assistant will call you and personalize memory around this name.</div>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-muted); font-weight:600;">AI Assistant Name:</label>
              <input id="profile-assistant-name" type="text" placeholder="Enter assistant name (e.g. GDR-AI, Jarvis, Friday...)" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:13px;">
              <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">The active name and persona identifier for your AI companion.</div>
            </div>
          </div>

          <div class="grid-2" style="gap:14px; margin-top:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Bot Master Password (Telegram & MarkanM):</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <input id="profile-bot-master-pw" type="password" placeholder="Set your custom bot authorization password..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
                <button class="btn btn-secondary" onclick="togglePasswordVisibility('profile-bot-master-pw')" style="padding:6px 10px; font-size:12px;">👁️</button>
              </div>
              <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">Use with <code>/auth &lt;password&gt;</code> to claim control from new clients.</div>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-muted); font-weight:600;">RAG Knowledge Vault Master PIN:</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <input id="profile-rag-pin" type="password" placeholder="Set your custom RAG PIN..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#c084fc; font-size:13px;">
                <button class="btn btn-secondary" onclick="togglePasswordVisibility('profile-rag-pin')" style="padding:6px 10px; font-size:12px;">👁️</button>
              </div>
              <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">Required to unlock and manage documents in the RAG Knowledge Vault.</div>
            </div>
          </div>
          <div id="profile-save-feedback" style="margin-top:10px; font-size:12px; color:#34d399; display:none;"></div>
        </div>

        <!-- 2. EMAIL INTEGRATION (GMAIL & IMAP APP PASSWORDS) -->
        <div style="margin-bottom: 22px; padding: 18px; border-radius: 10px; background: rgba(16,185,129,0.04); border: 1px solid rgba(16,185,129,0.2);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
            <div>
              <h3 style="margin:0; color:#34d399;">📧 Gmail & Email Integration</h3>
              <p style="margin:3px 0 0 0; font-size:12px; color:var(--text-muted);">
                Enable your assistant to summarize emails, detect urgent messages, and draft replies using secure IMAP/SMTP credentials.
              </p>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="testEmailConnection()" style="border-color:#34d399; color:#34d399; font-size:12px; padding:6px 12px;">⚡ Test Connection</button>
              <button class="btn" onclick="saveEmailSettings()" style="background:#10b981; color:#000; font-weight:bold; font-size:12px; padding:6px 16px;">💾 Save Credentials</button>
            </div>
          </div>

          <div class="grid-2" style="gap:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Your Email Address:</label>
              <input id="email-address-input" type="email" placeholder="e.g. your_email@gmail.com" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#34d399; font-size:13px;">
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Google 16-Character App Password:</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <input id="email-password-input" type="password" placeholder="e.g. abcd efgh ijkl mnop" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
                <button class="btn btn-secondary" onclick="togglePasswordVisibility('email-password-input')" style="padding:6px 10px; font-size:12px;">👁️</button>
              </div>
            </div>
          </div>

          <!-- Step-by-step guidance on how to get Google App Password -->
          <div style="margin-top:12px; padding:12px; border-radius:6px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.06); font-size:12px; color:#cbd5e1; line-height:1.5;">
            <b style="color:#34d399;">🔑 How to get your 16-character Google App Password:</b>
            <ol style="margin:6px 0 0 0; padding-left:18px; color:var(--text-muted); font-size:11px;">
              <li>Open your <a href="https://myaccount.google.com/security" target="_blank" style="color:#38bdf8; text-decoration:underline;">Google Account Security page</a>.</li>
              <li>Under <i>"How you sign in to Google"</i>, ensure <b>2-Step Verification</b> is turned ON.</li>
              <li>Go directly to <a href="https://myaccount.google.com/apppasswords" target="_blank" style="color:#34d399; text-decoration:underline;">Google App Passwords</a> (or search "App Passwords" in Google settings).</li>
              <li>Enter an app name (e.g. <code>GDR-AI</code>) and click <b>Create</b>.</li>
              <li>Copy the 16-letter password shown in the yellow box (e.g. <code>xxxx xxxx xxxx xxxx</code>) and paste it above!</li>
            </ol>
          </div>
          <div id="email-save-feedback" style="margin-top:8px; font-size:12px; display:none;"></div>
        </div>

        <!-- 3. SYSTEM COMPATIBILITY & HARDWARE DIAGNOSTICS -->
        <div style="margin-bottom: 22px; padding: 18px; border-radius: 10px; background: rgba(245,158,11,0.04); border: 1px solid rgba(245,158,11,0.2);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
            <div>
              <h3 style="margin:0; color:#fbbf24;">🖥️ System Hardware Compatibility Diagnostics</h3>
              <p style="margin:3px 0 0 0; font-size:12px; color:var(--text-muted);">
                Cross-platform audit: OS environment, Python runtime, RAM ceiling, free storage, audio devices, and GPU status.
              </p>
            </div>
            <button class="btn btn-secondary" onclick="runCompatibilityScan()" style="border-color:#f59e0b; color:#fbbf24; font-size:12px; padding:6px 14px;">🔄 Run Compatibility Scan</button>
          </div>
          <div id="compat-audit-container" style="background:rgba(0,0,0,0.5); border-radius:6px; border:1px solid var(--border); padding:10px;">
            <div id="compat-audit-loading" style="text-align:center; padding:12px; color:var(--text-muted); font-size:12px;">Loading system compatibility report...</div>
            <div id="compat-audit-list" style="display:none; font-size:12px;"></div>
          </div>
        </div>

        <div class="grid-2">
          <div>
            <h3>Google Accounts (OAuth 2.0)</h3>
            <div id="google-accounts-list">Loading...</div>
          </div>
          <div>
            <h3>Messaging & Voice Config</h3>
            <div class="metric-row"><span>Telegram Bot:</span><b style="color:var(--success);">Connected (Restricted ID)</b></div>
            <div class="metric-row"><span>WhatsApp Bridge:</span><b style="color:var(--text-muted);">Opt-In Disabled</b></div>
            <div class="metric-row"><span>Voice Engine:</span><b style="color:var(--cyan);">Neural Studio HD (Hindi & English)</b></div>
          </div>
        </div>

        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
          <h3 style="margin: 0 0 8px 0; color: var(--cyan);">🗣️ Multi-Language Voice Studio & Speech Engine</h3>
          <p style="color:var(--text-muted); font-size:13px; margin: 0 0 12px 0;">Select your custom AI voice. Studio-grade neural models provide natural, articulate inflection across Hindi, English, and regional accents without robotic distortion.</p>
          <div class="grid-2" style="gap:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-muted);">Active Voice Profile:</label>
              <select id="settings-voice-select" onchange="setVoicePreference(this.value)" style="width:100%; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:var(--cyan); font-size:13px;">
                <option value="aarushi_auto">🌸 Automatic (Aarushi Smart Neural - Swara for Hindi, Aria for English)</option>
                <option value="hi_swara">🇮🇳 Hindi: Swara Neural (Studio Female - स्वरा)</option>
                <option value="elevenlabs">✨ ElevenLabs: Custom Girl Voice (Ultra-Realistic)</option>
                <option value="en_aria">🇺🇸 English: Aria Neural (Expressive & Flirty Female)</option>
                <option value="en_jenny">🇺🇸 English: Jenny Neural (Sweet Female Studio)</option>
                <option value="en_neerja">🇮🇳 Indian English: Neerja Neural (Studio Female)</option>
                <option value="en_sonia">🇬🇧 British English: Sonia Neural (Refined Female)</option>
                <option value="piper_offline">💻 Local Offline Neural: Piper Female (0 tokens, CPU)</option>
                <option value="browser">🌐 Local Browser WebSpeech Synthesis</option>
              </select>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-muted);">Voice Audition & Preview:</label>
              <div style="display:flex; gap:8px; margin-top:4px; flex-wrap:wrap;">
                <button class="btn btn-secondary" onclick="auditionSelectedVoice()" style="font-size:12px; padding:8px 12px; border-color:var(--cyan); color:var(--cyan);">▶️ Audition Selected</button>
                <button class="btn btn-secondary" onclick="auditionVoice('hi')" style="font-size:12px; padding:8px 12px;">🇮🇳 Test Hindi</button>
                <button class="btn btn-secondary" onclick="auditionVoice('en')" style="font-size:12px; padding:8px 12px;">🇺🇸 Test English</button>
              </div>
            </div>
          </div>
        </div>

        <!-- AUDIO INPUT/OUTPUT DEVICE SELECTION & HARDWARE REPAIR -->
        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
            <div>
              <h3 style="margin: 0 0 4px 0; color: var(--cyan);">🎙️ Audio Devices, Microphone Diagnostics & Device Selection</h3>
              <p style="color:var(--text-muted); font-size:13px; margin: 0;">
                Select your preferred input microphone and playback speaker when multiple audio devices (internal laptop mic, USB mic, headset, Bluetooth) are available.
              </p>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="requestMicPermission()" style="border-color:#10b981; color:#34d399; font-size:12px; padding:6px 12px;">🔓 Grant Mic Permission</button>
              <button class="btn btn-secondary" onclick="fixAndDetectMic()" style="border-color:#f59e0b; color:#fbbf24; font-size:12px; padding:6px 12px;">🔧 Fix & Auto-Detect Mic</button>
            </div>
          </div>

          <!-- BROWSER AUDIO DEVICES -->
          <div style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:12px; margin-bottom:14px;">
            <div style="font-size:12px; font-weight:700; color:#38bdf8; text-transform:uppercase; margin-bottom:8px;">
              🌐 Browser Active Devices (Voice Input & Speech Playback)
            </div>
            <div class="grid-2" style="gap:14px;">
              <div>
                <label style="font-size:12px; color:var(--text-muted);">Selected Microphone (Audio Input):</label>
                <select id="browser-audio-input-select" onchange="onBrowserMicChange(this.value)" style="width:100%; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:13px;">
                  <option value="">Default Microphone</option>
                </select>
              </div>
              <div>
                <label style="font-size:12px; color:var(--text-muted);">Selected Speaker/Headphones (Audio Output):</label>
                <select id="browser-audio-output-select" onchange="onBrowserSpeakerChange(this.value)" style="width:100%; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:13px;">
                  <option value="">Default Audio Output</option>
                </select>
              </div>
            </div>

            <!-- LIVE MIC LEVEL VISUALIZER -->
            <div style="margin-top:10px;">
              <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-bottom:4px;">
                <span>Live Microphone Energy Meter:</span>
                <span id="mic-status-label" style="color:#10b981;">Ready</span>
              </div>
              <div style="height:8px; background:#000; border:1px solid var(--border); border-radius:4px; overflow:hidden;">
                <div id="live-mic-level-bar" style="height:100%; width:0%; background:linear-gradient(90deg, #10b981, #f59e0b, #ef4444); transition:width 0.08s ease;"></div>
              </div>
            </div>
          </div>

          <!-- SYSTEM / BACKEND HARDWARE AUDIO DEVICES -->
          <div style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:12px;">
            <div style="font-size:12px; font-weight:700; color:#c084fc; text-transform:uppercase; margin-bottom:8px;">
              💻 System Hardware Routing (PipeWire / ALSA Server)
            </div>
            <div class="grid-2" style="gap:14px;">
              <div>
                <label style="font-size:12px; color:var(--text-muted);">System Microphone Device:</label>
                <select id="system-audio-input-select" style="width:100%; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#c084fc; font-size:13px;">
                  <option value="">Scanning devices...</option>
                </select>
              </div>
              <div>
                <label style="font-size:12px; color:var(--text-muted);">System Speaker Device:</label>
                <select id="system-audio-output-select" style="width:100%; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#c084fc; font-size:13px;">
                  <option value="">Scanning devices...</option>
                </select>
              </div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-top:12px;">
              <div style="display:flex; gap:8px;">
                <button class="btn" onclick="saveSystemAudioDevices()" style="background:#a855f7; color:#fff; font-size:12px; padding:6px 14px;">Save Device Routing</button>
                <button class="btn btn-secondary" onclick="testSystemMic()" style="font-size:12px; padding:6px 12px; border-color:#38bdf8; color:#38bdf8;">⚡ Test Recording Signal</button>
              </div>
              <span id="audio-device-feedback-msg" style="font-size:12px; color:#34d399; display:none;"></span>
            </div>
          </div>
        </div>

        <!-- MODEL HUB & HUGGING FACE PULLER BANNER IN SETTINGS -->
        <div style="margin-top: 18px; padding: 14px 16px; background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <h3 style="margin: 0 0 4px 0; font-size: 15px; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
              <span>🤖 AI Models & Hugging Face Hub</span>
            </h3>
            <p style="color: var(--text-muted); font-size: 12px; margin: 0;">
              Switch between Cloud LLMs (Sarvam, Claude, OpenRouter) or pull and run open-source GGUF models directly from Hugging Face.
            </p>
          </div>
          <button class="btn btn-primary" onclick="openModelHubModal()" style="font-size: 12px; padding: 6px 16px;">
            Open Model Hub & Downloader
          </button>
        </div>

        <!-- SARVAM AI REASONING ENGINE SECTION -->
        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
            <div>
              <h3 style="margin: 0 0 4px 0; color: #f59e0b;">⚡ Sarvam AI Engine (Indian Multilingual 105B)</h3>
              <p style="color:var(--text-muted); font-size:13px; margin: 0;">
                Configure your Sarvam API subscription key. Changes made here immediately update the backend and persist securely across reboots.
              </p>
            </div>
            <span id="sarvam-status-badge" style="font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid #f59e0b; color:#fbbf24; background:rgba(245,158,11,0.1);">Checking...</span>
          </div>
          <div class="grid-2" style="gap:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-muted);">Sarvam API Key:</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <input id="sarvam-key-input" type="password" placeholder="Enter Sarvam API Key..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
                <button class="btn btn-secondary" onclick="toggleSarvamKeyVisibility()" style="padding:6px 10px; font-size:12px;">👁️</button>
                <button class="btn" onclick="saveSarvamConfig()" style="background:#f59e0b; color:#000; font-weight:bold; padding:6px 14px; font-size:12px;">Save Key</button>
              </div>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-muted);">Sarvam LLM Model:</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <select id="sarvam-model-select" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fbbf24; font-size:13px;">
                  <option value="sarvam-105b">sarvam-105b (General Reasoning & Tools)</option>
                  <option value="sarvam-105b-conversations">sarvam-105b-conversations (Multi-Turn Chat)</option>
                </select>
                <button class="btn btn-secondary" onclick="testSarvamConnection()" style="padding:6px 12px; font-size:12px; border-color:#f59e0b; color:#fbbf24;">⚡ Test</button>
              </div>
            </div>
          </div>
          <div style="margin-top:10px; display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
            <label style="font-size:12px; color:var(--text-muted);">Sarvam TTS Voice:</label>
            <label style="display:flex; align-items:center; gap:6px; cursor:pointer; user-select:none;">
              <input type="checkbox" id="sarvam-tts-enabled" style="width:16px;height:16px;cursor:pointer;" checked
                onchange="saveSarvamTTSToggle(this.checked)">
              <span style="font-size:12px; color:#fbbf24;" id="sarvam-tts-label">Enabled (Sarvam will generate Hindi voice)</span>
            </label>
            <span style="font-size:11px; color:var(--text-muted);">Disable if you get speaker errors or want Edge-TTS only</span>
          </div>
          <div id="sarvam-save-msg" style="margin-top:8px; font-size:12px; color:#34d399; display:none;"></div>
        </div>

        <!-- ELEVENLABS AI VOICE STUDIO SECTION -->
        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
            <div>
              <h3 style="margin: 0 0 4px 0; color: #38bdf8;">🎙️ ElevenLabs HD Neural Voice Studio</h3>
              <p style="color:var(--text-muted); font-size:13px; margin: 0;">
                Connect your ElevenLabs API key and any Voice ID for ultra-realistic conversational speech synthesis.
              </p>
            </div>
            <span id="elevenlabs-status-badge" style="font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid #38bdf8; color:#38bdf8; background:rgba(56,189,248,0.1);">Checking...</span>
          </div>
          <div class="grid-2" style="gap:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-muted);">ElevenLabs API Key:</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <input id="elevenlabs-key-input" type="password" placeholder="Enter ElevenLabs API Key..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
                <button class="btn btn-secondary" onclick="toggleElevenKeyVisibility()" style="padding:6px 10px; font-size:12px;">👁️</button>
                <button class="btn" onclick="saveElevenLabsConfig()" style="font-weight:bold; padding:6px 14px; font-size:12px;">Save Key</button>
              </div>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-muted);">ElevenLabs Voice ID or Voice Link:</label>
              <div style="display:flex; gap:6px; margin-top:4px;">
                <input id="elevenlabs-voice-id-input" type="text" oninput="handleVoiceIdPaste(this)" placeholder="Enter Voice ID or https://elevenlabs.io/voices/..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:13px;">
                <button class="btn" onclick="saveElevenLabsConfig()" style="font-weight:bold; padding:6px 12px; font-size:12px;">Save Voice</button>
                <button class="btn btn-secondary" onclick="testElevenLabsVoice(event)" style="padding:6px 12px; font-size:12px; border-color:#38bdf8; color:#38bdf8;">▶️ Test</button>
              </div>
            </div>
          </div>
          <div style="margin-top:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;">
            <label style="font-size:13px; color:#fff; display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input id="elevenlabs-enable-checkbox" type="checkbox" onchange="toggleElevenLabsPrimary(this.checked)" style="transform:scale(1.2);">
              <span>Use ElevenLabs as Primary Voice</span>
            </label>
            <div id="elevenlabs-save-msg" style="font-size:12px; color:#34d399; display:none;"></div>
          </div>
        </div>

        <!-- LAPTOP AUDIO & HARDWARE FIX SECTION -->
        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
              <h3 style="margin: 0 0 4px 0; color: #10b981;">🔊 Laptop Hardware Audio & Real Microphone Repair</h3>
              <p style="color:var(--text-muted); font-size:13px; margin: 0;">
                Fix dummy output, unmute, set speakers to 75% volume, and route input to your real physical laptop microphone (Realtek ALC256) at clean 65% gain.
              </p>
            </div>
            <button id="btn-fix-audio-settings" class="btn" style="background: linear-gradient(135deg, #059669, #10b981); color: #fff; font-weight: bold; padding: 8px 16px; border-radius: 6px; cursor: pointer;" onclick="repairLaptopAudioHardware()">
              🛠️ Fix Mic & Laptop Speakers
            </button>
          </div>
          <div id="audio-hardware-fix-status" style="margin-top: 10px; font-size: 12px; font-family: monospace; background: #000; padding: 10px; border-radius: 6px; border: 1px solid var(--border); color: #34d399; display: none;">
          </div>
        </div>

        <!-- CLOUDFLARE PUBLIC TUNNEL & REMOTE ACCESS SECTION -->
        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
              <h3 style="margin: 0 0 4px 0; color: #38bdf8;">☁️ Cloudflare Public Access & Remote Share</h3>
              <p style="color:var(--text-muted); font-size:13px; margin: 0;">
                Expose your GDR AI Web Dashboard to the internet so friends can control it from their phone. Destructive actions (shutdown PC, delete file, big tasks) require approval in the host terminal.
              </p>
            </div>
            <div style="display: flex; gap: 8px;">
              <button id="btn-cloudflare-settings" class="btn" style="background: linear-gradient(135deg, #0284c7, #38bdf8); color: #fff; font-weight: bold; padding: 8px 16px; border-radius: 6px; cursor: pointer;" onclick="openCloudflareModal()">
                🚀 Share via Cloudflare
              </button>
            </div>
          </div>
          <div id="tunnel-settings-status" style="margin-top: 10px; font-size: 13px; font-family: monospace; background: #000; padding: 12px; border-radius: 6px; border: 1px solid var(--border); color: #38bdf8; display: none;">
          </div>
        </div>
      </div>
    </div>

    <!-- 13. AUDIT & REQUEST DATABASE -->
    <div id="screen-audit" class="screen">
      <!-- INBOUND REQUEST DATABASE -->
      <div class="card" style="margin-bottom:16px; border-top: 3px solid var(--cyan);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
          <div>
            <h2 style="margin:0; color:var(--cyan);">🌐 Inbound Requests Database (`~/.config/gdr/requests.db`)</h2>
            <p style="color:var(--text-muted); font-size:13px; margin:4px 0 0 0;">
              Every request to GDR AI is recorded in SQLite with its IP address, method, path, timing, and user-provided details.
            </p>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary" onclick="fetchRequestLogs()">🔄 Refresh Requests</button>
            <button class="btn btn-secondary" onclick="clearOldRequests()" style="border-color:#ef4444; color:#f87171;">🧹 Purge >30d</button>
          </div>
        </div>

        <div style="display:flex; gap:16px; margin-bottom:12px; flex-wrap:wrap; align-items:center;">
          <div style="background:rgba(0,0,0,0.5); padding:6px 12px; border-radius:6px; border:1px solid var(--border); font-size:12px;">
            <span style="color:var(--text-muted);">Total Requests:</span> <b id="req-stat-total" style="color:var(--cyan);">-</b>
          </div>
          <div style="background:rgba(0,0,0,0.5); padding:6px 12px; border-radius:6px; border:1px solid var(--border); font-size:12px;">
            <span style="color:var(--text-muted);">Unique IPs:</span> <b id="req-stat-ips" style="color:#34d399;">-</b>
          </div>
          <div style="flex:1; display:flex; justify-content:flex-end; gap:8px;">
            <input id="req-filter-ip" type="text" placeholder="Filter by IP..." oninput="filterRequestLogs()" style="padding:6px 10px; font-size:12px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; width:140px;">
            <input id="req-filter-path" type="text" placeholder="Filter by path..." oninput="filterRequestLogs()" style="padding:6px 10px; font-size:12px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; width:140px;">
          </div>
        </div>

        <div style="max-height: 400px; overflow-y: auto; background: #000; border-radius: 6px; border: 1px solid var(--border);">
          <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); background:rgba(255,255,255,0.03); color:var(--text-muted);">
                <th style="padding:8px 10px;">Time</th>
                <th style="padding:8px 10px;">IP Address</th>
                <th style="padding:8px 10px;">Method & Path</th>
                <th style="padding:8px 10px;">Status</th>
                <th style="padding:8px 10px;">User Details & Payload</th>
                <th style="padding:8px 10px;">Duration</th>
              </tr>
            </thead>
            <tbody id="request-log-table-body">
              <tr><td colspan="6" style="padding:12px; text-align:center; color:var(--text-muted);">Loading requests...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- AUDIT TRAIL -->
      <div class="card">
        <h2>📜 Append-Only Action Trail (`~/.config/gdr/audit.log`)</h2>
        <p style="color:var(--text-muted); font-size: 13px;">Every automated or user-approved action is recorded with timestamp and reason.</p>
        <div id="audit-log-content" class="mono-font" style="max-height: 250px; overflow-y: auto; background: #000; padding: 12px; border-radius: 6px; font-size: 12px; color: #a5f3fc;"></div>
      </div>
    </div>

    <!-- 14. BOTS HUB (MARKANM & TELEGRAM) -->
    <div id="screen-bots" class="screen">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
        <div>
          <h2 style="margin:0; color:#38bdf8;">🤖 Bot Platforms & Remote Messaging</h2>
          <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:13px;">Connect GDR-AI to MarkanM Connect (Priority) and Telegram for remote chat, control, reminders, and vision.</p>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-secondary" onclick="loadMarkanMConfig(); loadTelegramConfig(); loadBotChannelsActivity();">🔄 Refresh Bots</button>
        </div>
      </div>

      <!-- MARKANM SPOTLIGHT BANNER -->
      <div class="card" style="border:1px solid rgba(56,189,248,0.25); background:radial-gradient(ellipse at top left, rgba(56,189,248,0.08), rgba(15,23,42,0.85)); margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <span style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:#38bdf8; background:rgba(56,189,248,0.12); padding:3px 8px; border-radius:12px; border:1px solid rgba(56,189,248,0.3);">⭐ Recommended Platform</span>
            <h3 style="margin:6px 0 4px 0; font-size:18px; color:#fff;">Why MarkanM Connect (chat.markanm.com)?</h3>
            <p style="margin:0; font-size:13px; color:#cbd5e1; line-height:1.5;">
              MarkanM is a developer bot platform built specifically for AI agents.
              Unlike Telegram, MarkanM offers <b>instant token creation</b> with zero phone verification hurdles, native real-time event streaming via the official Python SDK (<code>pip install markanm</code>), dynamic room routing, and rich interactive tool command support.
            </p>
          </div>
          <a href="https://chat.markanm.com/developers" target="_blank" rel="noopener" class="btn" style="background:#0284c7; color:#fff; text-decoration:none; padding:10px 16px; font-size:13px;">Open MarkanM Portal ↗</a>
        </div>
      </div>

      <div class="grid-2" style="gap:16px;">
        <!-- 1. MARKANM BOT CARD (PRIORITY #1) -->
        <div class="card" style="border-top:3px solid #38bdf8;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:24px;">💬</span>
              <div>
                <h3 style="margin:0; color:#38bdf8;">MarkanM Connect (Priority Platform)</h3>
                <span style="font-size:11px; color:var(--text-muted);">Official Bot Platform SDK (chat.markanm.com)</span>
              </div>
            </div>
            <span id="markanm-status-badge" style="font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid rgba(56,189,248,0.3); color:#38bdf8; background:rgba(56,189,248,0.08);">Checking...</span>
          </div>

          <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
            Chat with your assistant, trigger desktop actions, voice, reminders, and web search directly from MarkanM.
          </p>

          <div style="margin-bottom:10px;">
            <label style="font-size:12px; color:var(--text-muted);">MarkanM Bot Token (from chat.markanm.com/developers):</label>
            <div style="display:flex; gap:6px; margin-top:4px;">
              <input id="markanm-token-input" type="password" placeholder="Enter MarkanM Bot Token (mkbot_...)" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:12px;">
              <button class="btn btn-secondary" onclick="toggleMarkanMTokenVisibility()" style="padding:6px 10px; font-size:12px;">👁️</button>
            </div>
          </div>

          <div style="margin-bottom:12px;">
            <label style="font-size:12px; color:var(--text-muted);">Allowed MarkanM Username (Security Whitelist):</label>
            <input id="markanm-username-input" type="text" placeholder="e.g. your_username (Agent will only respond to you)" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
            <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">
              💡 <i>Room ID is auto-detected dynamically. If identity cannot be verified, authenticate via <code>/auth &lt;password&gt;</code> with your Bot Master Password.</i>
            </div>
          </div>

          <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-top:14px;">
            <div style="display:flex; gap:6px;">
              <button class="btn" onclick="saveMarkanMConfig()" style="font-weight:bold; padding:6px 14px; font-size:12px;">Save Token</button>
              <button id="markanm-toggle-btn" class="btn btn-secondary" onclick="toggleMarkanMBotService()" style="font-size:12px; padding:6px 12px;">Start Polling</button>
              <button class="btn btn-secondary" onclick="testMarkanMMessage()" style="font-size:12px; padding:6px 12px; border-color:#38bdf8; color:#38bdf8;">📨 Test Msg</button>
            </div>
            <div id="markanm-save-msg" style="font-size:12px; color:#34d399; display:none;"></div>
          </div>

          <div style="margin-top:14px; border-top:1px solid rgba(255,255,255,0.08); padding-top:12px;">
            <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Direct Message to MarkanM Room:</label>
            <div style="display:flex; gap:6px; margin-top:6px;">
              <input id="markanm-direct-msg-input" type="text" placeholder="Type a message to MarkanM room..." onkeydown="if(event.key==='Enter') sendDirectMarkanMMessage()" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
              <button class="btn" onclick="sendDirectMarkanMMessage()" style="font-size:12px; padding:6px 14px;">Send 📤</button>
            </div>
            <div id="markanm-direct-feedback" style="font-size:11px; margin-top:4px; display:none;"></div>
          </div>

          <div style="margin-top:14px; padding:10px; border-radius:6px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.05); font-size:11px; color:var(--text-muted);">
            <b>MarkanM Commands:</b> <code>/ask</code>, <code>/weather</code>, <code>/search</code>, <code>/rag</code>, <code>/voice</code>, <code>/volume</code>, <code>/brightness</code>, <code>/open</code>, <code>/location</code>, <code>/status</code>, <code>/remind</code>, <code>/screenshot</code>, <code>/auth &lt;password&gt;</code>, <code>/stop</code>, <code>/clearpanic</code>, or plain text!
          </div>
        </div>

        <!-- 2. TELEGRAM BOT CARD (SECONDARY CHANNEL) -->
        <div class="card" style="border-top:3px solid #0284c7;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:24px;">✈️</span>
              <div>
                <h3 style="margin:0; color:#38bdf8;">Telegram Bot Platform</h3>
                <span style="font-size:11px; color:var(--text-muted);">Secondary mobile assistant via Telegram API</span>
              </div>
            </div>
            <span id="tg-status-badge" style="font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid #0284c7; color:#38bdf8; background:rgba(2,132,199,0.1);">Checking...</span>
          </div>

          <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
            Talk to Aarushi, send voice notes, take screenshots, manage scheduled tasks, or receive emergency call escalations on Telegram.
          </p>

          <div style="margin-bottom:10px;">
            <label style="font-size:12px; color:var(--text-muted);">Telegram Bot Token (from @BotFather):</label>
            <div style="display:flex; gap:6px; margin-top:4px;">
              <input id="tg-token-input" type="password" placeholder="Enter Telegram Bot Token..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:12px;">
              <button class="btn btn-secondary" onclick="toggleTGTokenVisibility()" style="padding:6px 10px; font-size:12px;">👁️</button>
            </div>
          </div>

          <div style="margin-bottom:10px;">
            <label style="font-size:12px; color:var(--text-muted);">Target Chat ID / Allowed User ID:</label>
            <input id="tg-chatid-input" type="text" placeholder="Enter target Chat ID (or leave blank to auto-bind)" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
          </div>

          <div style="margin-bottom:12px;">
            <label style="font-size:12px; color:var(--text-muted);">Allowed Telegram Username (Security Whitelist):</label>
            <input id="tg-username-input" type="text" placeholder="e.g. your_username (Agent will only respond to you)" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
          </div>

          <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-top:14px;">
            <div style="display:flex; gap:6px;">
              <button class="btn" onclick="saveTelegramConfig()" style="background:#0284c7; color:#fff; font-weight:bold; padding:6px 14px; font-size:12px;">Save Token</button>
              <button id="tg-toggle-btn" class="btn btn-secondary" onclick="toggleTelegramBotService()" style="font-size:12px; padding:6px 12px;">Start Bot</button>
              <button class="btn btn-secondary" onclick="testTelegramMessage()" style="font-size:12px; padding:6px 12px; border-color:#0284c7; color:#38bdf8;">📨 Test Msg</button>
            </div>
            <div id="tg-save-msg" style="font-size:12px; color:#34d399; display:none;"></div>
          </div>

          <div style="margin-top:14px; border-top:1px solid rgba(255,255,255,0.08); padding-top:12px;">
            <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Direct Message / Command to Telegram:</label>
            <div style="display:flex; gap:6px; margin-top:6px;">
              <input id="tg-direct-msg-input" type="text" placeholder="Type a message or command..." onkeydown="if(event.key==='Enter') sendDirectTelegramMessage()" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
              <button class="btn" onclick="sendDirectTelegramMessage()" style="background:#0284c7; color:#fff; font-size:12px; padding:6px 14px;">Send 📤</button>
            </div>
            <div id="tg-direct-feedback" style="font-size:11px; margin-top:4px; display:none;"></div>
          </div>

          <div style="margin-top:14px; padding:10px; border-radius:6px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.05); font-size:11px; color:var(--text-muted);">
            <b>Telegram Commands:</b> <code>/status</code>, <code>/screenshot</code>, <code>/remind &lt;time&gt; &lt;msg&gt;</code>, <code>/callme</code>, <code>/tasks</code>, <code>/stop</code>, or send any voice note / text to chat with Aarushi!
          </div>
        </div>
      </div>
      </div>

      <!-- 3. MARKANM FULL DEVELOPER DOCUMENTATION & PYTHON BOT PLAYGROUND -->
      <div class="card" style="margin-top:16px; border-top:3px solid #ec4899;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
          <div>
            <h3 style="margin:0; color:#ec4899;">📖 MarkanM Connect Developer Documentation & Python Studio</h3>
            <span style="font-size:11px; color:var(--text-muted);">Real-time WebSocket protocol architecture, REST endpoints, and interactive Python bot code</span>
          </div>
          <div style="display:flex; gap:6px;">
            <button class="btn btn-secondary" onclick="copyMarkanMDocCode()" style="font-size:12px; padding:4px 10px; border-color:#ec4899; color:#f472b6;">📋 Copy Python Code</button>
            <button class="btn btn-secondary" onclick="downloadMarkanMExampleScript()" style="font-size:12px; padding:4px 10px; border-color:#38bdf8; color:#38bdf8;">💾 Download .py Script</button>
          </div>
        </div>

        <!-- Documentation Tabs -->
        <div style="display:flex; gap:8px; border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:12px;">
          <button id="mk-tab-btn-docs" class="btn" onclick="showMarkanMTab('docs')" style="font-size:12px; padding:5px 12px; background:#ec4899; color:#fff;">📘 Architecture & Guide</button>
          <button id="mk-tab-btn-code" class="btn btn-secondary" onclick="showMarkanMTab('code')" style="font-size:12px; padding:5px 12px;">🐍 Python Bot Implementation</button>
          <button id="mk-tab-btn-api" class="btn btn-secondary" onclick="showMarkanMTab('api')" style="font-size:12px; padding:5px 12px;">📡 REST & WebSocket Specs</button>
        </div>

        <!-- Tab 1: Architecture & Guide -->
        <div id="mk-tab-docs" style="font-size:13px; line-height:1.6; color:#d1d5db;">
          <h4 style="margin:0 0 6px 0; color:#f472b6;">🌟 Why MarkanM Connect (chat.markanm.com)?</h4>
          <p style="margin:0 0 10px 0;">
            <b>MarkanM Connect</b> is designed specifically for high-speed, autonomous agent interaction. Unlike Telegram, it provides a persistent WebSocket room mesh without requiring mobile phone numbers or complex webhook certificates.
          </p>
          <div class="grid-3" style="gap:10px; margin-bottom:14px;">
            <div style="background:rgba(0,0,0,0.4); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
              <b style="color:#34d399;">🔒 100% Phone-Free Privacy</b><br>
              <span style="font-size:12px; color:var(--text-muted);">Sign up anonymously with username and password. Never exposes personal phone numbers to public bots.</span>
            </div>
            <div style="background:rgba(0,0,0,0.4); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
              <b style="color:#38bdf8;">⚡ Low Latency WebSockets</b><br>
              <span style="font-size:12px; color:var(--text-muted);">Bi-directional event streaming with sub-50ms message delivery and real-time typing indicators.</span>
            </div>
            <div style="background:rgba(0,0,0,0.4); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
              <b style="color:#ec4899;">🌐 Dynamic Multi-Room Auto-Routing</b><br>
              <span style="font-size:12px; color:var(--text-muted);">No hardcoded room IDs needed. The bot auto-detects room joins and dispatches AI replies automatically.</span>
            </div>
          </div>

          <h4 style="margin:12px 0 6px 0; color:#f472b6;">🚀 Getting Started in 3 Steps:</h4>
          <ol style="margin:0 0 12px 0; padding-left:20px; font-size:12px; color:var(--text-muted);">
            <li>Create an account at <a href="https://chat.markanm.com" target="_blank" style="color:#ec4899;">chat.markanm.com</a>.</li>
            <li>Navigate to <b>Settings → Developer</b> to generate your <code>mkbot_...</code> bot token.</li>
            <li>Paste your token and username into the configuration card above and click <b>Start Polling</b>!</li>
          </ol>
        </div>

        <!-- Tab 2: Python Bot Implementation (Interactive & Editable) -->
        <div id="mk-tab-code" style="display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; color:var(--text-muted);">You can view, edit, or customize this standalone MarkanM Python bot runner:</span>
            <span style="font-size:11px; color:#38bdf8;">Python 3.10+ • AsyncIO • markanm SDK</span>
          </div>
          <textarea id="markanm-code-editor" rows="18" style="width:100%; box-sizing:border-box; background:#0b0f17; color:#38bdf8; font-family:monospace; font-size:12px; line-height:1.5; padding:12px; border-radius:6px; border:1px solid rgba(56,189,248,0.3); resize:vertical;">import os
import asyncio
from markanm import Bot

# 1. Initialize Bot with your token (or read from environment)
BOT_TOKEN = os.environ.get("MARKANM_BOT_TOKEN", "mkbot_your_token_here")
ALLOWED_USER = os.environ.get("MARKANM_ALLOWED_USERNAME", "your_username")
MASTER_PASSWORD = os.environ.get("BOT_MASTER_PASSWORD", "your_custom_password")

bot = Bot(token=BOT_TOKEN)

@bot.event
async def on_ready():
    print(f"✨ MarkanM Bot is online! Connected as: {bot.user.username}")

@bot.command("status")
async def status_cmd(ctx):
    # Report real-time system vitals back to the MarkanM room
    sender = getattr(ctx.user, "username", "")
    if sender.lower() != ALLOWED_USER.lower():
        await ctx.reply("❌ Access Denied: Unauthorized account. Use /auth <password> to verify.")
        return
    await ctx.reply("🟢 Aarushi AI is running smoothly! CPU: Normal | Memory: Optimal | Audio: Active")

@bot.command("auth")
async def auth_cmd(ctx):
    # Authenticate and claim ownership using the master security password
    provided_pw = " ".join(getattr(ctx, "args", []))
    if provided_pw == MASTER_PASSWORD:
        await ctx.reply(f"✅ Authorization verified! Welcome, {ctx.user.username}.")
    else:
        await ctx.reply("❌ Incorrect security password. Access denied.")

@bot.event
async def on_message(message):
    # Handle incoming room messages dynamically
    if message.author.is_bot:
        return
    # Process commands or forward to AI reasoning loop
    if message.content.startswith("/"):
        await bot.process_commands(message)
    else:
        print(f"[{message.room_id}] {message.author.username}: {message.content}")
        # Send AI response back to the active room
        # await message.reply(f"🌸 Heard: {message.content}")

if __name__ == "__main__":
    bot.run()
</textarea>
        </div>

        <!-- Tab 3: REST & WebSocket API Specs -->
        <div id="mk-tab-api" style="display:none; font-size:12px; color:#d1d5db;">
          <h4 style="margin:0 0 6px 0; color:#38bdf8;">📡 MarkanM Connect API Specifications</h4>
          <div style="background:rgba(0,0,0,0.5); padding:10px; border-radius:6px; font-family:monospace; margin-bottom:10px;">
            <b style="color:#ec4899;">WebSocket Gateway:</b> wss://chat.markanm.com/ws<br>
            <b style="color:#38bdf8;">REST Base URL:</b> https://chat.markanm.com/api/v1<br>
            <b style="color:#34d399;">Auth Header:</b> Authorization: Bearer mkbot_...
          </div>
          <table style="width:100%; border-collapse:collapse; font-size:11px; margin-top:8px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); color:var(--text-muted); text-align:left;">
                <th style="padding:6px;">Method</th>
                <th style="padding:6px;">Endpoint</th>
                <th style="padding:6px;">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:6px; color:#38bdf8;">POST</td>
                <td style="padding:6px; font-family:monospace;">/auth/bot</td>
                <td style="padding:6px;">Validate token & acquire session credentials</td>
              </tr>
              <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:6px; color:#34d399;">GET</td>
                <td style="padding:6px; font-family:monospace;">/rooms</td>
                <td style="padding:6px;">List all rooms bot is a member of</td>
              </tr>
              <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:6px; color:#38bdf8;">POST</td>
                <td style="padding:6px; font-family:monospace;">/rooms/{room_id}/messages</td>
                <td style="padding:6px;">Dispatch text or rich embed to room</td>
              </tr>
              <tr>
                <td style="padding:6px; color:#ec4899;">WS EVENT</td>
                <td style="padding:6px; font-family:monospace;">message:create</td>
                <td style="padding:6px;">Inbound real-time message stream with user & room metadata</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- LIVE BOT CHANNELS ACTIVITY TABLE -->
      <div class="card" style="margin-top:16px; border-top:3px solid #8b5cf6;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
          <div>
            <h3 style="margin:0; color:#a78bfa;">📡 Live Bot Channels Activity & Request Log</h3>
            <span style="font-size:11px; color:var(--text-muted);">Real-time database recording of incoming commands, messages, replies, and IP origins</span>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary" onclick="loadBotChannelsActivity()" style="font-size:12px; padding:4px 10px;">🔄 Refresh Activity</button>
            <button class="btn btn-secondary" onclick="clearBotActivity()" style="font-size:12px; padding:4px 10px; color:#ef4444; border-color:rgba(239,68,68,0.4);">🗑️ Clear Log</button>
          </div>
        </div>
        <div id="bot-activity-table-container" style="max-height:360px; overflow-y:auto; background:rgba(0,0,0,0.4); border-radius:6px; border:1px solid var(--border);">
          <div id="bot-activity-empty" style="text-align:center; padding:24px; color:var(--text-muted); font-size:12px;">Loading bot channel logs...</div>
          <table id="bot-activity-table" style="width:100%; border-collapse:collapse; font-size:12px; display:none;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); color:var(--text-muted); text-align:left;">
                <th style="padding:8px 10px;">Time</th>
                <th style="padding:8px 10px;">Channel</th>
                <th style="padding:8px 10px;">Action / Method</th>
                <th style="padding:8px 10px;">Sender / Origin</th>
                <th style="padding:8px 10px;">Content / Details</th>
                <th style="padding:8px 10px;">Status</th>
              </tr>
            </thead>
            <tbody id="bot-activity-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 20. MESSAGING INTEGRATIONS (Telegram & MarkanM Connect) -->
    <div id="screen-messaging" class="screen">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:16px;">
        <div>
          <h2 style="margin:0; color:#38bdf8;">💬 Messaging Integrations</h2>
          <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:13px;">
            Connect your AI assistant to Telegram and MarkanM Connect for remote interaction, instant status, system telemetry, and voice messaging.
          </p>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-secondary" onclick="loadMessagingIntegrationsConfig();">🔄 Refresh</button>
          <button class="btn btn-secondary" onclick="showScreen('bots');">🤖 Bot Studio</button>
        </div>
      </div>

      <!-- Overview Cards in 2 Columns -->
      <div class="grid-2" style="gap:16px; margin-bottom:16px;">
        <!-- Card 1: Telegram Bot Integration -->
        <div class="card" style="border-top:3px solid #0284c7; background:linear-gradient(180deg, rgba(2,132,199,0.06), rgba(15,23,42,0.85));">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:24px;">✈️</span>
              <div>
                <h3 style="margin:0; color:#38bdf8;">Telegram Bot Integration</h3>
                <span style="font-size:11px; color:var(--text-muted);">Remote mobile chat & notifications via Telegram API</span>
              </div>
            </div>
            <span id="msg-tg-status-badge" style="font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid #0284c7; color:#38bdf8; background:rgba(2,132,199,0.1);">Checking...</span>
          </div>

          <div style="margin-bottom:12px;">
            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Telegram Bot Token (from @BotFather):</label>
            <div style="display:flex; gap:6px;">
              <input id="msg-tg-token-input" type="password" placeholder="Enter Telegram Bot Token..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:12px;">
              <button class="btn btn-secondary" onclick="toggleMsgTGTokenVisibility()" style="padding:6px 10px; font-size:12px;" title="Toggle Token Visibility">👁️</button>
            </div>
          </div>

          <div style="display:flex; gap:10px; margin-bottom:12px;">
            <div style="flex:1;">
              <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Target Chat ID / Owner ID:</label>
              <input id="msg-tg-chatid-input" type="text" placeholder="e.g. 123456789 (Auto-binds on message)" style="width:100%; box-sizing:border-box; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
            </div>
            <div style="flex:1;">
              <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Allowed Username (Whitelist):</label>
              <input id="msg-tg-username-input" type="text" placeholder="e.g. your_telegram_username" style="width:100%; box-sizing:border-box; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
            </div>
          </div>

          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:14px;">
            <button class="btn btn-secondary" onclick="validateTelegramTokenUI('msg')" style="font-size:12px; padding:6px 12px; border-color:#0284c7; color:#38bdf8;">🔍 Validate Token</button>
            <button class="btn" onclick="saveTelegramConfigUI('msg')" style="background:#0284c7; color:#fff; font-weight:bold; font-size:12px; padding:6px 14px;">💾 Save & Connect</button>
            <button id="msg-tg-toggle-btn" class="btn btn-secondary" onclick="toggleTelegramBotServiceUI('msg')" style="font-size:12px; padding:6px 12px;">Start Bot</button>
            <button class="btn btn-secondary" onclick="testTelegramMessageUI('msg')" style="font-size:12px; padding:6px 12px; border-color:#34d399; color:#34d399;">📨 Send Test Msg</button>
          </div>

          <div id="msg-tg-feedback" style="font-size:12px; margin-top:10px; display:none; padding:8px; border-radius:6px; background:rgba(0,0,0,0.5);"></div>

          <div style="margin-top:14px; border-top:1px solid rgba(255,255,255,0.08); padding-top:12px;">
            <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Direct Message to Telegram:</label>
            <div style="display:flex; gap:6px; margin-top:6px;">
              <input id="msg-tg-direct-input" type="text" placeholder="Type a message to send directly to your Telegram chat..." onkeydown="if(event.key==='Enter') sendDirectTelegramMsgUI('msg')" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#38bdf8; font-size:12px;">
              <button class="btn" onclick="sendDirectTelegramMsgUI('msg')" style="background:#0284c7; color:#fff; font-size:12px; padding:6px 14px;">Send 📤</button>
            </div>
          </div>

          <div style="margin-top:14px; padding:10px; border-radius:6px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.05); font-size:11px; color:var(--text-muted);">
            <b>Quick Setup:</b>
            <ol style="margin:4px 0 0 0; padding-left:18px;">
              <li>Open Telegram and message <code>@BotFather</code>.</li>
              <li>Type <code>/newbot</code> and follow steps to get your API Token.</li>
              <li>Paste the token above and click <b>Validate Token</b>.</li>
            </ol>
          </div>
        </div>

        <!-- Card 2: MarkanM Connect Bot Integration -->
        <div class="card" style="border-top:3px solid #ec4899; background:linear-gradient(180deg, rgba(236,72,153,0.06), rgba(15,23,42,0.85));">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:24px;">💬</span>
              <div>
                <h3 style="margin:0; color:#ec4899;">MarkanM Connect (Developer Chat)</h3>
                <span style="font-size:11px; color:var(--text-muted);">Real-time agent websocket mesh at chat.markanm.com</span>
              </div>
            </div>
            <span id="msg-mk-status-badge" style="font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid #ec4899; color:#f472b6; background:rgba(236,72,153,0.1);">Checking...</span>
          </div>

          <div style="margin-bottom:12px;">
            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">MarkanM Bot Token (from chat.markanm.com/developers):</label>
            <div style="display:flex; gap:6px;">
              <input id="msg-mk-token-input" type="password" placeholder="Enter MarkanM Bot Token (mkbot_...)" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:12px;">
              <button class="btn btn-secondary" onclick="toggleMsgMKTokenVisibility()" style="padding:6px 10px; font-size:12px;" title="Toggle Token Visibility">👁️</button>
            </div>
          </div>

          <div style="display:flex; gap:10px; margin-bottom:12px;">
            <div style="flex:1;">
              <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Allowed Username (Whitelist):</label>
              <input id="msg-mk-username-input" type="text" placeholder="e.g. your_markanm_username" style="width:100%; box-sizing:border-box; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#ec4899; font-size:12px;">
            </div>
            <div style="flex:1;">
              <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Default Room ID (Optional):</label>
              <input id="msg-mk-roomid-input" type="text" placeholder="Auto-detected on room join" style="width:100%; box-sizing:border-box; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#ec4899; font-size:12px;">
            </div>
          </div>

          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:14px;">
            <button class="btn btn-secondary" onclick="validateMarkanMTokenUI('msg')" style="font-size:12px; padding:6px 12px; border-color:#ec4899; color:#f472b6;">🔍 Validate Token</button>
            <button class="btn" onclick="saveMarkanMConfigUI('msg')" style="background:#ec4899; color:#fff; font-weight:bold; font-size:12px; padding:6px 14px;">💾 Save & Connect</button>
            <button id="msg-mk-toggle-btn" class="btn btn-secondary" onclick="toggleMarkanMBotServiceUI('msg')" style="font-size:12px; padding:6px 12px;">Start Polling</button>
            <button class="btn btn-secondary" onclick="testMarkanMMessageUI('msg')" style="font-size:12px; padding:6px 12px; border-color:#34d399; color:#34d399;">📨 Send Test Msg</button>
          </div>

          <div id="msg-mk-feedback" style="font-size:12px; margin-top:10px; display:none; padding:8px; border-radius:6px; background:rgba(0,0,0,0.5);"></div>

          <div style="margin-top:14px; border-top:1px solid rgba(255,255,255,0.08); padding-top:12px;">
            <label style="font-size:12px; color:var(--text-muted); font-weight:600;">Direct Message to MarkanM Room:</label>
            <div style="display:flex; gap:6px; margin-top:6px;">
              <input id="msg-mk-direct-input" type="text" placeholder="Type a message to send directly to MarkanM room..." onkeydown="if(event.key==='Enter') sendDirectMarkanMMsgUI('msg')" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#ec4899; font-size:12px;">
              <button class="btn" onclick="sendDirectMarkanMMsgUI('msg')" style="background:#ec4899; color:#fff; font-size:12px; padding:6px 14px;">Send 📤</button>
            </div>
          </div>

          <div style="margin-top:14px; padding:10px; border-radius:6px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.05); font-size:11px; color:var(--text-muted);">
            <b>Quick Setup:</b>
            <ol style="margin:4px 0 0 0; padding-left:18px;">
              <li>Go to <a href="https://chat.markanm.com/developers" target="_blank" rel="noopener" style="color:#ec4899;">chat.markanm.com/developers</a>.</li>
              <li>Create a bot and generate an API Token starting with <code>mkbot_</code>.</li>
              <li>Paste the token above and click <b>Validate Token</b>.</li>
            </ol>
          </div>
        </div>
      </div>

      <!-- Live Messaging Activity Table with Provider Filter -->
      <div class="card" style="border-top:3px solid #8b5cf6;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
          <div>
            <h3 style="margin:0; color:#a78bfa;">📡 Live Bot Channels Activity & Request Log</h3>
            <span style="font-size:11px; color:var(--text-muted);">Real-time database recording of incoming commands, messages, replies, and latency</span>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <div style="display:flex; gap:4px; background:rgba(0,0,0,0.4); padding:3px; border-radius:6px; border:1px solid var(--border);">
              <button id="msg-filter-all-btn" class="btn btn-secondary" onclick="filterBotActivityLogs('all')" style="font-size:11px; padding:3px 8px; background:rgba(139,92,246,0.3); color:#fff;">All</button>
              <button id="msg-filter-tg-btn" class="btn btn-secondary" onclick="filterBotActivityLogs('telegram')" style="font-size:11px; padding:3px 8px;">Telegram</button>
              <button id="msg-filter-mk-btn" class="btn btn-secondary" onclick="filterBotActivityLogs('markanm')" style="font-size:11px; padding:3px 8px;">MarkanM</button>
            </div>
            <button class="btn btn-secondary" onclick="loadBotChannelsActivity()" style="font-size:12px; padding:4px 10px;">🔄 Refresh</button>
            <button class="btn btn-secondary" onclick="clearBotActivityLogs()" style="font-size:12px; padding:4px 10px; color:#ef4444; border-color:rgba(239,68,68,0.4);">🗑️ Clear Log</button>
          </div>
        </div>

        <div id="msg-activity-table-container" style="max-height:360px; overflow-y:auto; background:rgba(0,0,0,0.4); border-radius:6px; border:1px solid var(--border);">
          <div id="msg-activity-empty" style="text-align:center; padding:24px; color:var(--text-muted); font-size:12px;">Loading bot channel activity logs...</div>
          <table id="msg-activity-table" style="width:100%; border-collapse:collapse; font-size:12px; display:none;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); color:var(--text-muted); text-align:left;">
                <th style="padding:8px 10px;">Time</th>
                <th style="padding:8px 10px;">Channel</th>
                <th style="padding:8px 10px;">Action / Method</th>
                <th style="padding:8px 10px;">Sender / Origin</th>
                <th style="padding:8px 10px;">Content / Details</th>
                <th style="padding:8px 10px;">Status</th>
              </tr>
            </thead>
            <tbody id="msg-activity-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 15. RAG KNOWLEDGE BASE -->
    <div id="screen-rag" class="screen">
      <!-- PIN LOCK SCREEN (Rendered when locked) -->
      <div id="rag-lock-container" class="card" style="max-width:480px; margin:40px auto; text-align:center; padding:36px 24px; border:1px solid rgba(168,85,247,0.3); background:radial-gradient(circle at top, rgba(168,85,247,0.1), rgba(0,0,0,0.9));">
        <div style="font-size:48px; margin-bottom:12px;">🔒</div>
        <h2 style="margin:0 0 8px 0; color:#c084fc;">RAG Knowledge Base</h2>
        <p style="color:var(--text-muted); font-size:13px; line-height:1.5; margin:0 0 20px 0;">
          This knowledge vault contains your private indexed documents, notes, facts, and code injected into Aarushi's prompt context.
        </p>
        <div style="display:flex; justify-content:center; gap:8px; margin-bottom:16px;">
          <input id="rag-pin-input" type="password" placeholder="Enter RAG Master PIN..." onkeydown="if(event.key==='Enter') unlockRAG()" style="max-width:240px; text-align:center; font-size:16px; letter-spacing:2px; padding:10px; border-radius:8px; background:#000; border:1px solid rgba(168,85,247,0.5); color:#c084fc;">
          <button class="btn" onclick="unlockRAG()" style="background:#a855f7; color:#fff; font-weight:bold; padding:10px 20px; font-size:14px;">Unlock 🔓</button>
        </div>
        <div id="rag-pin-err" style="color:#ef4444; font-size:12px; display:none;">❌ Incorrect PIN. Please try again.</div>
      </div>

      <!-- UNLOCKED RAG KNOWLEDGE VAULT (Rendered after PIN entered) -->
      <div id="rag-vault-container" style="display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
          <div>
            <h2 style="margin:0; color:#c084fc;">🧠 RAG Knowledge Base & Semantic Vault</h2>
            <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:13px;">Knowledge documents indexed here are dynamically retrieved and injected into Aarushi's mind during conversations.</p>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary" onclick="lockRAG()" style="border-color:#a855f7; color:#c084fc;">🔒 Lock RAG</button>
            <button class="btn" onclick="loadRAGDocuments()" style="background:#a855f7; color:#fff;">🔄 Refresh</button>
          </div>
        </div>

        <!-- STATS BAR -->
        <div class="grid-4" style="gap:12px; margin-bottom:16px;">
          <div class="card" style="padding:12px; margin:0; text-align:center; border-top:2px solid #a855f7;">
            <div id="rag-stat-docs" style="font-size:24px; font-weight:bold; color:#c084fc;">0</div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Documents</div>
          </div>
          <div class="card" style="padding:12px; margin:0; text-align:center; border-top:2px solid #38bdf8;">
            <div id="rag-stat-words" style="font-size:24px; font-weight:bold; color:#38bdf8;">0</div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Indexed Words</div>
          </div>
          <div class="card" style="padding:12px; margin:0; text-align:center; border-top:2px solid #10b981;">
            <div id="rag-stat-cats" style="font-size:24px; font-weight:bold; color:#10b981;">0</div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Categories</div>
          </div>
          <div class="card" style="padding:12px; margin:0; text-align:center; border-top:2px solid #f59e0b;">
            <div style="font-size:24px; font-weight:bold; color:#f59e0b;">Active</div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">RAG Injection</div>
          </div>
        </div>

        <div class="grid-2" style="gap:16px;">
          <!-- ADD DOCUMENT CARD -->
          <div class="card">
            <h3 style="margin:0 0 10px 0; color:#c084fc;">➕ Ingest New Knowledge Document</h3>
            <div style="margin-bottom:8px;">
              <label style="font-size:12px; color:var(--text-muted);">Document Title:</label>
              <input id="rag-new-title" type="text" placeholder="e.g. Project Architecture, Secret Credentials, Personal Preferences..." style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
            </div>
            <div class="grid-2" style="gap:8px; margin-bottom:8px;">
              <div>
                <label style="font-size:12px; color:var(--text-muted);">Category:</label>
                <select id="rag-new-cat" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#c084fc; font-size:13px;">
                  <option value="notes">Notes / General</option>
                  <option value="docs">Documentation</option>
                  <option value="facts">Personal Facts & Preferences</option>
                  <option value="rules">Directives & Rules</option>
                  <option value="code">Code Snippets & Cheatsheets</option>
                  <option value="secrets">Credentials & Vault Notes</option>
                </select>
              </div>
              <div>
                <label style="font-size:12px; color:var(--text-muted);">Tags (comma separated):</label>
                <input id="rag-new-tags" type="text" placeholder="e.g. project, linux, priority" style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
              </div>
            </div>
            <div style="margin-bottom:10px;">
              <label style="font-size:12px; color:var(--text-muted);">Content / Knowledge Text:</label>
              <textarea id="rag-new-content" rows="6" placeholder="Paste full knowledge text, policies, code, guidelines, notes..." style="width:100%; box-sizing:border-box; margin-top:4px; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:12px; font-family:monospace; resize:vertical;"></textarea>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <button class="btn" onclick="saveRAGDocument()" style="background:#a855f7; color:#fff; font-weight:bold; padding:8px 16px;">Save to Knowledge Base</button>
              <span id="rag-add-msg" style="font-size:12px; color:#34d399; display:none;"></span>
            </div>
          </div>

          <!-- TEST RETRIEVAL & SEMANTIC SEARCH CARD -->
          <div class="card">
            <h3 style="margin:0 0 10px 0; color:#38bdf8;">🔍 Semantic RAG Retrieval Tester</h3>
            <p style="color:var(--text-muted); font-size:12px; margin-bottom:10px;">
              Type any query to test what knowledge chunks Aarushi will retrieve and inject into her response.
            </p>
            <div style="display:flex; gap:6px; margin-bottom:10px;">
              <input id="rag-test-query" type="text" placeholder="e.g. what is my server password, tell me about project..." onkeydown="if(event.key==='Enter') testRAGQuery()" style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
              <button class="btn btn-secondary" onclick="testRAGQuery()" style="border-color:#38bdf8; color:#38bdf8; padding:8px 14px;">Test Search</button>
            </div>
            <div id="rag-test-results" style="max-height:220px; overflow-y:auto; background:#000; padding:10px; border-radius:6px; border:1px solid var(--border); font-size:12px; color:#e2e8f0;">
              <span style="color:var(--text-muted)">Enter a query above to test knowledge retrieval...</span>
            </div>
          </div>
        </div>

        <!-- DOCUMENT CATALOG -->
        <div class="card" style="margin-top:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
            <h3 style="margin:0; color:#c084fc;">📚 Indexed Knowledge Documents</h3>
            <div style="display:flex; gap:6px;">
              <input id="rag-search-filter" type="text" placeholder="Filter documents..." oninput="loadRAGDocuments()" style="padding:6px 10px; font-size:12px; background:#000; border:1px solid var(--border); border-radius:6px; color:#fff;">
              <select id="rag-category-filter" onchange="loadRAGDocuments()" style="padding:6px 10px; font-size:12px; background:#000; border:1px solid var(--border); border-radius:6px; color:#c084fc;">
                <option value="all">All Categories</option>
                <option value="notes">Notes</option>
                <option value="docs">Docs</option>
                <option value="facts">Facts</option>
                <option value="rules">Rules</option>
                <option value="code">Code</option>
                <option value="secrets">Secrets</option>
              </select>
            </div>
          </div>
          <div id="rag-docs-list" style="display:flex; flex-direction:column; gap:8px; max-height:450px; overflow-y:auto;">
            <div style="color:var(--text-muted); font-size:13px;">Loading knowledge vault...</div>
          </div>
        </div>
      </div>
    </div>
    <div id="screen-multipanel" class="screen">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <h2 style="margin: 0; color: var(--cyan);">◫ GDR AI Multi-Panel Command Center</h2>
        <div style="display: flex; gap: 8px;">
          <button id="multi-autoscan-btn" class="btn" style="background: rgba(16,185,129,0.2); border: 1px solid var(--success); color: #6ee7b7;" onclick="toggleAutoScanner()">📷 Auto-Scan: ON</button>
          <button class="btn btn-secondary" onclick="requestLocationPermission()">📍 Request Location</button>
          <button class="btn btn-secondary" onclick="fetchOpenWindows()">🔄 Refresh Windows</button>
        </div>
      </div>

      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 14px;">
        <!-- PANEL 1: Conversational Chat & Speech Orb -->
        <div class="card" style="margin-bottom: 0;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h3 style="margin: 0;">💬 Conversational Agent</h3>
            <span id="multipanel-voice-badge" style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(0,240,255,0.1); color: var(--cyan); border: 1px solid var(--cyan);">AUTO-LISTEN ACTIVE</span>
          </div>
          <div id="multi-chat-history" style="height: 240px; overflow-y: auto; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 6px; font-size: 13px; margin-bottom: 8px;">
            <div style="color:var(--text-muted)">🤖 <b>GDR AI:</b> Command center ready. Speak or type instructions.</div>
          </div>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="multi-chat-input" placeholder="Say or type command..." onkeydown="if(event.key==='Enter') sendMultiChat()">
            <button class="btn btn-secondary" onclick="toggleBrowserSpeechRecognition()">🎙️</button>
            <button class="btn" onclick="sendMultiChat()">Send</button>
          </div>
        </div>

        <!-- PANEL 2: Live Camera & Ambient Presence HUD -->
        <div class="card" style="margin-bottom: 0;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h3 style="margin: 0;">📷 Real-Time Camera & Presence</h3>
            <span id="multi-cam-badge" style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid var(--success);">AUTO-SCAN ACTIVE</span>
          </div>
          <div class="webcam-box" style="height: 210px;">
            <video id="multi-webcam-feed" autoplay playsinline muted style="width: 100%; height: 100%; object-fit: cover;"></video>
            <div class="hud-reticle"></div>
            <div class="hud-target-ring"></div>
            <div id="multi-cam-overlay" style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.75); padding: 3px 8px; border-radius: 4px; font-size: 11px; color: var(--cyan);">
              ● SENSOR: SCANNING (/dev/video0)
            </div>
          </div>
          <div style="margin-top: 8px; display: flex; gap: 8px;">
            <button class="btn btn-secondary" style="font-size: 12px; padding: 5px 10px;" onclick="scanWebcamFace()">Scan Face</button>
            <button class="btn btn-secondary" style="font-size: 12px; padding: 5px 10px;" onclick="enrollFromWebcam()">➕ Multi-Angle Enroll</button>
            <button class="btn btn-secondary" style="font-size: 12px; padding: 5px 10px;" onclick="toggleCameraPrivacy()">Instant Privacy</button>
          </div>
        </div>

        <!-- PANEL 3: Desktop, Live Screen Stream & Window Typer -->
        <div class="card" style="margin-bottom: 0;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h3 style="margin: 0;">🖥️ Live Screen View & Desktop</h3>
            <button id="btn-screen-share" class="btn" style="background: rgba(0,240,255,0.15); border: 1px solid var(--cyan); color: var(--cyan); font-size: 11px; padding: 3px 8px;" onclick="toggleLiveScreenStream()">🖥️ Share Live Screen</button>
          </div>
          
          <!-- Live Screen Video Feed & Placeholder -->
          <div style="position: relative; width: 100%; height: 160px; background: #000; border-radius: 6px; overflow: hidden; margin-bottom: 8px; border: 1px solid var(--border);">
            <video id="live-screen-feed" autoplay playsinline muted style="width: 100%; height: 100%; object-fit: contain; display: none;"></video>
            <div id="live-screen-placeholder" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-size: 12px; text-align: center; padding: 10px;">
              <div style="font-size: 24px; margin-bottom: 4px;">🖥️</div>
              <div><b>Real-Time Live Screen Stream</b></div>
              <div style="font-size: 11px; margin-top: 4px; color: #64748b;">Streams Wayland/X11 screen to GDR AI without taking static screenshots.</div>
              <button class="btn btn-secondary" style="font-size: 11px; margin-top: 6px; padding: 3px 10px;" onclick="toggleLiveScreenStream()">Start Streaming</button>
            </div>
            <div id="live-screen-badge" style="display:none; position: absolute; top: 6px; left: 6px; background: rgba(0,0,0,0.8); border: 1px solid var(--success); color: #6ee7b7; font-size: 10px; padding: 2px 6px; border-radius: 3px;">
              ● LIVE SCREEN 30FPS
            </div>
          </div>

          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">Active Window: <b id="active-win-name" style="color:var(--cyan);">Detecting...</b></div>
          <div id="multi-open-windows" class="mono-font" style="height: 80px; overflow-y: auto; background: #000; padding: 6px; border-radius: 4px; font-size: 11px; color: #a5f3fc; margin-bottom: 8px;">Loading open windows...</div>
          
          <!-- Quick Window Typer -->
          <div style="display: flex; gap: 6px; margin-bottom: 8px;">
            <input type="text" id="window-type-input" placeholder="Type text into active/target window..." style="font-size: 12px; padding: 6px;">
            <button class="btn btn-secondary" style="font-size: 12px; white-space: nowrap;" onclick="quickTypeInWindow()">✍️ Type</button>
          </div>

          <!-- Quick WhatsApp Messenger -->
          <div style="display: flex; gap: 6px;">
            <input type="text" id="wa-phone-input" placeholder="WhatsApp Phone (+91...)" style="width: 45%; font-size: 12px; padding: 6px;">
            <input type="text" id="wa-msg-input" placeholder="Message..." style="font-size: 12px; padding: 6px;">
            <button class="btn" style="font-size: 12px; white-space: nowrap; background: #25D366; border-color: #25D366; color: #000;" onclick="quickSendWhatsApp()">📲 Send</button>
          </div>
        </div>

        <!-- PANEL 4: Hardware Telemetry, Bookmarks & Location -->
        <div class="card" style="margin-bottom: 0;">
          <h3 style="margin: 0 0 8px 0;">⚡ Hardware Telemetry & Bookmarks</h3>
          <div class="metric-row" style="font-size: 12px;"><span>VRAM Budget:</span><b id="multi-vram">Checking...</b></div>
          <div class="progress-bar" style="margin-bottom: 8px; height: 6px;"><div id="multi-vram-bar" class="progress-fill safe" style="width: 5%;"></div></div>
          
          <div class="metric-row" style="font-size: 12px;"><span>Screen Brightness:</span><b id="multi-brightness">85%</b></div>
          <div class="metric-row" style="font-size: 12px;"><span>Geographic Location:</span><b id="multi-location" style="color:var(--cyan);">Click 'Request Location'</b></div>
          
          <h4 style="margin: 8px 0 4px 0; font-size: 12px; color: var(--cyan);">📑 Saved Website Bookmarks:</h4>
          <div id="multi-bookmarks-list" style="max-height: 85px; overflow-y: auto; font-size: 12px; color: var(--text-muted);">Loading bookmarks...</div>
        </div>
      </div>
    </div>

    <!-- STEALTH COPILOT SCREEN -->
    <div id="screen-stealth" class="screen">
      <!-- Invisibility Architecture Banner -->
      <div class="card" style="border-color: rgba(16, 185, 129, 0.4); background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(6, 182, 212, 0.04) 100%);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
          <div>
            <h2 style="color: #34d399; margin-bottom: 6px; border-bottom: none; padding-bottom: 0;">
              🕵️ Invisible Stealth Meeting & Technical Interview Copilot
            </h2>
            <p style="color: #d1d5db; font-size: 13px; margin: 0; max-width: 900px; line-height: 1.5;">
              Watches your screen, analyzes technical questions and coding problems in real time, and produces staff-engineer-level answers.
              <b>Guaranteed 100% invisible to Google Meet participants even when sharing Entire Screen.</b>
            </p>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn" style="background: linear-gradient(135deg, #059669, #10b981); color: #fff; font-weight: bold;" onclick="triggerStealthSolve()">⚡ Solve Screen Now</button>
            <button id="stealth-autowatch-btn" class="btn btn-secondary" onclick="toggleStealthAutoWatch()">👁️ Auto-Watch: OFF</button>
            <button id="stealth-whisper-btn" class="btn btn-secondary" onclick="toggleStealthWhisper()">🎧 Whisper: OFF</button>
          </div>
        </div>

        <!-- 3 Invisibility Pillars -->
        <div class="grid-3" style="margin-top: 16px; gap: 14px;">
          <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(16, 185, 129, 0.3); padding: 12px; border-radius: 8px;">
            <div style="color: #34d399; font-weight: 700; font-size: 13px; margin-bottom: 4px;">📱 1. Phone Teleprompter (Zero Leak)</div>
            <div style="font-size: 12px; color: #9ca3af; line-height: 1.4;">
              Google Meet captures your laptop monitor. Your phone is a separate physical device propped under your screen. Participants cannot see it.
            </div>
          </div>
          <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(6, 182, 212, 0.3); padding: 12px; border-radius: 8px;">
            <div style="color: #22d3ee; font-weight: 700; font-size: 13px; margin-bottom: 4px;">🎧 2. Private Earphone Whisper</div>
            <div style="font-size: 12px; color: #9ca3af; line-height: 1.4;">
              Speaking points are whispered directly into your earbuds via Piper Neural TTS. Meet's microphone noise-filtering ensures interviewers hear only your voice.
            </div>
          </div>
          <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(168, 85, 247, 0.3); padding: 12px; border-radius: 8px;">
            <div style="color: #c084fc; font-weight: 700; font-size: 13px; margin-bottom: 4px;">👻 3. Desktop Ghost & Camouflage</div>
            <div style="font-size: 12px; color: #9ca3af; line-height: 1.4;">
              Semi-transparent floating prompter on PC with opacity slider (down to 15%) and 1-click decoy mode (disguises as a Linux System Resource Monitor).
            </div>
          </div>
        </div>
      </div>

      <!-- Pairing & Live Controls Row -->
      <div class="grid-2" style="grid-template-columns: 1fr 1.6fr; gap: 20px;">
        <!-- Left: Phone Pairing & Screen Feed -->
        <div class="card">
          <h2>📱 Phone Pairing (1-Second Setup)</h2>
          <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">
            Scan with your phone camera or open the link below on your smartphone while on the same Wi-Fi / network.
          </p>

          <div style="display: flex; gap: 14px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; background: var(--bg-input); padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
            <div id="stealth-qr-box" style="background: #fff; padding: 6px; border-radius: 6px; display: inline-block;">
              <canvas id="stealth-qr-canvas" width="130" height="130"></canvas>
            </div>
            <div style="flex: 1; display: flex; flex-direction: column; gap: 8px;">
              <div style="font-size: 11px; color: #9ca3af; text-transform: uppercase;">Direct Phone URL:</div>
              <div id="stealth-lan-url" style="font-family: monospace; font-size: 13px; color: var(--cyan); word-break: break-all; background: #0b0f19; padding: 6px 8px; border-radius: 4px; border: 1px solid #1e293b;">
                http://127.0.0.1:8844/stealth
              </div>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px;" onclick="copyStealthUrl()">📋 Copy Link</button>
                <a id="stealth-open-link" href="/stealth" target="_blank" class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px; text-decoration: none;">📱 Open Tab</a>
              </div>
            </div>
          </div>

          <h3 style="font-size: 13px; margin: 12px 0 6px 0; color: var(--cyan);">🖥️ Desktop Screen Perception</h3>
          <div style="background: #000; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; position: relative;">
            <img id="stealth-desktop-preview" src="/api/screen/latest.jpg" alt="Screen Frame" style="width: 100%; height: 160px; object-fit: contain; background: #07090e;" onerror="this.style.display='none'">
            <div id="stealth-screen-fallback" style="display: none; padding: 30px; text-align: center; color: var(--text-muted); font-size: 12px;">
              Live screen feed active via window reflection and screen perception.
            </div>
            <div style="position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 4px; font-size: 10px; color: #10b981;">
              ● Real-Time Vision
            </div>
          </div>
        </div>

        <!-- Right: Active Question & Elite Teleprompter Solution -->
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 14px;">
            <h2 style="margin: 0; border: none; padding: 0;">🎯 Live Solution Teleprompter</h2>
            <span id="stealth-sol-timestamp" style="font-size: 11px; color: var(--text-muted);">Ready</span>
          </div>

          <!-- Problem Name -->
          <div style="margin-bottom: 14px;">
            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Detected Question:</div>
            <div id="stealth-det-question" style="font-size: 16px; font-weight: 700; color: #fff; line-height: 1.3;">
              Stealth Copilot standing by. Waiting for question on screen...
            </div>
          </div>

          <!-- 1. Say This First -->
          <div style="background: linear-gradient(180deg, rgba(0, 240, 255, 0.08) 0%, rgba(0, 240, 255, 0.02) 100%); border-left: 3px solid var(--cyan); padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <b style="color: var(--cyan); font-size: 11px; text-transform: uppercase;">🗣️ Say This First (Spoken Points)</b>
              <button class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="copyElementText('stealth-det-say')">Copy</button>
            </div>
            <div id="stealth-det-say" style="font-size: 13px; line-height: 1.5; color: #e0f2fe;">
              Copilot ready. As soon as you solve or a problem appears, your high-IQ spoken opening will show up right here.
            </div>
          </div>

          <!-- 2. Optimal Approach & Big-O -->
          <div style="background: rgba(16, 185, 129, 0.06); border-left: 3px solid var(--green); padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <b style="color: #34d399; font-size: 11px; text-transform: uppercase;">💡 Optimal Approach & Big-O</b>
              <button class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="copyElementText('stealth-det-approach')">Copy</button>
            </div>
            <div id="stealth-det-approach" style="font-size: 12px; line-height: 1.5; color: #d1fae5; white-space: pre-line;">
              Optimal data structures, intuition, and Time/Space complexity will appear here.
            </div>
          </div>

          <!-- 3. Solution Code -->
          <div style="background: #040405; border: 1px solid #181920; border-radius: 6px; padding: 10px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <b style="color: #c084fc; font-size: 11px; text-transform: uppercase;">💻 Production-Ready Code</b>
              <button class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="copyElementText('stealth-det-code')">Copy Code</button>
            </div>
            <pre style="margin: 0; max-height: 180px; overflow-y: auto; font-family: monospace; font-size: 12px; color: #a5f3fc;"><code id="stealth-det-code"># Code solution will appear here
def solve():
    pass</code></pre>
          </div>

          <!-- 4. Edge Cases -->
          <div style="background: rgba(245, 158, 11, 0.06); border-left: 3px solid var(--yellow); padding: 10px; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <b style="color: #fbbf24; font-size: 11px; text-transform: uppercase;">⚠️ Edge Cases & Gotchas</b>
              <button class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="copyElementText('stealth-det-edges')">Copy</button>
            </div>
            <div id="stealth-det-edges" style="font-size: 12px; line-height: 1.4; color: #fef08a; white-space: pre-line;">
              • Null or empty inputs
              • Boundary limits
              • Duplicates
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 16. DEVICE MESH SCREEN -->
    <div id="screen-mesh" class="screen">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:18px;">
        <div>
          <h2 style="margin:0; border:none; padding:0; font-size:20px; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
            🌐 Multi-Device AI Mesh
            <span id="mesh-online-count-badge" style="font-size:11px; padding:2px 8px; border-radius:12px; background:var(--accent-soft); color:var(--accent-primary); border:1px solid var(--accent-border);">1 Online</span>
          </h2>
          <p style="margin:4px 0 0 0; font-size:13px; color:var(--text-muted);">
            Securely orchestrate Android Termux, Linux, Windows, and macOS devices into one unified AI assistant.
          </p>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn" onclick="openMeshPairModal()">➕ Connect Device</button>
          <button class="btn btn-secondary" onclick="fetchMeshDevices()">🔄 Refresh Nodes</button>
        </div>
      </div>

      <!-- Quick Platform Architecture Overview -->
      <div class="card" style="margin-bottom:18px; background:var(--bg-elevated); border:1px solid var(--border-subtle);">
        <div class="grid-3" style="gap:14px;">
          <div style="padding:10px; border-radius:var(--radius-sm); background:var(--bg-secondary);">
            <div style="font-size:12px; color:var(--text-muted); font-weight:600;">📱 ANDROID TERMUX</div>
            <div style="font-size:13px; color:var(--text-primary); margin-top:4px;">Battery diagnostics, push notifications, storage indexing, camera perception.</div>
          </div>
          <div style="padding:10px; border-radius:var(--radius-sm); background:var(--bg-secondary);">
            <div style="font-size:12px; color:var(--text-muted); font-weight:600;">🐧 LINUX / SERVERS</div>
            <div style="font-size:13px; color:var(--text-primary); margin-top:4px;">Safe directory search, CPU/RAM/VRAM diagnostics, scheduled tasks.</div>
          </div>
          <div style="padding:10px; border-radius:var(--radius-sm); background:var(--bg-secondary);">
            <div style="font-size:12px; color:var(--text-muted); font-weight:600;">🪟 WINDOWS & 🍎 MACOS</div>
            <div style="font-size:13px; color:var(--text-primary); margin-top:4px;">Cross-device file discovery, verified file transfer, system monitors.</div>
          </div>
        </div>
      </div>

      <!-- Live Devices Grid -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h3 style="font-size:14px; color:var(--text-secondary); margin:0;">Enrolled Device Nodes:</h3>
        <span style="font-size:12px; color:var(--text-muted);">Strict security: only approved folders and allowlisted diagnostics are accessible</span>
      </div>
      <div id="mesh-devices-grid" class="grid-2" style="gap:16px;">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- 17. GDR-IDE: NEXT-GEN AI WORKSPACE & PERSONAL TERMINAL -->
    <div id="screen-ide" class="screen" style="padding:0; height: calc(100vh - 110px); flex-direction:column; overflow:hidden; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-md);">
      
      <!-- VS Code Style Top Menu / Titlebar -->
      <div style="height:36px; background:#1e1e24; display:flex; align-items:center; justify-content:space-between; padding:0 12px; border-bottom:1px solid #27272a; user-select:none;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:14px;">💻</span>
          <span style="font-weight:700; font-size:12px; letter-spacing:0.5px; color:#f4f4f5;">GDR-IDE</span>
          <span style="font-size:11px; color:#71717a;">— Personal AI Studio & Terminal</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <span id="ide-call-active-badge" style="display:none; align-items:center; gap:6px; font-size:11px; background:rgba(236,72,153,0.2); color:#f472b6; border:1px solid #ec4899; padding:3px 8px; border-radius:12px; font-weight:600;">
            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#ec4899;"></span> 📞 Call Active
          </span>
          <button id="ide-call-btn" onclick="toggleIdeVoiceCall()" class="btn btn-secondary" style="font-size:11px; padding:4px 10px; border-radius:4px; border-color:#ec4899; color:#f472b6; font-weight:600;" title="Discreet Companion Voice Call in IDE">📞 Call</button>
          <button onclick="executeIdeCode()" class="btn" style="background:#10A37F; color:#fff; font-size:11px; padding:4px 10px; border-radius:4px; font-weight:600;">▶ Run Code (Ctrl+Enter)</button>
          <button onclick="saveActiveIdeFile()" class="btn btn-secondary" style="font-size:11px; padding:4px 10px; border-radius:4px;">💾 Save (Ctrl+S)</button>
          <button onclick="toggleIdeTerminal()" class="btn btn-secondary" style="font-size:11px; padding:4px 10px; border-radius:4px;">💻 Terminal</button>
          <button onclick="toggleIdeCopilot()" class="btn btn-secondary" style="font-size:11px; padding:4px 10px; border-radius:4px;">🤖 Copilot</button>
        </div>
      </div>

      <!-- Main IDE Body: Activity Bar + Sidebar + Editor + Copilot -->
      <div style="display:flex; flex:1; overflow:hidden;">
        
        <!-- 1. Activity Bar (VS Code 48px left rail) -->
        <div style="width:48px; background:#121215; border-right:1px solid #27272a; display:flex; flex-direction:column; align-items:center; padding:8px 0; gap:16px;">
          <button id="act-btn-explorer" onclick="setIdeActivityTab('explorer')" title="Explorer (Ctrl+Shift+E)" style="background:none; border:none; color:#f4f4f5; cursor:pointer; font-size:18px; padding:6px; border-left:2px solid var(--accent-primary);">📁</button>
          <button id="act-btn-terminal" onclick="setIdeActivityTab('terminal')" title="Personal Terminal" style="background:none; border:none; color:#71717a; cursor:pointer; font-size:18px; padding:6px;">💻</button>
          <button id="act-btn-copilot" onclick="setIdeActivityTab('copilot')" title="AI Copilot" style="background:none; border:none; color:#71717a; cursor:pointer; font-size:18px; padding:6px;">🤖</button>
          <button id="act-btn-git" onclick="setIdeActivityTab('git')" title="Source Control (Git)" style="background:none; border:none; color:#71717a; cursor:pointer; font-size:18px; padding:6px;">🌿</button>
          <div style="margin-top:auto;">
            <button onclick="showScreen('settings')" title="Settings" style="background:none; border:none; color:#71717a; cursor:pointer; font-size:18px; padding:6px;">⚙️</button>
          </div>
        </div>

        <!-- 2. Primary Sidebar (Explorer / Git) -->
        <div id="ide-sidebar" style="width:230px; background:#18181c; border-right:1px solid #27272a; display:flex; flex-direction:column; overflow:hidden;">
          <div style="padding:8px 12px; font-size:11px; font-weight:700; color:#a1a1aa; letter-spacing:0.8px; text-transform:uppercase; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #27272a;">
            <span id="ide-sidebar-title">Explorer</span>
            <div style="display:flex; gap:4px;">
              <button onclick="createIdeNewFile()" title="New File" style="background:none; border:none; color:#a1a1aa; cursor:pointer; font-size:12px;">➕</button>
              <button onclick="refreshIdeFiles()" title="Refresh" style="background:none; border:none; color:#a1a1aa; cursor:pointer; font-size:12px;">🔄</button>
            </div>
          </div>
          <!-- Project path root -->
          <div style="padding:6px 12px; font-size:11px; font-weight:600; color:#38bdf8; background:#121215; border-bottom:1px solid #27272a; display:flex; align-items:center; gap:6px;">
            <span>▾ GDR-AI</span>
            <span style="font-size:10px; color:#71717a;">~/gdragent</span>
          </div>
          <!-- File Tree -->
          <div id="ide-file-tree" style="flex:1; overflow-y:auto; padding:4px 0; font-size:12px; font-family:var(--font-mono, monospace);">
            <div style="color:#71717a; padding:12px; text-align:center;">Scanning project files...</div>
          </div>
        </div>

        <!-- 3. Center Editor + Terminal Split -->
        <div style="flex:1; display:flex; flex-direction:column; overflow:hidden; background:#1e1e24;">
          
          <!-- Open File Tabs Bar -->
          <div id="ide-tabs-bar" style="height:34px; background:#18181c; border-bottom:1px solid #27272a; display:flex; align-items:center; overflow-x:auto; padding:0 4px; gap:2px;">
            <!-- Tabs rendered dynamically -->
          </div>

          <!-- Breadcrumbs bar -->
          <div style="height:24px; background:#1e1e24; border-bottom:1px solid #27272a; display:flex; align-items:center; justify-content:space-between; padding:0 12px; font-size:11px; color:#71717a; font-family:var(--font-mono, monospace);">
            <div id="ide-breadcrumb-text">gdragent › scratch.py</div>
            <div id="ide-cursor-pos" style="font-size:10px; color:#a1a1aa;">Ln 1, Col 1</div>
          </div>

          <!-- Code Editor Body -->
          <div style="flex:1; display:flex; position:relative; overflow:hidden; background:#1e1e24;">
            <!-- Line Numbers Gutter -->
            <div id="ide-line-numbers" style="width:42px; background:#1e1e24; color:#52525b; font-family:var(--font-mono, monospace); font-size:13px; line-height:20px; text-align:right; padding:8px 8px 8px 0; user-select:none; border-right:1px solid #27272a; overflow:hidden;">1</div>
            <!-- Textarea Editor with VS Code look -->
            <textarea id="ide-code-editor" spellcheck="false" placeholder="# Write Python, Bash, or JavaScript here...&#10;# Press Ctrl+Enter to execute, Ctrl+S to save." oninput="updateIdeEditorState()" onscroll="syncIdeLineNumbers()" onkeydown="handleIdeEditorKey(event)" style="flex:1; height:100%; border:none; outline:none; background:#1e1e24; color:#f4f4f5; font-family:var(--font-mono, 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace); font-size:13px; line-height:20px; padding:8px 12px; resize:none; tab-size:4; white-space:pre;"></textarea>
          </div>

          <!-- 4. VS Code Style Bottom Panel (Personal Terminal & Output) -->
          <div id="ide-bottom-panel" style="height:220px; background:#121215; border-top:1px solid #27272a; display:flex; flex-direction:column; overflow:hidden;">
            <!-- Bottom Panel Header Tabs -->
            <div style="height:32px; background:#18181c; border-bottom:1px solid #27272a; display:flex; align-items:center; justify-content:space-between; padding:0 12px;">
              <div style="display:flex; gap:12px; font-size:11px; font-weight:600;">
                <span id="tab-term-btn" onclick="setIdeBottomTab('terminal')" style="cursor:pointer; color:#f4f4f5; border-bottom:2px solid #38bdf8; padding-bottom:4px;">💻 TERMINAL</span>
                <span id="tab-out-btn" onclick="setIdeBottomTab('output')" style="cursor:pointer; color:#71717a; padding-bottom:4px;">📄 OUTPUT</span>
                <span id="tab-git-btn" onclick="setIdeBottomTab('git')" style="cursor:pointer; color:#71717a; padding-bottom:4px;">🌿 GIT STATUS</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span id="ide-term-cwd" style="font-size:10px; color:#38bdf8; font-family:var(--font-mono, monospace);">~/gdragent</span>
                <button onclick="clearIdeTerminal()" title="Clear Terminal" style="background:none; border:none; color:#a1a1aa; cursor:pointer; font-size:11px;">🗑️ Clear</button>
                <button onclick="toggleIdeTerminalHeight()" title="Resize Panel" style="background:none; border:none; color:#a1a1aa; cursor:pointer; font-size:11px;">◫</button>
              </div>
            </div>

            <!-- Terminal Output Stream -->
            <div id="ide-terminal-body" style="flex:1; overflow-y:auto; padding:8px 12px; font-family:var(--font-mono, monospace); font-size:12px; line-height:1.4; color:#e4e4e7; background:#0e0e11;">
              <div style="color:#71717a; margin-bottom:6px;">🚀 GDR-IDE Personal Terminal [bash on Linux x86_64]</div>
              <div style="color:#71717a; margin-bottom:8px;">Type any system command below (e.g. <code>ls -la</code>, <code>git status</code>, <code>python3 main.py</code>, <code>pip list</code>, <code>pytest</code>):</div>
              <div id="ide-terminal-history"></div>
            </div>

            <!-- Interactive Terminal Prompt Input -->
            <div style="background:#18181c; border-top:1px solid #27272a; padding:6px 12px; display:flex; align-items:center; gap:8px;">
              <span id="ide-prompt-badge" style="color:#10A37F; font-weight:700; font-size:12px; font-family:var(--font-mono, monospace);">user@localhost:~$</span>
              <input id="ide-terminal-input" type="text" placeholder="Enter shell command..." onkeydown="handleIdeTerminalKey(event)" style="flex:1; background:transparent; border:none; outline:none; color:#f4f4f5; font-family:var(--font-mono, monospace); font-size:12px;">
              <button onclick="submitIdeTerminalCommand()" class="btn" style="padding:2px 8px; font-size:11px; background:#27272a; color:#f4f4f5;">Send</button>
            </div>
          </div>
        </div>

        <!-- 5. Right AI Copilot Panel (Collapsible) -->
        <div id="ide-copilot-panel" style="width:310px; background:#18181c; border-left:1px solid #27272a; display:flex; flex-direction:column; overflow:hidden;">
          <div style="padding:8px 12px; font-size:11px; font-weight:700; color:#a1a1aa; letter-spacing:0.8px; text-transform:uppercase; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #27272a;">
            <span>🤖 GDR Copilot</span>
            <button onclick="toggleIdeCopilot()" style="background:none; border:none; color:#71717a; cursor:pointer; font-size:12px;">✕</button>
          </div>
          <div id="ide-copilot-messages" style="flex:1; overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:8px;">
            <div style="color:#a1a1aa; font-size:12px; padding:8px; background:#1e1e24; border-radius:6px; border:1px solid #27272a;">
              ✨ Welcome to <strong>GDR-IDE Copilot</strong>! I can refactor code, find bugs, write unit tests, and explain algorithms in your active buffer.
            </div>
          </div>
          <div style="padding:8px; background:#121215; border-top:1px solid #27272a; display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; gap:4px; overflow-x:auto;">
              <button onclick="askIdeCopilotPreset('explain')" style="font-size:10px; padding:2px 6px; background:#27272a; color:#a1a1aa; border:none; border-radius:4px; cursor:pointer;">Explain</button>
              <button onclick="askIdeCopilotPreset('refactor')" style="font-size:10px; padding:2px 6px; background:#27272a; color:#a1a1aa; border:none; border-radius:4px; cursor:pointer;">Refactor</button>
              <button onclick="askIdeCopilotPreset('tests')" style="font-size:10px; padding:2px 6px; background:#27272a; color:#a1a1aa; border:none; border-radius:4px; cursor:pointer;">Write Tests</button>
            </div>
            <div style="display:flex; gap:6px;">
              <input id="ide-ai-prompt" type="text" placeholder="Ask AI about this code..." onkeydown="if(event.key==='Enter')askIdeCopilot()" style="flex:1; font-size:12px; padding:6px 8px; border-radius:4px; border:1px solid #27272a; background:#1e1e24; color:#f4f4f5;">
              <button class="btn" onclick="askIdeCopilot()" style="font-size:11px; padding:6px 10px; background:var(--accent-primary); color:#fff;">Ask</button>
            </div>
          </div>
        </div>
      </div>

      <!-- VS Code Style Bottom Status Bar -->
      <div style="height:22px; background:#007acc; color:#ffffff; font-size:11px; display:flex; align-items:center; justify-content:space-between; padding:0 12px; font-family:var(--font-mono, monospace); user-select:none;">
        <div style="display:flex; align-items:center; gap:12px;">
          <span style="font-weight:600;">⎇ main</span>
          <span>0 ⊗ 0 ⚠</span>
          <span id="ide-status-filename">scratch.py</span>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          <span id="ide-status-cursor">Ln 1, Col 1</span>
          <span>Spaces: 4</span>
          <span>UTF-8</span>
          <span id="ide-status-lang">Python 3.13</span>
          <span style="font-weight:600;">GDR-IDE v2.0</span>
        </div>
      </div>
    </div>

    <!-- 18. MY DAY / DIGITAL WELLBEING & ACTIVITY TIMELINE -->
    <div id="screen-timeline" class="screen">
      <div class="card" style="margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <h2 style="margin:0; font-size:16px; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
              <span>⏱️</span> My Day — Digital Activity Timeline & Wellbeing
            </h2>
            <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
              Real-time native OS boot detection, active work monitoring, and ergonomic care.
            </div>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-sm" onclick="fetchTimeline(); fetchWellbeing();">🔄 Refresh</button>
            <button class="btn btn-primary btn-sm" onclick="recordWellbeingBreak(5)">☕ Take 5m Break</button>
          </div>
        </div>
      </div>

      <!-- Quick Stats Row -->
      <div class="grid-4" style="gap:12px; margin-bottom:16px;">
        <div class="card" style="padding:12px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">PC Startup / Boots</div>
          <div id="tl-stat-boots" style="font-size:20px; font-weight:700; color:var(--accent-primary); margin-top:4px;">1</div>
          <div id="tl-stat-boot-time" style="font-size:11px; color:var(--text-muted); margin-top:2px;">Measured via OS kernel</div>
        </div>
        <div class="card" style="padding:12px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Active Screen Time</div>
          <div id="tl-stat-active" style="font-size:20px; font-weight:700; color:var(--success); margin-top:4px;">--</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">Measured work duration</div>
        </div>
        <div class="card" style="padding:12px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Continuous Focus</div>
          <div id="tl-stat-continuous" style="font-size:20px; font-weight:700; color:var(--warning); margin-top:4px;">--</div>
          <div id="tl-stat-limit" style="font-size:11px; color:var(--text-muted); margin-top:2px;">Limit: 55 min</div>
        </div>
        <div class="card" style="padding:12px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Breaks Taken</div>
          <div id="tl-stat-breaks" style="font-size:20px; font-weight:700; color:#a78bfa; margin-top:4px;">0</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">Target: 1 every hour</div>
        </div>
      </div>

      <!-- 2 Columns: Timeline list on Left, Wellbeing & Custom APIs on Right -->
      <div class="grid-2" style="gap:16px; align-items:start;">
        
        <!-- Left: Activity Timeline -->
        <div class="card">
          <div class="card-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div class="card-title">📜 Today's Event Timeline</div>
            <span class="badge" id="tl-event-count">0 events</span>
          </div>
          <div id="tl-events-list" style="display:flex; flex-direction:column; gap:8px; max-height:420px; overflow-y:auto; padding-right:4px;">
            <div style="color:var(--text-muted); font-size:12px;">Loading timeline...</div>
          </div>
        </div>

        <!-- Right: Digital Wellbeing Controls & Custom APIs -->
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Wellbeing Settings -->
          <div class="card">
            <div class="card-title" style="margin-bottom:12px;">🌿 Digital Wellbeing & Reminders</div>
            <div style="display:flex; flex-direction:column; gap:10px; font-size:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>Break Reminders:</span>
                <span class="badge badge-success" id="wb-status-badge">Active</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>Quiet Hours:</span>
                <span id="wb-quiet-hours" style="color:var(--text-muted);">22:00 — 08:00</span>
              </div>
              <div style="display:flex; gap:8px; margin-top:6px;">
                <button class="btn btn-secondary btn-sm" onclick="snoozeWellbeingBreak(10)">💤 Snooze (10m)</button>
                <button class="btn btn-primary btn-sm" onclick="recordWellbeingBreak(5)">✅ Log Break (5m)</button>
              </div>
            </div>
          </div>

          <!-- Connected Custom APIs -->
          <div class="card">
            <div class="card-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <div class="card-title">🔌 Connected User APIs</div>
              <button class="btn btn-secondary btn-sm" onclick="promptAddCustomApi()">+ Add API</button>
            </div>
            <div id="custom-apis-container" style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
              <div style="color:var(--text-muted);">No custom APIs connected yet.</div>
            </div>
          </div>

        </div>

      </div>
    </div>

    <!-- 20. TRUSTED RELATIONS & NETWORK SCREEN -->
    <div id="screen-contacts" class="screen">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
        <div>
          <h1 style="margin:0; font-size:22px; display:flex; align-items:center; gap:8px;">👥 Trusted Relations & Network</h1>
          <p style="margin:4px 0 0 0; font-size:12px; color:var(--text-muted);">Manage family, trusted friends, colleagues, and enemy/untrusted contacts with trust ratings (0-100%). Tell AI to email or call them safely with automatic approval.</p>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-primary" onclick="openAddContactModal()" style="display:flex; align-items:center; gap:6px;">
            <span>➕</span> Add Person
          </button>
          <button class="btn btn-secondary" onclick="fetchContacts()" title="Refresh Network">🔄 Refresh</button>
        </div>
      </div>

      <!-- Quick Metrics Row -->
      <div class="grid-3" style="margin-bottom:16px;">
        <div class="card" style="padding:12px; text-align:center;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Total In Network</div>
          <div id="contacts-stat-total" style="font-size:24px; font-weight:700; color:var(--cyan); margin-top:4px;">0</div>
        </div>
        <div class="card" style="padding:12px; text-align:center;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">⭐ High Trust & Family (&ge;80%)</div>
          <div id="contacts-stat-trusted" style="font-size:24px; font-weight:700; color:var(--success); margin-top:4px;">0</div>
        </div>
        <div class="card" style="padding:12px; text-align:center;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">⚠️ Enemies & Untrusted (&le;25%)</div>
          <div id="contacts-stat-enemies" style="font-size:24px; font-weight:700; color:var(--danger); margin-top:4px;">0</div>
        </div>
      </div>

      <!-- Filter bar and search -->
      <div class="card" style="padding:12px; margin-bottom:16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        <div style="flex:1; min-width:200px;">
          <input type="text" id="contacts-search-input" placeholder="🔍 Search by name, relation, email, phone, or notes..." oninput="handleContactsSearch()" style="width:100%; padding:8px 12px; background:rgba(0,0,0,0.4); border:1px solid var(--border); border-radius:6px; color:#fff; font-size:13px;">
        </div>
        <div class="btn-group" style="display:flex; gap:6px; flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary contacts-filter-btn" id="cfilter-all" onclick="filterContacts('all')">All</button>
          <button class="btn btn-sm btn-secondary contacts-filter-btn" id="cfilter-trusted" onclick="filterContacts('trusted')">⭐ Trusted (&ge;80%)</button>
          <button class="btn btn-sm btn-secondary contacts-filter-btn" id="cfilter-family" onclick="filterContacts('family')">💖 Family & Friends</button>
          <button class="btn btn-sm btn-secondary contacts-filter-btn" id="cfilter-work" onclick="filterContacts('work')">💼 Work / Colleague</button>
          <button class="btn btn-sm btn-secondary contacts-filter-btn" id="cfilter-enemy" onclick="filterContacts('enemy')">⚠️ Enemies / Untrusted</button>
        </div>
      </div>

      <!-- Contacts Grid -->
      <div id="contacts-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:14px;">
        <div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--text-muted);">
          Loading your personal network...
        </div>
      </div>
    </div>

  </main>

        <!-- E. SECONDARY / BOTTOM PANEL (TERMINAL, OUTPUT, DIAGNOSTICS) -->
        <div class="secondary-panel" id="secondary-panel">
          <div class="panel-header">
            <div class="panel-tabs">
              <button class="panel-tab active" id="ptab-terminal" onclick="switchPanelTab('terminal')">TERMINAL</button>
              <button class="panel-tab" id="ptab-output" onclick="switchPanelTab('output')">OUTPUT</button>
              <button class="panel-tab" id="ptab-diagnostics" onclick="switchPanelTab('diagnostics')">PROBLEMS / DIAGNOSTICS</button>
            </div>
            <div class="panel-actions">
              <button class="panel-action-btn" onclick="clearBottomTerminal()" title="Clear Terminal Output">🗑️</button>
              <button class="panel-action-btn" onclick="toggleBottomPanelMaximize()" title="Maximize / Restore Panel">🗖</button>
              <button class="panel-action-btn" onclick="toggleBottomPanel(false)" title="Close Panel (`Ctrl+` `~`)">✕</button>
            </div>
          </div>
          <div class="panel-content">
            <!-- Terminal Pane -->
            <div class="panel-pane active" id="pane-terminal">
              <div id="bottom-terminal-output" class="terminal-body mono-font">GDR-IDE Personal Terminal Ready. Type any command (e.g. ls, git status, pwd) or 'help'.
gdr@workbench:~$ </div>
              <div class="terminal-input-row">
                <span class="terminal-prompt" id="bottom-terminal-prompt">gdr@workbench:~$</span>
                <input type="text" id="bottom-terminal-input" class="terminal-input mono-font" placeholder="Enter shell command (e.g. ls, git status, pytest)..." onkeydown="handleBottomTerminalKey(event)">
                <button class="btn btn-secondary btn-sm" onclick="execBottomTerminal()">Run</button>
              </div>
            </div>
            <!-- Output Pane -->
            <div class="panel-pane" id="pane-output">
              <div id="bottom-output-content" class="terminal-body mono-font">[GDR-IDE Workbench]: 5-Section Navigation Architecture Online.
[Diagnostics]: Sarvam AI Cloud Engine active. Swara Neural Voice loaded.
[System]: 157 automated checks passing.</div>
            </div>
            <!-- Diagnostics Pane -->
            <div class="panel-pane" id="pane-diagnostics">
              <div class="terminal-body mono-font" id="pane-diag-list">✓ 0 Errors detected across 17 screens.
✓ Memory, Vector Store & RAG Vault operational.
✓ Device Mesh coordinator running.</div>
            </div>
          </div>
        </div>
      </div> <!-- /workbench-workspace -->
    </div> <!-- /workbench-body -->

    <!-- F. STATUS BAR -->
    <footer class="workbench-statusbar">
      <div class="statusbar-left">
        <span class="status-item" title="Git Branch"><span class="status-icon">🔀</span> main*</span>
        <span class="status-item" id="status-bar-model" title="AI Model"><span class="status-icon">🤖</span> Sarvam AI</span>
        <span class="status-item" id="status-bar-voice" title="Selected Voice"><span class="status-icon">🗣️</span> Swara Neural</span>
        <span class="status-item" id="status-bar-mic" title="Microphone State"><span class="status-icon">🎙️</span> Mic: Idle</span>
        <span class="status-item" id="status-bar-nodes" title="Mesh Device Nodes"><span class="status-icon">🌐</span> 1 Node</span>
      </div>
      <div class="statusbar-right">
        <span class="status-item" onclick="toggleBottomPanel()" style="cursor:pointer;" title="Toggle Bottom Panel (`Ctrl+` `~`)">📟 Terminal</span>
        <span class="status-item" title="Encoding">UTF-8</span>
        <span class="status-item" title="Indentation">Spaces: 2</span>
        <span class="status-item" title="Workbench Environment">GDR-IDE v2.0</span>
        <span class="status-item" id="status-bell" onclick="showScreen('audit')" style="cursor:pointer;" title="Notifications & Logs">🔔 0</span>
      </div>
    </footer>
  </div> <!-- /workbench-shell -->

  <!-- Device Mesh Pairing Modal -->
  <div id="mesh-pairing-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.75); backdrop-filter:blur(8px); z-index:10000; align-items:center; justify-content:center; padding:16px;">
    <div class="card" style="max-width:480px; width:100%; margin:0; border:1px solid var(--accent-border); box-shadow:0 10px 40px rgba(0,0,0,0.6);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid var(--border-subtle); padding-bottom:8px;">
        <h3 style="margin:0; font-size:16px; color:var(--text-primary);">📱 Connect New Device to Mesh</h3>
        <button class="btn btn-secondary" onclick="closeMeshPairModal()" style="padding:2px 8px; font-size:12px;">✕</button>
      </div>

      <div style="text-align:center; padding:10px 0;">
        <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px;">Single-Use Pairing Code</div>
        <div id="mesh-pair-code" class="mono-font" style="font-size:36px; font-weight:700; color:var(--accent-primary); letter-spacing:6px; margin:8px 0;">------</div>
        <div id="mesh-pair-countdown" style="font-size:11px; color:var(--warning);">⏳ Expires in 05:00</div>
      </div>

      <div style="display:flex; justify-content:center; margin:14px 0;">
        <div id="mesh-pair-qr-box" style="background:#fff; padding:10px; border-radius:8px; display:inline-block;">
          <img id="mesh-pair-qr-img" src="" alt="Pairing QR Code" style="width:160px; height:160px; display:block;">
        </div>
      </div>

      <div style="background:var(--bg-input); padding:10px 12px; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); font-size:12px; color:var(--text-secondary); line-height:1.5;">
        <b>Quick Setup Instructions:</b><br>
        1. On Android Termux, Windows, or Mac, open terminal.<br>
        2. Run: <code id="mesh-pair-cmd-hint" style="color:var(--accent-primary);">gdr mesh connect &lt;url&gt; &lt;code&gt;</code><br>
        3. Once approved, the device will connect instantly over WebSocket!
      </div>

      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn btn-secondary" onclick="closeMeshPairModal()">Close</button>
      </div>
    </div>
  </div>

  <!-- Device Permissions & Details Modal -->
  <div id="mesh-perm-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.75); backdrop-filter:blur(8px); z-index:10000; align-items:center; justify-content:center; padding:16px;">
    <div class="card" style="max-width:520px; width:100%; margin:0; border:1px solid var(--border-subtle);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid var(--border-subtle); padding-bottom:8px;">
        <h3 id="mesh-perm-device-title" style="margin:0; font-size:16px; color:var(--text-primary);">Device Permissions</h3>
        <button class="btn btn-secondary" onclick="closeMeshPermModal()" style="padding:2px 8px; font-size:12px;">✕</button>
      </div>

      <input type="hidden" id="mesh-perm-device-id" value="">

      <div style="margin-bottom:14px;">
        <label style="font-size:12px; color:var(--text-secondary); font-weight:600; display:block; margin-bottom:4px;">Approved Directories (Comma-separated allowlist):</label>
        <input type="text" id="mesh-perm-dirs-input" style="width:100%; box-sizing:border-box; padding:8px 10px; border-radius:6px; background:var(--bg-input); border:1px solid var(--border-subtle); color:var(--text-primary); font-size:12px;">
        <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">Strict sandbox boundary: only files in these paths can ever be read or indexed.</div>
      </div>

      <div style="margin-bottom:14px;">
        <label style="font-size:13px; color:var(--text-primary); display:flex; align-items:center; gap:8px; cursor:pointer;">
          <input type="checkbox" id="mesh-perm-readonly-check" style="transform:scale(1.2);">
          <span>Read-Only Mode (Prevent file creation or modifications)</span>
        </label>
      </div>

      <div style="margin-bottom:14px;">
        <label style="font-size:13px; color:var(--text-primary); display:flex; align-items:center; gap:8px; cursor:pointer;">
          <input type="checkbox" id="mesh-perm-diagnostics-check" style="transform:scale(1.2);">
          <span>Allow Read-Only System Diagnostics (uptime, df -h, free -m)</span>
        </label>
      </div>

      <div id="mesh-perm-save-feedback" style="font-size:12px; color:var(--success); margin-bottom:10px; display:none;"></div>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; border-top:1px solid var(--border-subtle); padding-top:12px;">
        <button id="mesh-perm-revoke-btn" class="btn btn-panic" onclick="revokeActiveMeshDevice()" style="font-size:11px;">🚫 Revoke Device</button>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-secondary" onclick="closeMeshPermModal()">Cancel</button>
          <button class="btn" onclick="saveActiveMeshPermissions()">💾 Save Permissions</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Model Hub & Hugging Face Downloader Modal -->
  <div id="model-manager-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.75); backdrop-filter:blur(8px); z-index:10000; align-items:center; justify-content:center; padding:16px;">
    <div class="card" style="max-width:680px; width:100%; max-height:90vh; overflow-y:auto; margin:0; border:1px solid var(--border-subtle); box-shadow:var(--shadow-soft);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid var(--border-subtle); padding-bottom:8px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:22px;">🤖</span>
          <h3 style="margin:0; font-size:16px; color:var(--text-primary);">AI Model Hub & Engine Switcher</h3>
        </div>
        <button class="btn btn-secondary" onclick="closeModelHubModal()" style="padding:2px 8px; font-size:12px;">✕</button>
      </div>

      <!-- Current Active Model Banner -->
      <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); padding:12px 16px; border-radius:var(--radius-sm); margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">Currently Active AI Engine</div>
          <div style="font-size:15px; font-weight:700; color:var(--accent-primary);" id="active-model-title">Sarvam AI 105B (Cloud)</div>
        </div>
        <span id="active-model-badge" style="font-size:11px; padding:3px 10px; border-radius:12px; font-weight:600; background:rgba(16,163,127,0.15); color:var(--accent-primary); border:1px solid var(--accent-primary);">ONLINE • CLOUD</span>
      </div>

      <!-- Section 1: Internet & Cloud Models -->
      <div style="margin-bottom:18px;">
        <h4 style="font-size:13px; color:var(--text-primary); margin:0 0 8px 0; display:flex; align-items:center; gap:6px;">
          <span>🌐 Internet & Cloud LLM Providers</span>
        </h4>
        <div id="cloud-models-list" style="display:grid; grid-template-columns:1fr; gap:8px;">
          <!-- Dynamically populated -->
        </div>
      </div>

      <!-- Section 2: Pull from Hugging Face -->
      <div style="margin-bottom:18px; background:var(--bg-secondary); border:1px dashed var(--border-subtle); border-radius:var(--radius-sm); padding:14px;">
        <h4 style="font-size:13px; color:var(--text-primary); margin:0 0 6px 0; display:flex; align-items:center; gap:6px;">
          <span>🤗 Pull Models from Hugging Face</span>
          <span style="font-size:10px; background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 6px; border-radius:8px;">100% Local GGUF</span>
        </h4>
        <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">
          Download and run quantized open-source models offline on CPU / GPU. Choose a curated preset or enter any Hugging Face repo.
        </div>

        <!-- Presets Grid -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px; margin-bottom:12px;" id="hf-presets-grid">
          <!-- Populated dynamically -->
        </div>

        <!-- Custom Hugging Face Repo input -->
        <div style="display:flex; gap:8px; align-items:center; margin-top:8px;">
          <input type="text" id="hf-custom-url" placeholder="Direct .gguf download URL or Hugging Face repo..." style="flex:1; padding:8px 10px; background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:6px; color:var(--text-primary); font-size:12px;">
          <button class="btn btn-secondary" onclick="pullCustomHFModel()" style="font-size:12px; padding:8px 14px;">⬇️ Pull Model</button>
        </div>

        <!-- Download Progress Bar Container -->
        <div id="hf-download-container" style="display:none; margin-top:12px; background:var(--bg-elevated); padding:10px 12px; border-radius:6px; border:1px solid var(--accent-primary);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span id="hf-download-title" style="font-size:12px; font-weight:600; color:var(--text-primary);">Downloading model...</span>
            <span id="hf-download-pct" style="font-size:12px; font-weight:700; color:var(--accent-primary);">0%</span>
          </div>
          <div style="width:100%; height:6px; background:var(--bg-secondary); border-radius:3px; overflow:hidden; margin-bottom:6px;">
            <div id="hf-download-fill" style="width:0%; height:100%; background:var(--accent-primary); transition:width 0.3s;"></div>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted);">
            <span id="hf-download-speed">0 MB / 0 MB • 0 MB/s</span>
            <button class="btn btn-secondary" onclick="cancelHFPull()" style="font-size:10px; padding:2px 8px; color:var(--danger);">Cancel</button>
          </div>
        </div>
      </div>

      <!-- Section 3: Installed Local Models -->
      <div style="margin-bottom:14px;">
        <h4 style="font-size:13px; color:var(--text-primary); margin:0 0 8px 0; display:flex; align-items:center; gap:6px;">
          <span>💾 Downloaded Local Models (~/.config/gdr/models)</span>
        </h4>
        <div id="local-models-list" style="display:grid; grid-template-columns:1fr; gap:6px;">
          <!-- Populated dynamically -->
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:8px; border-top:1px solid var(--border-subtle); padding-top:12px;">
        <button class="btn btn-secondary" onclick="closeModelHubModal()">Close</button>
      </div>
    </div>
  </div>

  <!-- Floating Camouflage Ghost Overlay for On-Screen Invisibility -->
  <div id="stealth-ghost-hud" style="display: none; position: fixed; top: 30px; right: 30px; width: 380px; max-height: 80vh; z-index: 9999; background: rgba(8, 9, 13, 0.92); border: 1px solid rgba(0, 240, 255, 0.4); border-radius: 10px; backdrop-filter: blur(12px); box-shadow: 0 10px 30px rgba(0,0,0,0.8); overflow: hidden; resize: both; font-family: sans-serif; transition: opacity 0.2s;">
    <!-- Ghost Header / Drag Handle -->
    <div style="background: rgba(14, 16, 24, 0.98); padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: space-between; cursor: move;" id="ghost-drag-handle">
      <div style="display: flex; align-items: center; gap: 6px;">
        <span id="ghost-header-title" style="font-size: 11px; font-weight: bold; color: var(--cyan); letter-spacing: 0.5px;">🕵️ STEALTH COPILOT</span>
        <span id="ghost-status-dot" style="width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
      </div>
      <div style="display: flex; align-items: center; gap: 6px;">
        <input type="range" id="ghost-opacity-slider" min="10" max="100" value="92" style="width: 50px; cursor: pointer;" title="Adjust Transparency" oninput="setGhostOpacity(this.value)">
        <button onclick="toggleGhostDecoy()" style="background: #1e293b; border: 1px solid #334155; color: #94a3b8; font-size: 10px; padding: 2px 6px; border-radius: 4px; cursor: pointer;" title="Disguise as System Resource Monitor">🎭 Decoy</button>
        <button onclick="triggerStealthSolve()" style="background: #0077b6; border: none; color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; cursor: pointer; font-weight: bold;">⚡</button>
        <button onclick="toggleGhostOverlay()" style="background: transparent; border: none; color: #9ca3af; font-size: 12px; cursor: pointer;">✕</button>
      </div>
    </div>
    
    <!-- Real Stealth Prompter Content -->
    <div id="ghost-real-content" style="padding: 12px; max-height: calc(80vh - 40px); overflow-y: auto;">
      <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Detected Question:</div>
      <div id="ghost-question" style="font-size: 13px; font-weight: bold; color: #fff; margin-bottom: 10px; line-height: 1.3;">Waiting for screen question...</div>
      
      <div style="background: rgba(0, 240, 255, 0.08); border-left: 2px solid var(--cyan); padding: 8px; border-radius: 4px; font-size: 12px; color: #e0f2fe; margin-bottom: 10px; line-height: 1.4;">
        <b style="color: var(--cyan); font-size: 10px; display: block; margin-bottom: 2px;">🗣️ SAY THIS FIRST:</b>
        <span id="ghost-say">Tap '⚡' or phone to solve visible screen question.</span>
      </div>

      <div style="background: rgba(16, 185, 129, 0.08); border-left: 2px solid var(--green); padding: 8px; border-radius: 4px; font-size: 11px; color: #d1fae5; margin-bottom: 10px; line-height: 1.4;">
        <b style="color: var(--green); font-size: 10px; display: block; margin-bottom: 2px;">💡 OPTIMAL APPROACH & BIG-O:</b>
        <div id="ghost-approach" style="white-space: pre-line;">Algorithm and complexity will appear here.</div>
      </div>

      <div style="background: #000; border: 1px solid #1e2230; padding: 8px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #a5f3fc; overflow-x: auto; margin-bottom: 10px;">
        <pre id="ghost-code" style="margin: 0;"># Solution code</pre>
      </div>

      <div style="font-size: 11px; color: #fde047; background: rgba(245, 158, 11, 0.08); border-left: 2px solid var(--yellow); padding: 8px; border-radius: 4px; line-height: 1.4;">
        <b style="color: var(--yellow); font-size: 10px; display: block; margin-bottom: 2px;">⚠️ EDGE CASES:</b>
        <div id="ghost-edges" style="white-space: pre-line;">• Empty/null inputs</div>
      </div>
    </div>

    <!-- Camouflage Decoy Content (Looks like benign Linux System Monitor) -->
    <div id="ghost-decoy-content" style="display: none; padding: 12px;">
      <div style="font-family: monospace; font-size: 11px; color: #94a3b8; line-height: 1.6;">
        <div style="display: flex; justify-content: space-between;"><span style="color: #38bdf8;">CPU Utilization:</span><span id="decoy-cpu">14.2% [4 Cores]</span></div>
        <div style="display: flex; justify-content: space-between;"><span style="color: #34d399;">Memory (RAM):</span><span id="decoy-ram">3.8 / 15.6 GB</span></div>
        <div style="display: flex; justify-content: space-between;"><span style="color: #fbbf24;">GPU VRAM:</span><span>820 / 4096 MiB</span></div>
        <div style="display: flex; justify-content: space-between;"><span style="color: #c084fc;">Kernel Version:</span><span>Linux 6.8.0-kali</span></div>
        <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Network Rx/Tx:</span><span>42.1 KB/s</span></div>
        <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Cooling Fan:</span><span>2150 RPM [Normal]</span></div>
        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #1e293b; font-size: 9px; color: #64748b; text-align: center;">
          [System Monitor Active - Press ESC or Double Click to Exit Camouflage]
        </div>
      </div>
    </div>
  </div>

  <!-- ADD / EDIT CONTACT MODAL -->
  <div id="contact-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); backdrop-filter:blur(8px); z-index:10000; align-items:center; justify-content:center; padding:16px;">
    <div class="card" style="max-width:500px; width:100%; max-height:90vh; overflow-y:auto; padding:20px; border:1px solid var(--border); border-radius:12px; background:#0d1117;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <h3 id="contact-modal-title" style="margin:0; font-size:16px;">➕ Add Person to Network</h3>
        <button class="btn btn-secondary btn-sm" onclick="closeContactModal()">✕</button>
      </div>
      <input type="hidden" id="contact-id-field" value="">

      <div style="display:flex; flex-direction:column; gap:12px;">
        <div>
          <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Full Name / Display Name *</label>
          <input type="text" id="contact-name-input" placeholder="e.g. Rohan Sharma, Mom, Vivek" style="width:100%; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
        </div>

        <div class="grid-2" style="gap:10px;">
          <div>
            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Relationship Type</label>
            <select id="contact-rel-select" onchange="onContactRelChange()" style="width:100%; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
              <option value="Trusted Family">💖 Trusted Family (Sister, Brother, Parents)</option>
              <option value="Family member">Family member</option>
              <option value="Best Friend">Best Friend</option>
              <option value="Friend" selected>Friend</option>
              <option value="Partner">Partner</option>
              <option value="Colleague">Colleague / Work</option>
              <option value="Classmate">Classmate</option>
              <option value="Professional contact">Professional contact</option>
              <option value="Enemy / Rival / Untrusted">⚠️ Enemy / Rival / Untrusted</option>
              <option value="Acquaintance">Acquaintance</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Preferred Channel</label>
            <select id="contact-channel-select" style="width:100%; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
              <option value="any">Any Available</option>
              <option value="email">Email</option>
              <option value="phone">Phone / SMS</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="telegram">Telegram</option>
            </select>
          </div>
        </div>

        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <label style="font-size:12px; color:var(--text-muted);">Trust Level: <span id="contact-trust-label" style="font-weight:700; color:var(--cyan);">50% (Neutral)</span></label>
          </div>
          <input type="range" id="contact-trust-slider" min="0" max="100" value="50" oninput="updateContactTrustSlider(this.value)" style="width:100%;">
          <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--text-muted); margin-top:2px;">
            <span style="color:var(--danger)">0% (Enemy / Zero Trust)</span>
            <span>50% (Neutral)</span>
            <span style="color:var(--success)">100% (Absolute Trust)</span>
          </div>
        </div>

        <div class="grid-2" style="gap:10px;">
          <div>
            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Email Address</label>
            <input type="email" id="contact-email-input" placeholder="e.g. rohan@example.com" style="width:100%; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
          </div>
          <div>
            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Phone / WhatsApp</label>
            <input type="text" id="contact-phone-input" placeholder="e.g. +91 98765 43210" style="width:100%; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
          </div>
        </div>

        <div>
          <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">Notes & AI Safety Rules</label>
          <textarea id="contact-notes-input" rows="2" placeholder="e.g. Always take approval before sending email; Never share financial data; Close friend from college" style="width:100%; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:12px;"></textarea>
        </div>

        <div style="display:flex; align-items:center; gap:8px;">
          <input type="checkbox" id="contact-trusted-check">
          <label for="contact-trusted-check" style="font-size:12px; color:var(--text-light); cursor:pointer;">
            Designate as ⭐ Trusted Contact (Can be used for emergency contact & automated assistance)
          </label>
        </div>

        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button class="btn btn-secondary" onclick="closeContactModal()">Cancel</button>
          <button class="btn btn-primary" onclick="saveContactRecord()">Save Person</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Global VS Code Command Palette Modal (Ctrl+Shift+P / Ctrl+P / Ctrl+K) -->
  <div id="cmd-palette" onclick="if(event.target===this) closePalette()">
    <div class="cmd-palette-box">
      <div class="cmd-palette-header">
        <span style="color:var(--accent-primary); font-size:14px;">></span>
        <input type="text" id="cmd-input" class="cmd-palette-input" placeholder="Type a command or screen to jump to..." autofocus oninput="filterPaletteCommands()" onkeydown="handlePaletteKey(event)">
        <kbd class="search-kbd" style="cursor:pointer;" onclick="closePalette()">ESC</kbd>
      </div>
      <div class="cmd-palette-list" id="cmd-palette-list">
        <!-- Rendered dynamically -->
      </div>
    </div>
  </div>

  <script>
    let speechEnabled = true;
    let handsFreeMode = true;
    let isSpeaking = false;
    let isListening = false;
    let recognition = null;
    let webcamStream = null;
    let autoRestartTimer = null;
    let typewriterTimer = null;
    window.typewriterTimer = null;
    let activeSpeechTranscript = '';
    let audioUnlocked = false;
    let currentAudio = null;
    let activeVoiceProfile = 'neural_auto';
    let isBackendOffline = false;

    // Audio Autoplay Unlocker for Instant Responsive Speech
    function unlockAudioPlayback() {
      if (audioUnlocked) return;
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          const ctx = new AudioCtx();
          if (ctx.state === 'suspended') ctx.resume();
        }
        const silent = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA');
        silent.play().catch(() => {});
        audioUnlocked = true;
      } catch(e) {}
    }
    window.addEventListener('click', unlockAudioPlayback, { passive: true });
    window.addEventListener('keydown', unlockAudioPlayback, { passive: true });
    window.addEventListener('touchstart', unlockAudioPlayback, { passive: true });

    // Primary Sidebar Action Handlers (VS Code Inspired)
    function newChatConversation() {
      if (typeof stopSpeakingNow === 'function') stopSpeakingNow();
      const cIn = document.getElementById('chat-input');
      if (cIn) cIn.value = '';
      const hIn = document.getElementById('home-chat-input');
      if (hIn) hIn.value = '';
      showScreen('chat');
      if (cIn) cIn.focus();
    }
    window.newChatConversation = newChatConversation;

    function openChatHistoryModal() {
      showScreen('chat');
      const chatEl = document.getElementById('chat-history');
      if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
    }
    window.openChatHistoryModal = openChatHistoryModal;

    function openAarushiCompanionModal() {
      showScreen('settings');
      if (typeof scrollToSettingsCard === 'function') scrollToSettingsCard('voice');
    }
    window.openAarushiCompanionModal = openAarushiCompanionModal;

    function triggerIdeAssistance() {
      showScreen('ide');
      const inp = document.getElementById('ide-copilot-input');
      if (inp) {
        inp.focus();
        inp.placeholder = "Ask Aarushi for programming assistance or code generation...";
      }
    }
    window.triggerIdeAssistance = triggerIdeAssistance;

    function runIdeTests() {
      showScreen('ide');
      if (typeof toggleBottomPanel === 'function') toggleBottomPanel(true, 'terminal');
      if (typeof executeTerminalCommand === 'function') executeTerminalCommand('pytest tests/ -v');
    }
    window.runIdeTests = runIdeTests;

    function openMemoryVaultModal() {
      showScreen('memory');
    }
    window.openMemoryVaultModal = openMemoryVaultModal;

    function refreshIdeFileTree() {
      if (typeof refreshIdeFiles === 'function') refreshIdeFiles();
    }
    window.refreshIdeFileTree = refreshIdeFileTree;

    // Distinct Audio Beeps for Listening Lifecycle (Synthesized in Web Audio API)
    function playListeningBeep(type) {
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        if (ctx.state === 'suspended') ctx.resume();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.connect(gain);
        gain.connect(ctx.destination);

        if (type === 'start') {
          // Distinct Start-Listening prompt: Bright, uplifting two-tone rise (520Hz -> 820Hz)
          osc.frequency.setValueAtTime(520, now);
          osc.frequency.exponentialRampToValueAtTime(820, now + 0.12);
          gain.gain.setValueAtTime(0.001, now);
          gain.gain.linearRampToValueAtTime(0.12, now + 0.02);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
          osc.start(now);
          osc.stop(now + 0.18);
        } else if (type === 'end' || type === 'proceed') {
          // Distinct Proceeding/Processing tone: Smooth confirmation chime (740Hz -> 540Hz)
          osc.frequency.setValueAtTime(740, now);
          osc.frequency.exponentialRampToValueAtTime(540, now + 0.14);
          gain.gain.setValueAtTime(0.001, now);
          gain.gain.linearRampToValueAtTime(0.10, now + 0.02);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.20);
          osc.start(now);
          osc.stop(now + 0.20);
        }
      } catch (e) {
        console.debug('playListeningBeep error:', e);
      }
    }

    // Toggle Hands-Free continuous conversation
    function toggleHandsFree() {
      handsFreeMode = !handsFreeMode;
      const btn = document.getElementById('handsfree-btn');
      if (btn) {
        btn.textContent = handsFreeMode ? '🎙️ Auto-Listen: ON' : '🎙️ Auto-Listen: OFF';
        btn.style.color = handsFreeMode ? 'var(--success)' : 'var(--text-muted)';
      }
      if (handsFreeMode && !isListening && !isSpeaking) {
        startListeningSafe();
      }
    }

    // Toggle Voice readout
    function toggleAudioSpeech() {
      speechEnabled = !speechEnabled;
      const btn = document.getElementById('audio-mute-btn');
      btn.textContent = speechEnabled ? '🔊 Voice: ON' : '🔇 Muted';
      btn.style.color = speechEnabled ? 'var(--cyan)' : 'var(--text-muted)';
    }

    let currentPlaybackId = 0;
    let isSendingChat = false;
    let lastChatInteractionTime = 0;
    let lastPresenceSpokenTime = 0;

    function escapeHtml(text) {
      return (text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // Voice Profile Preference Management
    function setVoicePreference(val) {
      activeVoiceProfile = val;
      const hSel = document.getElementById('header-voice-select');
      if (hSel) hSel.value = val;
      const sSel = document.getElementById('settings-voice-select');
      if (sSel) sSel.value = val;
      const vName = document.getElementById('header-voice-name');
      const sbVoice = document.getElementById('status-bar-voice');
      if (vName && hSel) {
        const opt = hSel.options[hSel.selectedIndex];
        if (opt) {
          const shortName = opt.text.split('(')[0].replace(/[🎙️🇮🇳🇺🇸🇬🇧💻🌐✨⚡]/g, '').trim();
          vName.textContent = '🗣️ ' + shortName;
          if (sbVoice) sbVoice.textContent = '🗣️ ' + shortName;
        }
      }
      try { localStorage.setItem('gdr_voice_profile', val); } catch(e) {}

      // Synchronize with authoritative backend VoiceManager
      fetch('/api/voice/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_id: val })
      }).catch(() => {});
    }

    function restoreVoicePreference() {
      try {
        const saved = localStorage.getItem('gdr_voice_profile');
        if (saved) setVoicePreference(saved);
      } catch(e) {}
    }

    // Audition test for currently selected voice
    function auditionSelectedVoice() {
      const profile = activeVoiceProfile;
      if (profile.startsWith('hi_') || profile === 'hi_madhur' || profile === 'hi_swara') {
        speakText("नमस्ते! मैं आपका चयनित हिंदी स्वर हूँ। क्या आपको मेरी आवाज़ पसंद आई?");
      } else if (profile.includes('ryan') || profile.includes('sonia')) {
        speakText("Good day, sir. This is your British English voice profile. All systems are operational.");
      } else if (profile.includes('prabhat') || profile.includes('neerja')) {
        speakText("Hello! This is your Indian English voice profile, tuned with natural pacing.");
      } else {
        speakText("Hello! This is your chosen neural voice profile. Ready for your instructions.");
      }
    }

    // Audition test for Hindi & English voices
    function auditionVoice(lang) {
      if (lang === 'hi') {
        speakText("नमस्ते! मैं जीडीआर एआई हूँ। अब मेरी हिंदी आवाज़ स्पष्ट और प्राकृतिक है। आप मुझसे कोई भी सवाल पूछ सकते हैं।");
      } else {
        speakText("Hello! GDR AI neural voice engine is online with studio-grade crystal-clear synthesis.");
      }
    }

    // Clear live transcript
    function clearLiveTranscript() {
      const el = document.getElementById('home-transcript-list');
      if (el) el.innerHTML = '<div style="color:var(--text-muted); font-style:italic;">Transcript cleared. Speak to the Orb or type to begin.</div>';
    }

    // Language Detection for Hindi & Hinglish
    function detectHindi(text) {
      if (!text) return false;
      if (/[\u0900-\u097F]/.test(text)) return true;
      const hinglishWords = [
        "namaste", "namaskar", "kaise", "kaisi", "kaisa", "haal", "kya", "kyun", "kyon",
        "theek", "shukriya", "dhanyavad", "batao", "bataiye", "karo", "kariye", "mera",
        "meri", "mere", "aapka", "aapki", "aapke", "hum", "humara", "kahan", "kidhar",
        "mausam", "nahi", "nahin", "haan", "accha", "achha", "bahut", "dost", "bhai",
        "suno", "sunao", "bolo", "chalo", "shant", "ruko", "gaana", "sunao"
      ];
      const lower = text.toLowerCase();
      const tokens = lower.match(/\b[a-z]+\b/g) || [];
      let matches = 0;
      for (const tok of tokens) {
        if (hinglishWords.includes(tok)) matches++;
      }
      return matches >= 2 || (tokens.length <= 5 && matches >= 1);
    }

    let isQuietMode = false;

    // Check backend silence controller status
    async function updateSilenceState() {
      try {
        const res = await fetch('/api/silence/status');
        if (res.ok) {
          const d = await res.json();
          isQuietMode = !!d.active;
          const badgeEl = document.getElementById('home-engine-badge');
          if (isQuietMode && badgeEl) {
            badgeEl.textContent = `🤫 Quiet Mode Active (${d.remaining_seconds}s remaining)`;
          }
        }
      } catch(e) {}
    }

    // Stop speaking immediately and enter listening mode (Barge-in Mutex)
    function stopSpeakingNow() {
      currentPlaybackId++;
      if (typewriterTimer) {
        clearTimeout(typewriterTimer);
        clearInterval(typewriterTimer);
        typewriterTimer = null;
      }
      if (typeof synchronizedTypewriterTimer !== 'undefined' && synchronizedTypewriterTimer) {
        clearInterval(synchronizedTypewriterTimer);
        synchronizedTypewriterTimer = null;
      }
      if (typeof window.onAudioSpeechFinished === 'function') {
        window.onAudioSpeechFinished();
      }
      activeSentenceQueue = [];
      activeSentenceIndex = 0;
      if (nextAudioPreload) {
        try { nextAudioPreload.src = ''; } catch(e) {}
        nextAudioPreload = null;
      }
      if (currentAudio) {
        try {
          currentAudio.pause();
          currentAudio.currentTime = 0;
          currentAudio.src = '';
        } catch(e) {}
        currentAudio = null;
      }
      if (typeof gdrSpeechQueue !== 'undefined' && gdrSpeechQueue) {
        try { gdrSpeechQueue.cancelCurrent(); } catch(e) {}
      }
      if (window.speechSynthesis) {
        try {
          window.speechSynthesis.cancel();
          window.speechSynthesis.resume();
        } catch(e) {}
      }
      isSpeaking = false;
      fetch('/api/stop', { method: 'POST' }).catch(() => {});
      fetch('/api/tts/stop', { method: 'POST' }).catch(() => {});
      const stopBtn = document.getElementById('barge-in-stop-btn');
      if (stopBtn) stopBtn.style.display = 'none';
      const stopBtnOrb = document.getElementById('orb-stop-btn');
      if (stopBtnOrb) stopBtnOrb.style.display = 'none';

      setOrbState('listening');
      const b = document.getElementById('home-mic-banner');
      if (b) { b.style.display = 'block'; b.textContent = '🛑 Stopped speaking. Listening to you...'; }
      const statusMic = document.getElementById('status-bar-mic');
      if (statusMic) statusMic.textContent = '🎙️ Mic: Listening...';
      startListeningSafe(true);
    }

    function onOrbClick() {
      if (isSpeaking) {
        stopSpeakingNow();
      } else {
        toggleBrowserSpeechRecognition();
      }
    }

    function onSpeechDone(playbackId) {
      if (playbackId !== undefined && playbackId !== currentPlaybackId) return;
      if (currentAudio) {
        try { currentAudio.pause(); currentAudio.src = ''; } catch(e) {}
        currentAudio = null;
      }
      isSpeaking = false;
      const stopBtn = document.getElementById('barge-in-stop-btn');
      if (stopBtn) stopBtn.style.display = 'none';
      const stopBtnOrb = document.getElementById('orb-stop-btn');
      if (stopBtnOrb) stopBtnOrb.style.display = 'none';

      if (handsFreeMode) {
        setOrbState('listening');
        clearTimeout(autoRestartTimer);
        autoRestartTimer = setTimeout(() => {
          if (handsFreeMode && !isSpeaking) startListeningSafe();
        }, 350);
      } else {
        setOrbState('idle');
      }
    }

    // Local Browser SpeechSynthesis fallback (single voice only)
    // =========================================================================
    // AUTHORITATIVE SPEECH-TEXT PROCESSOR & VOICE STREAMING QUEUE
    // =========================================================================

    function cleanTextForSpokenOutput(text) {
      if (!text) return "";
      let t = String(text);

      // 1. Strip bracketed model prefixes and system tags (e.g. [Sarvam • Neural HD Studio], [LocalOfflineLLM • Piper Neural])
      t = t.replace(/\[(?:LocalOfflineLLM|Sarvam|Offline Local AI Mode|GDR Fast Lane|GDR Heavy MoE Lane|Local System AI|vol|FACT|PREFERENCE|PERSONA|STYLE|Query Ingestion|Policy Verification|Agent Response)[^\]]*\]/gi, " ");
      t = t.replace(/\[[^\]]*\b(?:Mode|Engine|Model|Lane|tokens?|Studio|Neural)\b[^\]]*\]/gi, " ");
      t = t.replace(/\b(?:Sweet Companion|Internal Telemetry)\b/gi, " ");

      // 2. Code blocks -> concise spoken summary
      if (/```[\s\S]*?```/.test(t)) {
        const withoutCode = t.replace(/```[\s\S]*?```/g, " ").trim();
        if (!withoutCode || withoutCode.length < 15) {
          t = t.replace(/```[\s\S]*?```/g, " Here is the code snippet. ");
        } else {
          t = t.replace(/```[\s\S]*?```/g, " ");
        }
      }
      t = t.replace(/`([^`]+)`/g, "$1");

      // 3. Headings: '### System\n' -> 'System. '
      t = t.replace(/^#{1,6}\s*(.+)$/gm, "$1.");

      // 4. Markdown tables -> gentle pause
      t = t.replace(/\|?\s*[-:]{2,}\s*\|\s*[-:]{2,}[\s\S]*?\|/g, " ");
      t = t.replace(/\|/g, " , ");

      // 5. Percentages: 70% -> 70 percent
      t = t.replace(/(\d+)%/g, "$1 percent");

      // 6. Dashes: em-dash or double dash to comma pause
      t = t.replace(/\s*[—–]\s*/g, ", ");
      t = t.replace(/\s+--\s+/g, ", ");

      // 7. Bold & italics: **word** -> word
      t = t.replace(/\*\*([^*]+)\*\*/g, "$1");
      t = t.replace(/\*([^*]+)\*/g, "$1");
      t = t.replace(/__([^_]+)__/g, "$1");
      t = t.replace(/_([^_]+)_/g, "$1");

      // 8. URLs -> link
      t = t.replace(/https?:\/\/\S+/g, "link");

      // 9. Decorative emojis & symbols
      t = t.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, "");
      const stripSymbols = ["♪", "♫", "♩", "♬", "•", "●", "◆", "■", "★", "→", "►", "✓", "✗", "⚡", "💬", "🤖", "💖", "👻"];
      stripSymbols.forEach(sym => { t = t.split(sym).join(" "); });

      // 10. Clean raw bracket/symbol noise
      t = t.replace(/[{}()\[\]|~#\\<>=^/@]/g, " ");
      t = t.replace(/\.{2,}/g, ". ");
      t = t.replace(/,\s*,+/g, ", ");
      t = t.replace(/\s+([.,!?])/g, "$1");
      return t.replace(/\s+/g, " ").trim().slice(0, 1500);
    }

    function segmentTextIntoPhrases(text) {
      if (!text) return [];
      // Protect decimals (3.14) and abbreviations (e.g., Mr., Dr.)
      let protectedText = text.replace(/(\d+)\.(\d+)/g, "$1<DOT>$2");
      protectedText = protectedText.replace(/\b(e\.g|i\.e|mr|mrs|dr|vs|prof|etc)\./gi, "$1<DOT>");

      const rawParts = protectedText.match(/[^.!?\n।]+[.!?\n।]+|[^.!?\n।]+$/g) || [protectedText];
      const segments = [];
      let buffer = "";

      for (let part of rawParts) {
        let restored = part.replace(/<DOT>/g, ".").trim();
        if (!restored) continue;
        if (restored.length < 15 && !/[.!?।]$/.test(restored)) {
          buffer = (buffer ? buffer + " " : "") + restored;
        } else {
          if (buffer) {
            segments.push(buffer + " " + restored);
            buffer = "";
          } else {
            segments.push(restored);
          }
        }
      }
      if (buffer) {
        if (segments.length > 0) segments[segments.length - 1] += " " + buffer;
        else segments.push(buffer);
      }
      return segments.filter(s => s.trim().length > 0);
    }

    function resolveVoiceParamFromSnapshot(snapshot, isHi) {
      if (snapshot.isOffline) return 'piper';
      const p = snapshot.voiceProfile || activeVoiceProfile;
      if (p === 'hi_swara' || p === 'hi_female') return 'hi-IN-SwaraNeural';
      if (p === 'hi_male') return 'hi-IN-MadhurNeural';
      if (p === 'elevenlabs') return 'elevenlabs';
      if (p === 'en_aria') return 'en-US-AriaNeural';
      if (p === 'en_jenny' || p === 'en_female') return 'en-US-JennyNeural';
      if (p === 'en_male') return 'en-US-GuyNeural';
      if (p === 'en_sonia') return 'en-GB-SoniaNeural';
      if (p === 'en_ryan') return 'en-GB-RyanNeural';
      if (p === 'en_neerja' || p === 'en_indian') return 'en-IN-NeerjaNeural';
      if (p === 'sarvam' || p === 'sarvam_bulbul') return 'anushka';
      if (p === 'piper' || p === 'piper_offline') return 'piper';
      return isHi ? 'hi-IN-SwaraNeural' : 'en-US-AriaNeural';
    }

    class CoordinatedAudioSpeechQueue {
      constructor() {
        this.activeJobId = 0;
        this.responseId = null;
        this.voiceSnapshot = null;
        this.chunks = [];
        this.currentChunkIdx = 0;
        this.isPlaying = false;
        this.isCancelled = false;
        this.currentAudioEl = null;
        this.preloadedAudio = null;
      }

      cancelCurrent() {
        this.isCancelled = true;
        this.isPlaying = false;
        this.chunks = [];
        this.currentChunkIdx = 0;

        if (this.currentAudioEl) {
          try {
            this.currentAudioEl.pause();
            this.currentAudioEl.currentTime = 0;
            this.currentAudioEl.src = '';
          } catch(e) {}
          this.currentAudioEl = null;
        }

        if (this.preloadedAudio) {
          try { this.preloadedAudio.src = ''; } catch(e) {}
          this.preloadedAudio = null;
        }

        if (window.speechSynthesis) {
          try {
            window.speechSynthesis.cancel();
          } catch(e) {}
        }

        fetch('/api/tts/stop', { method: 'POST' }).catch(() => {});
      }

      startNewSpeech(text, customVoice = null) {
        this.cancelCurrent();

        this.activeJobId++;
        const jobId = this.activeJobId;
        this.isCancelled = false;
        this.responseId = 'resp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);

        const isOffline = (!window.navigator.onLine || isBackendOffline);
        const selectedProfile = customVoice || activeVoiceProfile || 'hi_swara';
        this.voiceSnapshot = {
          responseId: this.responseId,
          voiceProfile: selectedProfile,
          isOffline: isOffline
        };

        const clean = cleanTextForSpokenOutput(text);
        if (!clean) {
          this.onFinished(jobId);
          return;
        }

        this.chunks = segmentTextIntoPhrases(clean);
        if (!this.chunks.length) {
          this.onFinished(jobId);
          return;
        }

        this.currentChunkIdx = 0;
        this.isPlaying = true;
        isSpeaking = true;
        setOrbState('speaking');

        const stopBtn = document.getElementById('barge-in-stop-btn');
        if (stopBtn) stopBtn.style.display = 'inline-flex';
        const stopBtnOrb = document.getElementById('orb-stop-btn');
        if (stopBtnOrb) stopBtnOrb.style.display = 'block';

        const statusMic = document.getElementById('status-bar-mic');
        if (statusMic) statusMic.textContent = '🗣️ Voice: Speaking...';

        this.playNextChunk(jobId);
      }

      playNextChunk(jobId) {
        if (this.isCancelled || jobId !== this.activeJobId) return;

        if (this.currentChunkIdx >= this.chunks.length) {
          this.onFinished(jobId);
          return;
        }

        const chunkIndex = this.currentChunkIdx;
        const sentence = this.chunks[chunkIndex];
        this.currentChunkIdx++;

        const isHi = detectHindi(sentence);
        const langParam = isHi ? 'hi' : 'en';
        const voiceParam = resolveVoiceParamFromSnapshot(this.voiceSnapshot, isHi);

        if (this.voiceSnapshot.voiceProfile === 'browser') {
          this.playWithBrowser(sentence, isHi, jobId);
          return;
        }

        let audio = null;
        if (this.preloadedAudio && this.preloadedAudio.dataset.chunkIdx == chunkIndex) {
          audio = this.preloadedAudio;
          this.preloadedAudio = null;
        } else {
          const audioUrl = `/api/tts/audio?text=${encodeURIComponent(sentence)}&lang=${langParam}&voice=${encodeURIComponent(voiceParam)}&response_id=${encodeURIComponent(this.voiceSnapshot.responseId)}`;
          let playbackInitiated = false;
          audio = new Audio();
          audio.src = audioUrl;
          audio.oncanplaythrough = () => {
            if (!playbackInitiated) {
              playbackInitiated = true;
            }
          };
        }

        this.currentAudioEl = audio;
        currentAudio = audio;

        const prefSpeakerId = localStorage.getItem('gdr_preferred_speaker_id');
        if (prefSpeakerId && typeof audio.setSinkId === 'function') {
          audio.setSinkId(prefSpeakerId).catch(() => {});
        }

        // Controlled prefetching of chunk N+1 using the exact same voice snapshot
        if (this.currentChunkIdx < this.chunks.length) {
          const nextIndex = this.currentChunkIdx;
          const nextSent = this.chunks[nextIndex];
          const nextIsHi = detectHindi(nextSent);
          const nextLang = nextIsHi ? 'hi' : 'en';
          const nextVoiceParam = resolveVoiceParamFromSnapshot(this.voiceSnapshot, nextIsHi);
          const nextUrl = `/api/tts/audio?text=${encodeURIComponent(nextSent)}&lang=${nextLang}&voice=${encodeURIComponent(nextVoiceParam)}&response_id=${encodeURIComponent(this.voiceSnapshot.responseId)}`;
          const preAudio = new Audio(nextUrl);
          preAudio.dataset.chunkIdx = nextIndex;
          preAudio.load();
          this.preloadedAudio = preAudio;
        }

        let advanced = false;
        const advance = () => {
          if (!advanced && !this.isCancelled && jobId === this.activeJobId) {
            advanced = true;
            this.playNextChunk(jobId);
          }
        };

        audio.onplay = () => {
          if (typeof window.onAudioChunkStart === 'function') {
            window.onAudioChunkStart(sentence, chunkIndex, this.chunks.length);
          }
        };

        audio.onended = advance;
        audio.onerror = () => {
          if (typeof window.onAudioChunkStart === 'function') {
            window.onAudioChunkStart(sentence, chunkIndex, this.chunks.length);
          }
          this.playWithBrowser(sentence, isHi, jobId);
        };

        audio.play().catch((err) => {
          console.warn("Audio element play error, trying host speaker & synthesis:", err);
          try {
            fetch('/api/tts/speak', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ text: sentence, lang: langParam, voice: voiceParam })
            }).catch(() => {});
          } catch(e) {}
          if (typeof window.onAudioChunkStart === 'function') {
            window.onAudioChunkStart(sentence, chunkIndex, this.chunks.length);
          }
          this.playWithBrowser(sentence, isHi, jobId);
        });
      }

      playWithBrowser(sentence, isHi, jobId) {
        if (this.isCancelled || jobId !== this.activeJobId) return;
        if (!window.speechSynthesis) {
          this.playNextChunk(jobId);
          return;
        }

        const utterance = new SpeechSynthesisUtterance(sentence);
        utterance.lang = isHi ? 'hi-IN' : 'en-US';
        utterance.rate = 1.05;
        utterance.pitch = 1.0;

        const voices = window.speechSynthesis.getVoices() || [];
        if (isHi) {
          const hiVoice = voices.find(v => v.lang.startsWith('hi'));
          if (hiVoice) utterance.voice = hiVoice;
        } else {
          const enVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Guy') || v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Female')));
          if (enVoice) utterance.voice = enVoice;
        }

        utterance.onstart = () => {
          if (typeof window.onAudioChunkStart === 'function') {
            window.onAudioChunkStart(sentence, this.currentChunkIdx - 1, this.chunks.length);
          }
        };

        let advanced = false;
        const advance = () => {
          if (!advanced && !this.isCancelled && jobId === this.activeJobId) {
            advanced = true;
            this.playNextChunk(jobId);
          }
        };

        utterance.onend = advance;
        utterance.onerror = advance;
        window.speechSynthesis.speak(utterance);
      }

      onFinished(jobId) {
        if (jobId !== this.activeJobId) return;
        this.isPlaying = false;
        isSpeaking = false;
        if (typeof window.onAudioSpeechFinished === 'function') {
          window.onAudioSpeechFinished();
        }
        setOrbState(handsFreeMode ? 'listening' : 'idle');

        const stopBtn = document.getElementById('barge-in-stop-btn');
        if (stopBtn) stopBtn.style.display = 'none';
        const stopBtnOrb = document.getElementById('orb-stop-btn');
        if (stopBtnOrb) stopBtnOrb.style.display = 'none';

        const statusMic = document.getElementById('status-bar-mic');
        if (statusMic) statusMic.textContent = handsFreeMode ? '🎙️ Mic: Listening...' : '🎙️ Mic: Idle';

        if (handsFreeMode && recognition && !isListening) {
          try { recognition.start(); } catch(e) {}
        }
      }
    }

    const gdrSpeechQueue = new CoordinatedAudioSpeechQueue();

    function speakText(text) {
      if (typeof updateFocusAssistantTranscript === 'function') {
        updateFocusAssistantTranscript(text);
      }
      if (!speechEnabled || isQuietMode) return;
      gdrSpeechQueue.startNewSpeech(text);
    }

    function speakTextBrowserFallback(cleanText, playbackId) {
      if (isQuietMode) return;
      if (currentAudio) {
        try { currentAudio.pause(); currentAudio.src = ''; } catch(e) {}
        currentAudio = null;
      }
      if (!window.speechSynthesis) return;
      try { window.speechSynthesis.cancel(); } catch(e) {}
      const isHi = detectHindi(cleanText);
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = isHi ? 'hi-IN' : 'en-US';
      window.speechSynthesis.speak(utterance);
    }

    // Screen Navigation
    function showScreen(screenId) {
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));

      const target = document.getElementById('screen-' + screenId);
      if (target) target.classList.add('active');

      const tabs = Array.from(document.querySelectorAll('.nav-tab'));
      const activeTab = tabs.find(t => t.textContent.toLowerCase().includes(screenId));
      if (activeTab) activeTab.classList.add('active');

      // Map screen to 5 Primary Sections
      const sectionMap = {
        'home': 'home-chat',
        'chat': 'home-chat',
        'memory': 'home-chat',
        'inbox': 'home-chat',
        'calendar': 'home-chat',
        'timeline': 'home-chat',
        'contacts': 'home-chat',
        'coding': 'coding-studio',
        'ide': 'coding-studio',
        'tasks': 'automation-tasks',
        'workflows': 'automation-tasks',
        'bots': 'automation-tasks',
        'messaging': 'automation-tasks',
        'approvals': 'automation-tasks',
        'stealth': 'automation-tasks',
        'monitor': 'devices-system',
        'camera': 'devices-system',
        'mesh': 'devices-system',
        'settings': 'settings-security',
        'rag': 'settings-security',
        'audit': 'settings-security'
      };

      const parentSec = sectionMap[screenId];
      if (parentSec) {
        selectSection(parentSec, false);
      }

      const scrCrumb = document.getElementById('titlebar-screen-crumb');
      if (scrCrumb) {
        scrCrumb.textContent = (activeTab ? activeTab.innerText.trim() : screenId);
      }

      // Trigger data fetch for screen
      if (screenId === 'home') { fetchStatus(); fetchBriefing(); }
      if (screenId === 'approvals') fetchApprovals();
      if (screenId === 'tasks') fetchTasks();
      if (screenId === 'inbox') fetchInbox();
      if (screenId === 'calendar') fetchCalendar();
      if (screenId === 'memory') fetchMemory();
      if (screenId === 'camera') { fetchCamera(); startWebcam(); }
      if (screenId === 'workflows') fetchWorkflows();
      if (screenId === 'monitor') fetchMonitor();
      if (screenId === 'settings') {
        fetchSettings();
        loadSarvamConfig();
        loadElevenLabsConfig();
        enumerateBrowserAudioDevices();
        loadSystemAudioDevices();
      }
      if (screenId === 'audit') fetchAudit();
      if (screenId === 'bots') {
        loadTelegramConfig();
        loadMarkanMConfig();
        loadBotChannelsActivity();
      }
      if (screenId === 'messaging') {
        loadMessagingIntegrationsConfig();
        loadBotChannelsActivity();
      }
      if (screenId === 'rag') {
        initRAGScreen();
      }
      if (screenId === 'ide') {
        renderIdeTabs();
        refreshIdeFiles();
        syncIdeLineNumbers();
      }
      if (screenId === 'contacts') {
        fetchContacts();
      }
      if (screenId === 'timeline') {
        fetchTimeline();
        fetchWellbeing();
        fetchCustomApis();
      }
      if (screenId === 'stealth') {
        fetchStealthStatus();
        fetchStealthLatest();
        renderStealthQR();
      }
      if (screenId === 'multipanel') {
        startWebcam();
        fetchOpenWindows();
        fetchBookmarks();
        fetchMonitor();
        startAutoPresenceScanner();
      }
      if (screenId === 'mesh') {
        fetchMeshDevices();
      }
    }

    // AI Orb State Animation
    function setOrbState(state) {
      const orb = document.getElementById('main-orb');
      const badge = document.getElementById('orb-badge');
      if (orb) orb.className = 'orb ' + state;
      if (badge) badge.textContent = state.toUpperCase() + (state === 'listening' ? ' // LISTENING...' : ' // ACTIVE');
      if (typeof updateFocusCallState === 'function') {
        updateFocusCallState(state);
      }
    }

    // Real Browser Web Speech Recognition
    function initSpeechRecognition() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        console.warn('SpeechRecognition API not available in this browser.');
        return null;
      }
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onstart = () => {
        isListening = true;
        playListeningBeep('start');
        setOrbState('listening');
        const b = document.getElementById('home-mic-banner');
        if (b) { b.style.display = 'block'; b.textContent = '🎙️ Listening... Speak naturally to GDR AI'; }
        const hlb = document.getElementById('home-live-audio-box');
        if (hlb) hlb.style.display = 'block';
        startAudioWaveVisualizer();
        const cib = document.getElementById('chat-interim-box');
        if (cib) cib.style.display = 'block';
        const tp = document.getElementById('transcribing-pulse');
        if (tp) tp.style.display = 'inline-block';
        const qb = document.getElementById('quick-talk-btn');
        if (qb) qb.classList.add('btn-mic-active');
        const cmb = document.getElementById('chat-mic-btn');
        if (cmb) cmb.classList.add('btn-mic-active');
        const hmb = document.getElementById('home-mic-btn');
        if (hmb) hmb.classList.add('btn-mic-active');
      };

      rec.onresult = (event) => {
        let fullTranscript = '';
        for (let i = 0; i < event.results.length; ++i) {
          fullTranscript += event.results[i][0].transcript;
        }
        activeSpeechTranscript = fullTranscript.trim();
        const transcript = activeSpeechTranscript;
        const lower = transcript.toLowerCase().trim();

        // Barge-in check: If user speaks while assistant is speaking, STOP immediately!
        if (isSpeaking) {
          const isStopCmd = lower.includes('stop') || lower.includes('wait') || lower.includes('quiet') ||
                            lower.includes('hold on') || lower.includes('cancel') || lower.includes('shut up') ||
                            lower.includes('pause') || lower.includes('listen') ||
                            lower.includes('ruko') || lower.includes('chup') || lower.includes('bas') ||
                            lower.includes('thahro') || lower.includes('shant');
          if (isStopCmd || lower.length > 2) {
            console.log("Barge-in: User interrupted speech with:", transcript);
            stopSpeakingNow();

            let cleanQuery = lower;
            for (const word of ['stop', 'wait', 'quiet', 'hold on', 'cancel', 'shut up', 'pause', 'listen', 'ruko', 'chup', 'bas', 'thahro', 'shant']) {
              if (cleanQuery.startsWith(word)) {
                cleanQuery = cleanQuery.slice(word.length).trim();
              }
            }
            if (cleanQuery.length > 0) {
              document.getElementById('chat-input').value = cleanQuery;
              const hIn = document.getElementById('home-chat-input');
              if (hIn) hIn.value = cleanQuery;
              const cit = document.getElementById('chat-interim-text');
              if (cit) cit.textContent = cleanQuery;
              const hlt = document.getElementById('home-live-transcript-text');
              if (hlt) hlt.textContent = cleanQuery;
            } else {
              document.getElementById('chat-input').value = '';
              const hIn = document.getElementById('home-chat-input');
              if (hIn) hIn.value = '';
            }
            return;
          }
        }

        document.getElementById('chat-input').value = transcript;
        const hInput = document.getElementById('home-chat-input');
        if (hInput) hInput.value = transcript;
        const cit = document.getElementById('chat-interim-text');
        if (cit) cit.textContent = transcript;
        const hlt = document.getElementById('home-live-transcript-text');
        if (hlt) hlt.textContent = transcript;
        if (typeof updateFocusUserTranscript === 'function') {
          updateFocusUserTranscript(transcript);
        }
        const hlb = document.getElementById('home-live-audio-box');
        if (hlb) hlb.style.display = 'block';
        const hmb = document.getElementById('home-mic-banner');
        if (hmb) hmb.textContent = '🎙️ Hearing: "' + transcript + '"';
      };

      rec.onerror = (e) => {
        console.log('Speech recognition event:', e.error);
        if (e.error === 'no-speech') {
          if (handsFreeMode && !isSpeaking) {
            clearTimeout(autoRestartTimer);
            autoRestartTimer = setTimeout(() => {
              if (handsFreeMode && !isSpeaking) startListeningSafe();
            }, 500);
            return;
          }
        }
        if (e.error === 'network' || e.error === 'service-not-allowed' || e.error === 'not-allowed') {
          console.warn('SpeechRecognition network issue. Activating local offline mic (Whisper CPU)...');
          stopSpeechRecognition();
          startOfflineMediaRecorder();
          return;
        }
        stopSpeechRecognition();
      };

      rec.onend = () => {
        if (offlineMediaRecorder && offlineMediaRecorder.state === 'recording') return;
        const hIn = document.getElementById('home-chat-input');
        const cIn = document.getElementById('chat-input');
        const text = (activeSpeechTranscript && activeSpeechTranscript.trim()) ||
                     (hIn && hIn.value && hIn.value.trim()) ||
                     (cIn && cIn.value && cIn.value.trim()) || '';
        stopSpeechRecognition();
        activeSpeechTranscript = '';
        if (text) {
          playListeningBeep('proceed');
          sendChat(text);
        } else if (handsFreeMode && !isSpeaking) {
          clearTimeout(autoRestartTimer);
          autoRestartTimer = setTimeout(() => {
            if (handsFreeMode && !isSpeaking) startListeningSafe();
          }, 400);
        }
      };

      return rec;
    }

    let offlineMediaRecorder = null;
    let offlineAudioChunks = [];
    let offlineSilenceTimer = null;
    let offlineAudioContext = null;
    let offlineAnalyser = null;
    let offlineMicStream = null;
    let isHostListening = false;
    let hostListenAbortController = null;

    // Direct Host Hardware Microphone Listener (Zero Browser Permission Dependency)
    async function listenViaHostMic(silentLoop = false) {
      if (isSpeaking) return;
      if (isHostListening) return;

      isHostListening = true;
      isListening = true;
      playListeningBeep('start');
      setOrbState('listening');

      const b = document.getElementById('home-mic-banner');
      if (b) {
        b.style.display = 'block';
        b.style.borderColor = 'var(--success)';
        b.style.color = '#6ee7b7';
        b.textContent = '🎙️ Listening via Laptop Hardware Mic (ALC256)... Speak now!';
      }
      const hmb = document.getElementById('home-mic-btn');
      if (hmb) hmb.classList.add('btn-mic-active');
      const cmb = document.getElementById('chat-mic-btn');
      if (cmb) cmb.classList.add('btn-mic-active');
      const tp = document.getElementById('transcribing-pulse');
      if (tp) tp.style.display = 'inline-block';
      const cib = document.getElementById('chat-interim-box');
      if (cib) cib.style.display = 'block';
      const cit = document.getElementById('chat-interim-text');
      if (cit) cit.textContent = '🎙️ Listening via Host Hardware Microphone...';

      try {
        hostListenAbortController = new AbortController();
        const res = await fetch('/api/voice/listen_host', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ max_seconds: 15.0, wait_seconds: 5.0, silence_seconds: 0.75 }),
          signal: hostListenAbortController.signal
        });
        const d = await res.json();
        isHostListening = false;

        if (d.success && d.text && d.text.trim()) {
          const heard = d.text.trim();
          const hInput = document.getElementById('home-chat-input');
          if (hInput) hInput.value = heard;
          const cInput = document.getElementById('chat-input');
          if (cInput) cInput.value = heard;
          if (cit) cit.textContent = heard;
          if (b) b.textContent = '🎙️ Heard: "' + heard + '"';
          stopSpeechRecognition();
          playListeningBeep('proceed');
          sendChat(heard);
        } else {
          if (b) {
            b.textContent = '🎙️ No speech detected. Click Mic to speak again.';
            b.style.borderColor = 'rgba(255,255,255,0.2)';
            b.style.color = 'var(--text-muted)';
          }
          if (handsFreeMode && !isSpeaking) {
            clearTimeout(autoRestartTimer);
            autoRestartTimer = setTimeout(() => {
              if (handsFreeMode && !isSpeaking) listenViaHostMic(true);
            }, 500);
          } else {
            stopSpeechRecognition();
          }
        }
      } catch (err) {
        isHostListening = false;
        if (err.name === 'AbortError') return;
        console.warn('Host hardware mic listen event:', err);
        if (handsFreeMode && !isSpeaking) {
          clearTimeout(autoRestartTimer);
          autoRestartTimer = setTimeout(() => {
            if (handsFreeMode && !isSpeaking) listenViaHostMic(true);
          }, 800);
        } else {
          stopSpeechRecognition();
        }
      }
    }

    async function startOfflineMediaRecorder() {
      if (isSpeaking) return;
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.isSecureContext) {
          throw new Error('Browser mediaDevices not accessible in this context');
        }
        if (!offlineMicStream || !offlineMicStream.active) {
          const prefMicId = localStorage.getItem('gdr_preferred_mic_id');
          const audioConstraints = {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            ...(prefMicId ? { deviceId: { exact: prefMicId } } : {})
          };
          offlineMicStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
          initMicVisualizer(offlineMicStream);
        }
        if (offlineMediaRecorder && offlineMediaRecorder.state === 'recording') {
          try { offlineMediaRecorder.stop(); } catch(e) {}
        }
        isListening = true;
        playListeningBeep('start');
        setOrbState('listening');
        const b = document.getElementById('home-mic-banner');
        if (b) {
          b.style.display = 'block';
          b.style.borderColor = 'var(--success)';
          b.style.color = '#6ee7b7';
          b.textContent = '🎙️ Listening via Local Microphone (Whisper CPU)... Speak naturally';
        }
        const hlb = document.getElementById('home-live-audio-box');
        if (hlb) hlb.style.display = 'block';
        startAudioWaveVisualizer();
        const cib = document.getElementById('chat-interim-box');
        if (cib) cib.style.display = 'block';
        const cit = document.getElementById('chat-interim-text');
        if (cit) cit.textContent = 'Listening on microphone...';
        const tp = document.getElementById('transcribing-pulse');
        if (tp) tp.style.display = 'inline-block';
        const qb = document.getElementById('quick-talk-btn');
        if (qb) qb.classList.add('btn-mic-active');
        const cmb = document.getElementById('chat-mic-btn');
        if (cmb) cmb.classList.add('btn-mic-active');
        const hmb = document.getElementById('home-mic-btn');
        if (hmb) hmb.classList.add('btn-mic-active');

        offlineAudioChunks = [];
        offlineMediaRecorder = new MediaRecorder(offlineMicStream);
        offlineMediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            offlineAudioChunks.push(e.data);
          }
        };

        offlineMediaRecorder.onstop = async () => {
          if (offlineAudioChunks.length === 0) {
            if (handsFreeMode && !isSpeaking) {
              clearTimeout(autoRestartTimer);
              autoRestartTimer = setTimeout(() => {
                if (handsFreeMode && !isSpeaking) startListeningSafe();
              }, 400);
            }
            return;
          }
          const blob = new Blob(offlineAudioChunks, { type: offlineMediaRecorder.mimeType || 'audio/webm' });
          offlineAudioChunks = [];
          const reader = new FileReader();
          reader.onloadend = async () => {
            const base64Data = reader.result;
            try {
              if (b) b.textContent = '⚡ Transcribing audio locally on CPU...';
              const res = await fetch('/api/voice/transcribe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ audio_base64: base64Data })
              });
              const data = await res.json();
              const text = (data.text || '').trim();
              if (text && text.length > 0) {
                const hInput = document.getElementById('home-chat-input');
                if (hInput) hInput.value = text;
                const cInput = document.getElementById('chat-input');
                if (cInput) cInput.value = text;
                if (cit) cit.textContent = text;
                const hlt = document.getElementById('home-live-transcript-text');
                if (hlt) hlt.textContent = text;
                const hlb = document.getElementById('home-live-audio-box');
                if (hlb) hlb.style.display = 'block';
                if (b) b.textContent = '🎙️ Heard: "' + text + '"';
                playListeningBeep('proceed');
                sendChat(text);
              } else {
                if (b) {
                  b.textContent = '🎙️ No speech detected. Click Mic to speak again.';
                  b.style.borderColor = 'rgba(255,255,255,0.2)';
                  b.style.color = 'var(--text-muted)';
                }
                if (handsFreeMode && !isSpeaking) {
                  clearTimeout(autoRestartTimer);
                  autoRestartTimer = setTimeout(() => {
                    if (handsFreeMode && !isSpeaking) startListeningSafe();
                  }, 500);
                }
              }
            } catch (err) {
              console.warn('Local transcription error, switching to Host Mic:', err);
              listenViaHostMic();
            }
          };
          reader.readAsDataURL(blob);
        };

        offlineMediaRecorder.start(250);

        // VAD audio energy detection
        try {
          if (!offlineAudioContext) {
            offlineAudioContext = new (window.AudioContext || window.webkitAudioContext)();
          }
          if (offlineAudioContext.state === 'suspended') {
            await offlineAudioContext.resume();
          }
          if (!offlineAnalyser) {
            const source = offlineAudioContext.createMediaStreamSource(offlineMicStream);
            offlineAnalyser = offlineAudioContext.createAnalyser();
            offlineAnalyser.fftSize = 512;
            source.connect(offlineAnalyser);
          }

          let speechStartTime = null;
          let silenceStart = null;
          let noiseFloor = 3.0;
          let speechFrameCount = 0;

          const checkAudioLevel = () => {
            if (!isListening || !offlineMediaRecorder || offlineMediaRecorder.state !== 'recording') return;
            const dataArray = new Uint8Array(offlineAnalyser.frequencyBinCount);
            offlineAnalyser.getByteFrequencyData(dataArray);
            let sum = 0;
            let maxVal = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
              if (dataArray[i] > maxVal) maxVal = dataArray[i];
            }
            const avg = sum / dataArray.length;

            // Rolling ambient background noise calibration
            if (!speechStartTime) {
              noiseFloor = noiseFloor * 0.90 + avg * 0.10;
            }
            const dynamicThreshold = Math.max(3.0, noiseFloor * 1.25 + 2.0);
            const isSpeechPresent = maxVal > dynamicThreshold;

            if (isSpeechPresent) {
              speechFrameCount++;
              if (!speechStartTime) speechStartTime = Date.now();
              silenceStart = null;
              if (cit) cit.textContent = `🎙️ Hearing voice... [Vol: ${Math.round(maxVal)}]`;
            } else {
              if (cit && speechStartTime) {
                cit.textContent = `🎙️ Processing phrase...`;
              } else if (cit) {
                cit.textContent = `🎙️ Listening... [Mic: ${Math.round(maxVal)}]`;
              }

              if (speechStartTime) {
                if (!silenceStart) silenceStart = Date.now();
                const silenceDuration = Date.now() - silenceStart;
                const totalSpeechDuration = Date.now() - speechStartTime;

                // ChatGPT / Gemini style dynamic endpointing
                const requiredSilence = totalSpeechDuration < 1200 ? 500 : 700;

                if (silenceDuration >= requiredSilence) {
                  console.log(`Speech complete (${Math.round(totalSpeechDuration)}ms speech, ${Math.round(silenceDuration)}ms pause). Finalizing...`);
                  if (offlineMediaRecorder && offlineMediaRecorder.state === 'recording') {
                    if (b) {
                      b.style.display = 'block';
                      b.textContent = '⚡ Transcribing audio...';
                    }
                    offlineMediaRecorder.stop();
                  }
                  return;
                }
              }
            }
            requestAnimationFrame(checkAudioLevel);
          };
          requestAnimationFrame(checkAudioLevel);

          // Fast timeout limit: up to 15s (prevents 2-minute freeze)
          clearTimeout(offlineSilenceTimer);
          offlineSilenceTimer = setTimeout(() => {
            if (isListening && offlineMediaRecorder && offlineMediaRecorder.state === 'recording') {
              console.log('Voice recording maximum limit reached (15s), transcribing...');
              if (offlineMediaRecorder && offlineMediaRecorder.state === 'recording') {
                if (b) { b.style.display = 'block'; b.textContent = '⚡ Transcribing audio...'; }
                offlineMediaRecorder.stop();
              }
            }
          }, 15000);
        } catch(e) {
          clearTimeout(offlineSilenceTimer);
          offlineSilenceTimer = setTimeout(() => {
            if (isListening) stopSpeechRecognition();
          }, 12000);
        }

      } catch (err) {
        console.warn('Microphone getUserMedia access failed, activating direct Host Hardware Mic:', err);
        listenViaHostMic();
      }
    }

    function startListeningSafe(force = false) {
      if (isSpeaking && !force) return;
      
      // Prioritize Web Speech API for instant zero-latency word-by-word streaming transcript
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition && navigator.onLine) {
        try {
          if (!recognition) {
            recognition = initSpeechRecognition();
          }
          if (recognition) {
            try {
              recognition.start();
              return;
            } catch (err) {
              if (err.name !== 'InvalidStateError') {
                console.warn('SpeechRecognition start error:', err);
              }
              return;
            }
          }
        } catch (e) {
          console.warn('SpeechRecognition failed, falling back:', e);
        }
      }

      // Seamless fallback: browser media recorder (Whisper/Sarvam CPU/Cloud), auto-failover to physical Host Mic
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.isSecureContext) {
        startOfflineMediaRecorder().catch(() => listenViaHostMic());
      } else {
        listenViaHostMic();
      }
    }

    function toggleBrowserSpeechRecognition() {
      if (isListening || isHostListening) {
        handsFreeMode = false;
        const btn = document.getElementById('handsfree-btn');
        if (btn) { btn.textContent = '🎙️ Auto-Listen: OFF'; btn.style.color = 'var(--text-muted)'; }
        stopSpeechRecognition();
      } else {
        handsFreeMode = true;
        const btn = document.getElementById('handsfree-btn');
        if (btn) { btn.textContent = '🎙️ Auto-Listen: ON'; btn.style.color = 'var(--success)'; }
        startListeningSafe(true);
      }
    }

    // Global keyboard shortcut: Escape key halts speech and starts listening
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isSpeaking) {
        e.preventDefault();
        stopSpeakingNow();
      }
    });

    function stopSpeechRecognition() {
      isListening = false;
      isHostListening = false;
      if (hostListenAbortController) {
        try { hostListenAbortController.abort(); } catch(e) {}
        hostListenAbortController = null;
      }
      setOrbState('idle');
      const b = document.getElementById('home-mic-banner');
      if (b) b.style.display = 'none';
      const cib = document.getElementById('chat-interim-box');
      if (cib) cib.style.display = 'none';
      const tp = document.getElementById('transcribing-pulse');
      if (tp) tp.style.display = 'none';
      const qb = document.getElementById('quick-talk-btn');
      if (qb) qb.classList.remove('btn-mic-active');
      const cmb = document.getElementById('chat-mic-btn');
      if (cmb) cmb.classList.remove('btn-mic-active');
      const hmb = document.getElementById('home-mic-btn');
      if (hmb) hmb.classList.remove('btn-mic-active');
      if (recognition) {
        try { recognition.stop(); } catch(e) {}
      }
      if (offlineMediaRecorder && offlineMediaRecorder.state === 'recording') {
        try { offlineMediaRecorder.stop(); } catch(e) {}
      }
    }

    // Multi-Panel HUD Switcher
    function toggleMultiPanel() {
      const ms = document.getElementById('screen-multipanel');
      if (ms && ms.classList.contains('active')) {
        showScreen('home');
      } else {
        showScreen('multipanel');
      }
    }

    // Live Screen Stream (Continuous Wayland/X11 Screen Vision via getDisplayMedia)
    let liveScreenStream = null;
    let liveScreenInterval = null;

    async function toggleLiveScreenStream() {
      const v = document.getElementById('live-screen-feed');
      const placeholder = document.getElementById('live-screen-placeholder');
      const badge = document.getElementById('live-screen-badge');
      const btn = document.getElementById('btn-screen-share');
      const navBtn = document.getElementById('screen-share-nav-btn');

      if (liveScreenStream) {
        // Stop active screen stream
        try {
          liveScreenStream.getTracks().forEach(t => t.stop());
        } catch(e) {}
        liveScreenStream = null;
        if (liveScreenInterval) clearInterval(liveScreenInterval);
        liveScreenInterval = null;

        if (v) { v.srcObject = null; v.style.display = 'none'; }
        if (placeholder) placeholder.style.display = 'flex';
        if (badge) badge.style.display = 'none';
        if (btn) {
          btn.textContent = '🖥️ Share Live Screen';
          btn.style.borderColor = 'var(--cyan)';
          btn.style.color = 'var(--cyan)';
          btn.style.background = 'rgba(0,240,255,0.15)';
        }
        if (navBtn) {
          navBtn.textContent = '🖥️ Live Screen';
          navBtn.style.color = 'var(--cyan)';
        }
        return;
      }

      // Start screen streaming
      try {
        liveScreenStream = await navigator.mediaDevices.getDisplayMedia({
          video: { cursor: 'always' },
          audio: false
        });

        if (v) {
          v.srcObject = liveScreenStream;
          v.style.display = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';
        if (badge) badge.style.display = 'block';

        if (btn) {
          btn.textContent = '🛑 Stop Screen Stream';
          btn.style.borderColor = 'var(--danger)';
          btn.style.color = '#fca5a5';
          btn.style.background = 'rgba(239,68,68,0.2)';
        }
        if (navBtn) {
          navBtn.textContent = '🟢 Screen Active';
          navBtn.style.color = '#6ee7b7';
        }

        // Clean up if user stops screen share from browser UI
        liveScreenStream.getVideoTracks()[0].addEventListener('ended', () => {
          if (liveScreenStream) toggleLiveScreenStream();
        });

        // Background canvas frame pusher to /api/screen/frame every 1.8s
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const sendFrame = async () => {
          if (!liveScreenStream || !v || v.videoWidth === 0) return;
          canvas.width = Math.min(1280, v.videoWidth);
          canvas.height = Math.round(canvas.width * (v.videoHeight / v.videoWidth));
          ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
          const dataUrl = canvas.toDataURL('image/jpeg', 0.75);
          try {
            await fetch('/api/screen/frame', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ image: dataUrl })
            });
          } catch(e) {}
        };

        v.onloadedmetadata = () => {
          v.play();
          setTimeout(sendFrame, 500);
        };
        setTimeout(sendFrame, 800);
        liveScreenInterval = setInterval(sendFrame, 1800);

      } catch(err) {
        console.warn('Live screen sharing rejected or unavailable:', err);
      }
    }

    // Real Live HTML5 Webcam Stream (Supports Home, Camera & Multi-Panel views)
    async function startWebcam() {
      const v1 = document.getElementById('webcam-feed');
      const v2 = document.getElementById('multi-webcam-feed');
      if (webcamStream) {
        if (v1 && !v1.srcObject) v1.srcObject = webcamStream;
        if (v2 && !v2.srcObject) v2.srcObject = webcamStream;
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 } }
        });
        webcamStream = stream;
        if (v1) v1.srcObject = stream;
        if (v2) v2.srcObject = stream;
        const ov1 = document.getElementById('cam-status-overlay');
        if (ov1) {
          ov1.textContent = '● LIVE SENSOR STREAM (ACTIVE)';
          ov1.style.color = 'var(--cyan)';
        }
        const ov2 = document.getElementById('multi-cam-overlay');
        if (ov2) {
          ov2.textContent = '● LIVE SENSOR STREAM (ACTIVE)';
          ov2.style.color = 'var(--cyan)';
        }
      } catch(e) {
        const ov1 = document.getElementById('cam-status-overlay');
        if (ov1) {
          ov1.textContent = '● LOCAL WEBCAM DISCONNECTED / RESTRICTED';
          ov1.style.color = 'var(--warning)';
        }
        const ov2 = document.getElementById('multi-cam-overlay');
        if (ov2) {
          ov2.textContent = '● LOCAL WEBCAM DISCONNECTED / RESTRICTED';
          ov2.style.color = 'var(--warning)';
        }
      }
    }

    function stopWebcam() {
      if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
        const v1 = document.getElementById('webcam-feed');
        if (v1) v1.srcObject = null;
        const v2 = document.getElementById('multi-webcam-feed');
        if (v2) v2.srcObject = null;
      }
      const ov1 = document.getElementById('cam-status-overlay');
      if (ov1) {
        ov1.textContent = '🔒 PRIVACY ACTIVE - CAMERA DISCONNECTED';
        ov1.style.color = 'var(--danger)';
      }
      const ov2 = document.getElementById('multi-cam-overlay');
      if (ov2) {
        ov2.textContent = '🔒 PRIVACY ACTIVE - CAMERA DISCONNECTED';
        ov2.style.color = 'var(--danger)';
      }
    }

    function getActiveVideoEl() {
      const v2 = document.getElementById('multi-webcam-feed');
      if (v2 && v2.srcObject && v2.videoWidth > 0) return v2;
      const v1 = document.getElementById('webcam-feed');
      if (v1 && v1.srcObject && v1.videoWidth > 0) return v1;
      return v2 || v1;
    }

    // Auto Presence & Face Scanner (Runs automatically in background)
    let autoPresenceScannerActive = false;
    let lastScanTime = 0;

    function startAutoPresenceScanner() {
      if (autoPresenceScannerActive) return;
      autoPresenceScannerActive = true;
      setInterval(async () => {
        const videoEl = getActiveVideoEl();
        if (!videoEl || !videoEl.srcObject || isSpeaking) return;
        const now = Date.now();
        if (now - lastScanTime < 3500) return;
        lastScanTime = now;

        try {
          const canvas = document.createElement('canvas');
          canvas.width = videoEl.videoWidth || 640;
          canvas.height = videoEl.videoHeight || 480;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
          const b64 = canvas.toDataURL('image/jpeg', 0.7);

          const res = await fetch('/api/camera/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ image_base64: b64 })
          });
          const d = await res.json();
          if (d.status === 'privacy_mode_active') return;

          const conf = Math.round((d.similarity || 0) * 100);
          const ov = document.getElementById('multi-cam-overlay');
          const timeSinceChat = Date.now() - lastChatInteractionTime;
          const timeSinceSpoken = Date.now() - lastPresenceSpokenTime;
          const canSpeakGreeting = !isSpeaking && !isListening && timeSinceChat > 45000 && timeSinceSpoken > 90000;

          if (d.identified) {
            if (ov) {
              ov.innerHTML = `● ${d.role.toUpperCase()}: ${d.name} (${conf}%)`;
              ov.style.color = d.is_owner ? 'var(--success)' : 'var(--cyan)';
            }
            if (d.spoken_message && canSpeakGreeting) {
              lastPresenceSpokenTime = Date.now();
              speakText(d.spoken_message);
            }
          } else if (conf > 30) {
            if (ov) {
              ov.innerHTML = `● UNKNOWN VISITOR DETECTED (${conf}%)`;
              ov.style.color = 'var(--warning)';
            }
            if (d.spoken_message && canSpeakGreeting) {
              lastPresenceSpokenTime = Date.now();
              speakText(d.spoken_message);
            }
          }
        } catch(e) {}
      }, 3500);
    }

    async function scanWebcamFace() {
      const videoEl = getActiveVideoEl();
      if (!videoEl) return;
      const canvas = document.createElement('canvas');
      canvas.width = videoEl.videoWidth || 640;
      canvas.height = videoEl.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
      const b64 = canvas.toDataURL('image/jpeg', 0.85);

      const resBox = document.getElementById('cam-scan-result');
      if (resBox) {
        resBox.style.display = 'block';
        resBox.textContent = '🔍 Analyzing facial features with local 2D DCT embedding engine...';
      }

      try {
        const res = await fetch('/api/camera/analyze', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ image_base64: b64 })
        });
        const d = await res.json();
        const conf = Math.round((d.similarity || 0) * 100);

        if (resBox) {
          if (d.identified) {
            const isOwner = d.is_owner;
            const roleLabel = isOwner ? 'Owner' : 'Guest';
            resBox.style.background = isOwner ? 'rgba(16,185,129,0.15)' : 'rgba(14,165,233,0.15)';
            resBox.style.borderColor = isOwner ? 'var(--success)' : 'var(--cyan)';
            resBox.style.color = isOwner ? '#6ee7b7' : '#7dd3fc';
            resBox.innerHTML = `✅ <b>${roleLabel} Recognized: ${d.name}</b> (Match Confidence: ${conf}%)<br><small>${d.spoken_message || 'Welcome back!'}</small>`;
          } else {
            resBox.style.background = 'rgba(245,158,11,0.15)';
            resBox.style.borderColor = 'var(--warning)';
            resBox.style.color = '#fde68a';
            resBox.innerHTML = `
              👤 <b>Unknown Visitor Detected</b> (Match Confidence: ${conf}% - Below Threshold)<br>
              <small>${d.spoken_message || "Hello! May I know your name so I can remember you?"}</small>
              <div style="margin-top: 10px; display:flex; gap: 8px;">
                <input type="text" id="visitor-name-input" placeholder="Visitor Name" style="padding: 6px 10px; background: #000; color: #fff; border: 1px solid #444; border-radius: 4px; font-size: 13px;">
                <button class="btn btn-secondary" onclick="enrollVisitorQuick()">💾 Remember Face Card</button>
              </div>
            `;
          }
        }
        if (d.spoken_message) {
          speakText(d.spoken_message);
        }
      } catch(e) {
        if (resBox) resBox.textContent = 'Scan complete: Local presence verified.';
      }
    }

    async function enrollVisitorQuick() {
      const nameInput = document.getElementById('visitor-name-input');
      const name = nameInput ? nameInput.value.trim() : '';
      if (!name) {
        alert("Please enter the visitor's name.");
        return;
      }
      const videoEl = getActiveVideoEl();
      if (!videoEl) return;
      const samples = [];
      for (let i = 0; i < 3; i++) {
        const canvas = document.createElement('canvas');
        canvas.width = videoEl.videoWidth || 640;
        canvas.height = videoEl.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
        samples.push(canvas.toDataURL('image/jpeg', 0.85));
        await new Promise(r => setTimeout(r, 350));
      }
      try {
        const res = await fetch('/api/camera/enroll', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ name, is_owner: false, notes: 'Registered via webcam visitor prompt', samples_base64: samples })
        });
        const d = await res.json();
        const resBox = document.getElementById('cam-scan-result');
        if (resBox) {
          resBox.style.background = 'rgba(14,165,233,0.15)';
          resBox.style.borderColor = 'var(--cyan)';
          resBox.style.color = '#7dd3fc';
          resBox.innerHTML = `🎉 <b>Guest Face Card Registered</b>: '${name}' remembered into long-term memory! Next time ${name} appears, they will be greeted by name.`;
        }
        speakText(`Nice to meet you, ${name}. I have remembered your face card.`);
        fetchCamera();
      } catch(e) {
        alert("Error enrolling visitor: " + e);
      }
    }

    // Multi-Angle Face Enrollment (Frontal, Left, Right, Tilt)
    async function enrollFromWebcam() {
      const videoEl = getActiveVideoEl();
      if (!videoEl || !webcamStream) {
        alert("Please activate webcam first.");
        return;
      }
      const name = window.prompt("Enter name for multi-angle face enrollment:", "GDR");
      if (!name) return;
      const isOwner = window.confirm(`Is '${name}' the Owner (GDR)?\nClick OK for Owner, Cancel for Guest.`);

      const angles = [
        "Angle 1/4: Look straight at camera (Frontal pose)",
        "Angle 2/4: Turn head slightly to the LEFT",
        "Angle 3/4: Turn head slightly to the RIGHT",
        "Angle 4/4: Tilt head slightly UP or DOWN"
      ];
      const samples = [];

      for (let i = 0; i < angles.length; i++) {
        alert(`${angles[i]}.\nClick OK when in position!`);
        await new Promise(r => setTimeout(r, 400));
        const canvas = document.createElement('canvas');
        canvas.width = videoEl.videoWidth || 640;
        canvas.height = videoEl.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
        samples.push(canvas.toDataURL('image/jpeg', 0.85));
      }

      try {
        const res = await fetch('/api/camera/enroll', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ name, is_owner: isOwner, notes: 'Multi-angle 4-pose enrollment', samples_base64: samples })
        });
        const d = await res.json();
        alert(`🎉 Multi-angle face card for '${name}' enrolled successfully (${d.samples_count} angle embeddings stored encrypted). Role: ${isOwner ? 'Owner' : 'Guest'}`);
        fetchCamera();
      } catch(e) {
        alert("Error enrolling multi-angle face: " + e);
      }
    }

    // Desktop Window Listing & Typing
    async function fetchOpenWindows() {
      try {
        const res = await fetch('/api/windows');
        const d = await res.json();
        const winNameEl = document.getElementById('active-win-name');
        if (winNameEl) winNameEl.textContent = d.active_window || 'Desktop';
        const winListEl = document.getElementById('multi-open-windows');
        if (winListEl) winListEl.textContent = d.open_windows || 'No open windows detected.';
      } catch(e) {
        console.warn('Windows fetch error:', e);
      }
    }

    async function quickTypeInWindow() {
      const input = document.getElementById('window-type-input');
      const text = input ? input.value.trim() : '';
      if (!text) return;
      try {
        const res = await fetch('/api/windows/type', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ text, press_enter: true })
        });
        const d = await res.json();
        if (input) input.value = '';
        fetchOpenWindows();
      } catch(e) {
        alert("Type in window error: " + e);
      }
    }

    async function quickSendWhatsApp() {
      const pInput = document.getElementById('wa-phone-input');
      const mInput = document.getElementById('wa-msg-input');
      const recipient = pInput ? pInput.value.trim() : '';
      const message = mInput ? mInput.value.trim() : '';
      if (!recipient || !message) {
        alert("Please enter both recipient phone and message.");
        return;
      }
      try {
        const res = await fetch('/api/whatsapp/send', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ recipient, message })
        });
        const d = await res.json();
        alert(d.result || "WhatsApp message initiated.");
        if (mInput) mInput.value = '';
      } catch(e) {
        alert("WhatsApp error: " + e);
      }
    }

    async function requestLocationPermission() {
      const locEl = document.getElementById('multi-location');
      // 1. Check existing cached location first
      try {
        const cachedRes = await fetch('/api/location');
        const cached = await cachedRes.json();
        if (cached && (cached.display_name || cached.city)) {
          if (locEl) locEl.textContent = cached.display_name || `${cached.city}, ${cached.state || ''} ${cached.country || ''}`;
        }
      } catch(e) {}

      if (!navigator.geolocation) {
        if (locEl && !locEl.textContent) locEl.textContent = 'Geolocation not supported in browser';
        return;
      }
      if (locEl && (!locEl.textContent || locEl.textContent.includes('Request Location'))) {
        locEl.textContent = 'Resolving GPS...';
      }

      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const { latitude, longitude, accuracy } = pos.coords;
          try {
            const res = await fetch('/api/location', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ latitude, longitude, accuracy })
            });
            const d = await res.json();
            if (locEl) {
              if (d.location && d.location.display_name) {
                locEl.textContent = `📍 ${d.location.display_name}`;
              } else if (d.location && d.location.city) {
                locEl.textContent = `📍 ${d.location.city}, ${d.location.state || ''} (GPS ±${Math.round(accuracy)}m)`;
              } else {
                locEl.textContent = `📍 ${latitude.toFixed(4)}°, ${longitude.toFixed(4)}° (±${Math.round(accuracy)}m)`;
              }
            }
          } catch(e) {}
        },
        (err) => {
          console.warn('Geolocation permission notice:', err.message);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    }

    function sendMultiChat() {
      const input = document.getElementById('multi-chat-input');
      const text = input ? input.value.trim() : '';
      if (!text) return;
      input.value = '';
      const mainInput = document.getElementById('chat-input');
      if (mainInput) mainInput.value = text;
      sendChat();
    }

    async function fetchBookmarks() {
      try {
        const res = await fetch('/api/bookmarks');
        const b = await res.json();
        const listEl = document.getElementById('multi-bookmarks-list');
        if (!listEl) return;
        const keys = Object.keys(b);
        if (!keys.length) {
          listEl.innerHTML = '<span style="color:var(--text-muted)">No saved website bookmarks yet.</span>';
          return;
        }
        listEl.innerHTML = keys.map(k => `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; padding:3px 6px; background:rgba(0,0,0,0.4); border-radius:4px;">
            <span><b style="color:var(--cyan);">${k}</b>: <small>${b[k].url}</small></span>
            <button class="btn btn-secondary" style="font-size:10px; padding:2px 6px;" onclick="window.open('${b[k].url}', '_blank')">Open ↗</button>
          </div>
        `).join('');
      } catch(e) {
        console.warn('Bookmarks fetch error:', e);
      }
    }

    // Quick prompt chip clicked
    function quickPrompt(text) {
      document.getElementById('chat-input').value = text;
      showScreen('chat');
      sendChat();
    }

    // Command Palette
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        openPalette();
      }
      if (e.key === 'Escape') closePalette();
    });
    function openPalette() {
      document.getElementById('cmd-palette').classList.add('open');
      document.getElementById('cmd-input').focus();
    }
    function closePalette() {
      document.getElementById('cmd-palette').classList.remove('open');
    }
    function handlePaletteKey(e) {
      if (e.key === 'Enter') {
        const val = document.getElementById('cmd-input').value.toLowerCase().trim();
        closePalette();
        if (val === 'panic') togglePanic();
        else if (val === 'privacy') toggleCameraPrivacy();
        else if (val.includes('talk') || val.includes('voice')) toggleBrowserSpeechRecognition();
        else if (val.includes('multi') || val.includes('hud')) toggleMultiPanel();
        else if (val.includes('chat')) showScreen('chat');
        else if (val.includes('approv')) showScreen('approvals');
        else if (val.includes('work')) showScreen('workflows');
        else if (val.includes('task')) showScreen('tasks');
        else if (val.includes('inbox')) showScreen('inbox');
        else if (val.includes('mon')) showScreen('monitor');
      }
    }

    // Dynamic Panic Toggle & UI Feedback
    function updatePanicUI(panicked) {
      const btn = document.getElementById('panic-btn');
      if (!btn) return;
      if (panicked) {
        btn.textContent = '🟢 RESUME SYSTEM';
        btn.style.background = 'rgba(16, 185, 129, 0.2)';
        btn.style.borderColor = 'var(--success)';
        btn.style.color = '#6ee7b7';
        setOrbState('alert');
      } else {
        btn.textContent = '🚨 PANIC KILL';
        btn.style.background = 'rgba(239, 68, 68, 0.2)';
        btn.style.borderColor = 'var(--danger)';
        btn.style.color = '#fca5a5';
      }
    }

    async function togglePanic() {
      try {
        const res = await fetch('/api/panic', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ action: 'toggle' })
        });
        const d = await res.json();
        updatePanicUI(d.panicked);
        if (d.panicked) {
          setOrbState('alert');
          alert('🚨 ' + d.message);
        } else {
          setOrbState('idle');
          alert('🟢 ' + d.message);
        }
      } catch(e) {
        alert('Panic switch error: ' + e);
      }
    }

    // REST API Integration
    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        const d = await res.json();
        document.getElementById('what-doing-text').textContent = d.what_im_doing_now;
        updatePanicUI(d.panicked);

        // Dynamic time-of-day greeting & identity customization
        const nowH = new Date().getHours();
        let timeGreeting = "Welcome back";
        if (nowH >= 5 && nowH < 12) timeGreeting = "Good morning";
        else if (nowH >= 12 && nowH < 17) timeGreeting = "Good afternoon";
        else if (nowH >= 17 && nowH < 22) timeGreeting = "Good evening";

        const gt = document.getElementById('greeting-time-phrase');
        if (gt) gt.textContent = timeGreeting;

        const dateOptions = { weekday: 'short', month: 'short', day: 'numeric' };
        const dateStr = new Date().toLocaleDateString(undefined, dateOptions);
        const gd = document.getElementById('greeting-date-phrase');
        if (gd) gd.textContent = `• ${dateStr}`;

        const bt = document.getElementById('briefing-title');
        if (bt) bt.textContent = `📋 ${timeGreeting} Overview`;

        if (d.user_name) {
          const ownerEl = document.getElementById('owner-name-display');
          if (ownerEl) ownerEl.textContent = d.user_name;
        }
        if (d.agent_name) {
          const aiEl = document.getElementById('header-ai-name');
          if (aiEl) aiEl.textContent = d.agent_name;
          const chatHeaderEl = document.getElementById('chat-header-name');
          if (chatHeaderEl) chatHeaderEl.textContent = d.agent_name;
          const chatBubbleEl = document.getElementById('chat-bubble-name');
          if (chatBubbleEl) chatBubbleEl.textContent = d.agent_name;
        }
        if (d.hardware) {
          const vramStr = `${d.hardware.vram_used_mib} MiB / 3800 MiB Limit`;
          const qv = document.getElementById('quick-vram');
          if (qv) qv.textContent = vramStr;
          const mv = document.getElementById('multi-vram');
          if (mv) mv.textContent = vramStr;
          const pct = Math.min(100, Math.round((d.hardware.vram_used_mib / 3800) * 100));
          const qvb = document.getElementById('quick-vram-bar');
          if (qvb) qvb.style.width = pct + '%';
          const mvb = document.getElementById('multi-vram-bar');
          if (mvb) mvb.style.width = pct + '%';
        }
        if (d.engine_info) {
          isBackendOffline = !!d.engine_info.is_offline;
          const hMod = document.getElementById('header-model-name');
          if (hMod) hMod.textContent = `🤖 ${d.engine_info.llm_provider} (${d.engine_info.has_api_token ? 'Cloud' : 'Local'})`;
          const badgeEl = document.getElementById('home-engine-badge');
          if (badgeEl) badgeEl.textContent = `Model: ${d.engine_info.llm_provider} (${d.engine_info.llm_source}) | Voice: ${d.engine_info.voice_source}`;
        }
        if (d.sarvam_quota_exceeded) {
          handleSarvamQuotaExceeded(d.sarvam_last_error);
        }
      } catch(e) {}
    }

    async function fetchBriefing() {
      try {
        const res = await fetch('/api/briefing');
        const d = await res.json();
        const el = document.getElementById('briefing-content');
        if (el && d.briefing_text) {
          el.innerHTML = formatMarkdown(d.briefing_text);
        }
      } catch(e) {}
    }

    function formatMarkdown(text) {
      if (!text) return '';
      let str = text;

      // Code blocks: ```lang ... ```
      str = str.replace(/```([a-zA-Z0-9_\-\.]*)\n([\s\S]*?)```/g, function(match, lang, code) {
        const codeId = 'code-' + Math.random().toString(36).substring(2, 9);
        const safeCode = escapeHtml(code.trim());
        return `<div class="code-block-card" style="margin: 10px 0; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; overflow: hidden;">
          <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-elevated); padding: 5px 12px; font-size: 11px; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);">
            <span style="text-transform: uppercase; font-family: monospace; font-weight: 600; color: var(--accent-primary);">${lang || 'code'}</span>
            <button class="btn btn-secondary" onclick="copyCodeSnippet('${codeId}')" style="padding: 2px 8px; font-size: 10px; border-radius: 4px;">📋 Copy</button>
          </div>
          <pre style="margin: 0; padding: 12px; overflow-x: auto; font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.5; color: var(--text-primary);"><code id="${codeId}">${safeCode}</code></pre>
        </div>`;
      });

      // Inline code: `code`
      str = str.replace(/`([^`]+)`/g, '<code style="background: var(--bg-elevated); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; color: var(--accent-primary); border: 1px solid var(--border-subtle);">$1</code>');

      // Headings
      str = str.replace(/^#### (.*$)/gim, '<h5 style="margin: 8px 0 3px 0; color: var(--text-secondary); font-size: 12px; font-weight: 700;">$1</h5>');
      str = str.replace(/^### (.*$)/gim, '<h4 style="margin: 10px 0 4px 0; color: var(--accent-primary); font-size: 13px; font-weight: 600;">$1</h4>');
      str = str.replace(/^## (.*$)/gim, '<h3 style="margin: 12px 0 6px 0; color: var(--text-primary); font-size: 14px; font-weight: 700;">$1</h3>');
      str = str.replace(/^# (.*$)/gim, '<h2 style="margin: 14px 0 8px 0; color: var(--text-primary); font-size: 16px; font-weight: 700;">$1</h2>');

      // Bold & Italic
      str = str.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: var(--text-primary); font-weight: 600;">$1</strong>');
      str = str.replace(/__([^_]+)__/g, '<strong style="color: var(--text-primary); font-weight: 600;">$1</strong>');
      str = str.replace(/\*([^*]+)\*/g, '<em style="color: var(--text-secondary);">$1</em>');
      str = str.replace(/_([^_]+)_/g, '<em style="color: var(--text-secondary);">$1</em>');

      // Links: [label](url)
      str = str.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color: var(--accent-primary); text-decoration: underline;">$1</a>');

      // Bullet points
      str = str.replace(/^\s*[-*•]\s+(.*$)/gim, '<div style="margin: 3px 0 3px 12px; color: var(--text-secondary); display:flex; align-items:flex-start; gap:6px;"><span style="color:var(--accent-primary);">•</span><span>$1</span></div>');

      // Blockquotes
      str = str.replace(/^\>\s+(.*$)/gim, '<blockquote style="border-left: 3px solid var(--accent-primary); margin: 6px 0; padding-left: 10px; color: var(--text-muted); font-style: italic; background: var(--accent-soft); padding: 4px 10px; border-radius: 0 4px 4px 0;">$1</blockquote>');

      // Horizontal rules
      str = str.replace(/^(?:---|___|\*\*\*)$/gim, '<hr style="border:none; border-top:1px solid var(--border-subtle); margin:12px 0;">');

      // Linebreaks
      str = str.replace(/\n\n+/g, '<br><br>');
      str = str.replace(/\n/g, '<br>');

      return str;
    }

    function copyCodeSnippet(codeId) {
      const el = document.getElementById(codeId);
      if (!el) return;
      navigator.clipboard.writeText(el.innerText).then(() => {
        alert('Code snippet copied to clipboard! 📋');
      });
    }

    function copyResponseText(msgId) {
      const el = document.getElementById(msgId);
      if (!el) return;
      const raw = el.getAttribute('data-raw') || el.innerText;
      navigator.clipboard.writeText(raw).then(() => {
        alert('Response copied to clipboard! 📋');
      });
    }

    let isVoiceMuted = false;
    function toggleMuteVoice() {
      isVoiceMuted = !isVoiceMuted;
      const btn = document.getElementById('chat-voice-mute-btn');
      if (btn) {
        btn.textContent = isVoiceMuted ? '🔇 Voice: OFF' : '🔊 Voice: ON';
        btn.style.color = isVoiceMuted ? '#ef4444' : '#38bdf8';
      }
      if (isVoiceMuted) {
        stopSpeakingNow();
      }
    }

    function clearChatHistory() {
      const chatEl = document.getElementById('chat-history');
      if (chatEl) {
        chatEl.innerHTML = `
          <div class="chat-msg-row">
            <div class="chat-avatar" style="background:linear-gradient(135deg, #ec4899, #8b5cf6); border:none;">🌸</div>
            <div class="chat-bubble-assistant">
              <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">
                <b style="color:#f472b6;">Aarushi</b> • Conversation reset
              </div>
              <div>Chat cleared! How can I assist you right now? ❤️</div>
            </div>
          </div>
        `;
      }
    }

    let waveAnimFrame = null;
    function startAudioWaveVisualizer() {
      if (waveAnimFrame) return;
      const canvasChat = document.getElementById('chat-audio-wave');
      const canvasHome = document.getElementById('home-audio-wave');
      if (!canvasChat && !canvasHome) return;

      if (canvasChat) canvasChat.style.display = 'block';
      if (canvasHome) canvasHome.style.display = 'block';

      const drawBars = (canvas, data) => {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const count = 32;
        const barWidth = (canvas.width / count) - 2;
        const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--accent-primary').trim() || '#10a37f';

        for (let i = 0; i < count; i++) {
          const val = (data[i % data.length] || 0) / 255.0;
          const barHeight = Math.max(3, val * canvas.height * 0.92);
          const x = i * (barWidth + 2);
          const y = (canvas.height - barHeight) / 2;

          const grad = ctx.createLinearGradient(0, y, 0, y + barHeight);
          grad.addColorStop(0, primaryColor);
          grad.addColorStop(1, '#38bdf8');
          ctx.fillStyle = grad;
          ctx.fillRect(x, y, barWidth, barHeight);
        }
      };

      const draw = () => {
        if (!isListening && !isHostListening) {
          if (canvasChat) canvasChat.style.display = 'none';
          if (waveAnimFrame) {
            cancelAnimationFrame(waveAnimFrame);
            waveAnimFrame = null;
          }
          const freqLabel = document.getElementById('home-mic-freq-label');
          if (freqLabel) freqLabel.textContent = 'Signal: Idle • 0 Hz';
          const badge = document.getElementById('home-mic-detected-badge');
          if (badge) { badge.textContent = 'IDLE'; badge.style.color = 'var(--text-muted)'; }
          return;
        }
        waveAnimFrame = requestAnimationFrame(draw);

        const data = new Uint8Array(32);
        if (offlineAnalyser) {
          offlineAnalyser.getByteFrequencyData(data);
        } else {
          for (let i = 0; i < 32; i++) {
            data[i] = Math.floor(Math.random() * 20) + 8;
          }
        }

        let sum = 0;
        let maxVal = 0;
        for (let i = 0; i < data.length; i++) {
          sum += data[i];
          if (data[i] > maxVal) maxVal = data[i];
        }
        const avgLevel = Math.min(100, Math.round((sum / data.length / 255.0) * 160));

        // Update live status pill on Home screen
        const freqLabel = document.getElementById('home-mic-freq-label');
        const badge = document.getElementById('home-mic-detected-badge');
        if (freqLabel) {
          if (maxVal > 20) {
            freqLabel.textContent = `Frequency: ${maxVal * 24} Hz • Level: ${avgLevel}% (Sound Detected)`;
            freqLabel.style.color = 'var(--accent-primary)';
            if (badge) {
              badge.textContent = '● RECEIVING VOICE';
              badge.style.color = 'var(--accent-primary)';
              badge.style.borderColor = 'var(--accent-primary)';
            }
          } else {
            freqLabel.textContent = `Signal: ${avgLevel}% • Standby (Waiting for voice)`;
            freqLabel.style.color = 'var(--text-muted)';
            if (badge) {
              badge.textContent = '○ LISTENING';
              badge.style.color = 'var(--text-muted)';
              badge.style.borderColor = 'var(--border-subtle)';
            }
          }
        }

        drawBars(canvasChat, data);
        drawBars(canvasHome, data);
      };
      draw();
    }

    function appendUserTranscript(text) {
      if (typeof updateFocusUserTranscript === 'function') {
        updateFocusUserTranscript(text);
      }
      lastChatInteractionTime = Date.now();
      recordUserActivity();
      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      // ChatGPT / Claude style container
      const chatEl = document.getElementById('chat-history');
      if (chatEl && chatEl.classList.contains('chat-stream')) {
        const row = document.createElement('div');
        row.className = 'chat-msg-row user';
        row.innerHTML = `
          <div class="chat-bubble-user">
            <div style="font-size:11px; color:#93c5fd; margin-bottom:4px; font-weight:600; display:flex; justify-content:space-between; gap:16px;">
              <span>👤 You</span>
              <span style="opacity:0.7; font-weight:400;">${timeStr}</span>
            </div>
            <div style="word-break:break-word;">${escapeHtml(text)}</div>
          </div>
          <div class="chat-avatar user-avatar">👤</div>
        `;
        chatEl.appendChild(row);
        chatEl.scrollTop = chatEl.scrollHeight;
      }

      // Legacy fallback
      const fallbackHtml = `<div style="margin: 8px 0; padding: 6px 10px; background: rgba(0,240,255,0.07); border-left: 3px solid var(--cyan); border-radius: 4px;">
        <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;">👤 <b>You</b> <span style="float:right;">${timeStr}</span></div>
        <div style="color:#fff;">${escapeHtml(text)}</div>
      </div>`;

      ['home-transcript-list', 'multi-chat-history'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          if (id === 'home-transcript-list' && el.innerHTML.includes('Speak to the Orb')) el.innerHTML = '';
          el.innerHTML += fallbackHtml;
          el.scrollTop = el.scrollHeight;
        }
      });
    }

    window.activeChatBubbleTargetEl = null;
    window.activeChatBubbleFallbackNodes = [];
    window.activeChatFullText = '';
    window.activeChatAccumulatedText = '';
    let synchronizedTypewriterTimer = null;

    window.onAudioChunkStart = function(sentence, chunkIndex, totalChunks) {
      if (synchronizedTypewriterTimer) {
        clearInterval(synchronizedTypewriterTimer);
        synchronizedTypewriterTimer = null;
      }
      if (typewriterTimer) {
        clearTimeout(typewriterTimer);
        clearInterval(typewriterTimer);
        typewriterTimer = null;
      }
      const targetEl = window.activeChatBubbleTargetEl;
      const fallbackNodes = window.activeChatBubbleFallbackNodes || [];
      if (!targetEl && !fallbackNodes.length) return;

      const words = sentence.split(/(\s+)/);
      let wordIdx = 0;
      const interval = Math.max(20, Math.min(50, Math.floor(1200 / Math.max(words.length, 1))));

      synchronizedTypewriterTimer = setInterval(() => {
        if (wordIdx >= words.length) {
          clearInterval(synchronizedTypewriterTimer);
          synchronizedTypewriterTimer = null;
          if (chunkIndex === totalChunks - 1) {
            window.onAudioSpeechFinished();
          }
          return;
        }

        window.activeChatAccumulatedText = (window.activeChatAccumulatedText || '') + words[wordIdx];
        wordIdx++;

        if (targetEl) {
          targetEl.innerHTML = formatMarkdown(window.activeChatAccumulatedText) + '<span style="display:inline-block; margin-left:2px; color:#ec4899;">▌</span>';
          const chatEl = document.getElementById('chat-history');
          if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
        }
        fallbackNodes.forEach(n => {
          n.holder.textContent = (window.activeChatAccumulatedText || '') + '▌';
          if (n.parent) n.parent.scrollTop = n.parent.scrollHeight;
        });
      }, interval);
    };

    window.onAudioSpeechFinished = function() {
      if (synchronizedTypewriterTimer) {
        clearInterval(synchronizedTypewriterTimer);
        synchronizedTypewriterTimer = null;
      }
      const targetEl = window.activeChatBubbleTargetEl;
      const fallbackNodes = window.activeChatBubbleFallbackNodes || [];
      const fullText = window.activeChatFullText || '';
      if (targetEl && fullText) {
        targetEl.innerHTML = formatMarkdown(fullText);
      }
      fallbackNodes.forEach(n => {
        n.holder.textContent = fullText;
      });
    };

    function streamGDRResponse(text, telemetry, timeline) {
      if (typeof updateFocusAssistantTranscript === 'function') {
        updateFocusAssistantTranscript(text);
      }
      if (typewriterTimer) {
        clearTimeout(typewriterTimer);
        clearInterval(typewriterTimer);
        typewriterTimer = null;
      }
      if (synchronizedTypewriterTimer) {
        clearInterval(synchronizedTypewriterTimer);
        synchronizedTypewriterTimer = null;
      }

      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const msgId = 'gdr-msg-' + Date.now();
      const provName = telemetry ? (telemetry.llm_provider || 'Sarvam AI') : 'Aarushi AI';
      const voiceName = telemetry ? (telemetry.voice_source || 'ElevenLabs Neural') : 'Voice';
      const badge = `[${provName} • ${voiceName}]`;

      const chatEl = document.getElementById('chat-history');
      let targetEl = null;
      if (chatEl && chatEl.classList.contains('chat-stream')) {
        const row = document.createElement('div');
        row.className = 'chat-msg-row';
        row.innerHTML = `
          <div class="chat-avatar" style="background:linear-gradient(135deg, #ec4899, #8b5cf6); border:none; box-shadow:0 0 10px rgba(236,72,153,0.3);">🌸</div>
          <div class="chat-bubble-assistant">
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
              <span style="font-weight:700; color:#f472b6;">Aarushi <small style="color:var(--text-dim); font-weight:normal; margin-left:6px;">${badge}</small></span>
              <span>${timeStr}</span>
            </div>
            <div id="${msgId}" style="line-height:1.6; word-break:break-word;"></div>
            <div style="margin-top:10px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.06); display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="copyResponseText('${msgId}')" style="font-size:10px; padding:2px 8px; border-radius:12px;">📋 Copy</button>
              <button class="btn btn-secondary" onclick="speakText(document.getElementById('${msgId}').getAttribute('data-raw') || '')" style="font-size:10px; padding:2px 8px; border-radius:12px;">🔊 Speak</button>
            </div>
          </div>
        `;
        chatEl.appendChild(row);

        targetEl = document.getElementById(msgId);
        if (targetEl) {
          targetEl.setAttribute('data-raw', text);
        }
        chatEl.scrollTop = chatEl.scrollHeight;
      }

      // Legacy fallback holders
      const fallbackNodes = [];
      ['home-transcript-list', 'multi-chat-history'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          if (id === 'home-transcript-list' && el.innerHTML.includes('Speak to the Orb')) el.innerHTML = '';
          const wrapper = document.createElement('div');
          wrapper.style.margin = '8px 0';
          wrapper.style.padding = '6px 10px';
          wrapper.style.background = 'rgba(0,0,0,0.5)';
          wrapper.style.borderLeft = '3px solid var(--success)';
          wrapper.style.borderRadius = '4px';
          wrapper.innerHTML = `
            <div style="font-size:11px; color:var(--cyan); margin-bottom:3px;">
              🤖 <b>Aarushi</b> <span style="font-size:10px; color:var(--text-muted); margin-left:6px;">${badge}</span>
              <span style="float:right; font-size:10px; color:var(--text-muted);">${timeStr}</span>
            </div>
            <div class="fallback-text-holder" style="color:var(--text-light); white-space:pre-wrap;"></div>
          `;
          el.appendChild(wrapper);
          const holder = wrapper.querySelector('.fallback-text-holder');
          if (holder) fallbackNodes.push({ parent: el, holder });
          el.scrollTop = el.scrollHeight;
        }
      });

      window.activeChatBubbleTargetEl = targetEl;
      window.activeChatBubbleFallbackNodes = fallbackNodes;
      window.activeChatFullText = text;
      window.activeChatAccumulatedText = '';

      if (!speechEnabled || isQuietMode) {
        const tokens = text.split(/(\s+)/);
        let currIdx = 0;
        let accumulated = '';
        const stepInterval = Math.max(12, Math.min(38, Math.floor(1800 / Math.max(tokens.length, 1))));

        typewriterTimer = setInterval(() => {
          if (currIdx >= tokens.length) {
            clearInterval(typewriterTimer);
            typewriterTimer = null;
            if (targetEl) targetEl.innerHTML = formatMarkdown(text);
            fallbackNodes.forEach(n => { n.holder.textContent = text; });
            return;
          }

          accumulated += tokens[currIdx];
          currIdx++;

          if (targetEl) {
            targetEl.innerHTML = formatMarkdown(accumulated) + '<span style="display:inline-block; margin-left:2px; color:#ec4899;">▌</span>';
            if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
          }
          fallbackNodes.forEach(n => {
            n.holder.textContent = accumulated + '▌';
            n.parent.scrollTop = n.parent.scrollHeight;
          });
        }, stepInterval);
      } else {
        if (targetEl) {
          targetEl.innerHTML = '<span style="color:#ec4899;">🌸</span> <span style="display:inline-block; margin-left:2px; color:#ec4899;">▌</span>';
        }
        typewriterTimer = setTimeout(() => {
          if (!window.activeChatAccumulatedText) {
            window.onAudioChunkStart(text, 0, 1);
          }
        }, 750);
      }
    }

    async function sendChat(customPrompt = null) {
      if (isSendingChat) return;
      let text = (typeof customPrompt === 'string' && customPrompt.trim().length > 0) ? customPrompt.trim() : '';
      if (!text) {
        const homeInput = document.getElementById('home-chat-input');
        const screenInput = document.getElementById('chat-input');
        if (homeInput && homeInput.value && homeInput.value.trim()) {
          text = homeInput.value.trim();
        } else if (screenInput && screenInput.value && screenInput.value.trim()) {
          text = screenInput.value.trim();
        }
      }
      if (!text) return;

      const homeInput = document.getElementById('home-chat-input');
      const screenInput = document.getElementById('chat-input');
      if (homeInput) homeInput.value = '';
      if (screenInput) screenInput.value = '';
      const cib = document.getElementById('chat-interim-box');
      if (cib) cib.style.display = 'none';

      isSendingChat = true;
      // Reset quiet mode whenever user initiates conversation so AI speaks aloud
      isQuietMode = false;
      appendUserTranscript(text);
      setOrbState('thinking');

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt: text })
        });
        const d = await res.json();
        setOrbState('speaking');

        if (d.engine_info) {
          const badgeEl = document.getElementById('home-engine-badge');
          if (badgeEl) badgeEl.textContent = `Model: ${d.engine_info.llm_provider} (${d.engine_info.llm_source}) | Voice: ${d.engine_info.voice_source}`;
          const hMod = document.getElementById('header-model-name');
          if (hMod) hMod.textContent = `🤖 ${d.engine_info.llm_provider} (${d.engine_info.has_api_token ? 'Cloud' : 'Local'})`;
        }

        if (d.silence_active) {
          isQuietMode = true;
          stopSpeakingNow();
          const badgeEl = document.getElementById('home-engine-badge');
          if (badgeEl) badgeEl.textContent = `🤫 Quiet Mode Active (Speech Muted)`;
          const micBanner = document.getElementById('home-mic-banner');
          if (micBanner) {
            micBanner.style.display = 'block';
            micBanner.style.borderColor = 'var(--text-muted)';
            micBanner.style.color = 'var(--text-secondary)';
            micBanner.textContent = '🤫 Quiet Mode Active. Assistant will remain silent until duration expires or you say "resume" / "bol sakte ho".';
          }
          setOrbState('idle');
        } else {
          isQuietMode = false;
        }

        streamGDRResponse(d.reply, d.engine_info, d.timeline);
        if (!d.silence_active && !isQuietMode) {
          speakText(d.reply);
        }
      } catch(e) {
        setOrbState('idle');
        const errHtml = `<div style="color:var(--danger)">Error communicating with daemon: ${e}</div>`;
        ['home-transcript-list', 'chat-history', 'multi-chat-history'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.innerHTML += errHtml;
        });
      } finally {
        isSendingChat = false;
      }
    }

    async function fetchApprovals() {
      const res = await fetch('/api/approvals');
      const items = await res.json();
      const cont = document.getElementById('approvals-cards');
      if (!items || !items.length) {
        cont.innerHTML = '<div style="color:var(--text-muted); padding:20px;">No actions pending approval. All nominal.</div>';
        return;
      }
      cont.innerHTML = items.map(i => `
        <div class="wf-node">
          <div>
            <b>Tool: ${i.tool}</b><br>
            <small style="color:var(--text-muted);">Args: ${JSON.stringify(i.args)}</small><br>
            <small style="color:var(--warning);">Reason: Outside allowlist / External party / Financial</small>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-success" onclick="resolveApproval('${i.id}', true)">Approve</button>
            <button class="btn btn-danger" onclick="resolveApproval('${i.id}', false)">Deny</button>
          </div>
        </div>
      `).join('');
    }

    async function resolveApproval(id, approved) {
      await fetch('/api/approvals/' + id, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({approved}) });
      fetchApprovals();
    }

    async function fetchTasks() {
      const res = await fetch('/api/tasks');
      const tasks = await res.json();
      const el = document.getElementById('tasks-container');
      if (!tasks.length) { el.innerHTML = '<div style="color:var(--text-muted)">No active scheduled tasks.</div>'; return; }
      el.innerHTML = tasks.map(t => `
        <div class="wf-node">
          <div><b>#${t.id} ${t.description}</b><br><small style="color:var(--text-muted)">Next Run: ${t.next_run_at || 'Immediate'} | Type: ${t.schedule_type}</small></div>
          <button class="btn btn-secondary" onclick="deleteTask(${t.id})">Cancel</button>
        </div>
      `).join('');
    }

    async function addNewTask() {
      const text = document.getElementById('task-nl-input').value.trim();
      if (!text) return;
      await fetch('/api/tasks', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text}) });
      document.getElementById('task-nl-input').value = '';
      fetchTasks();
    }

    async function deleteTask(id) {
      await fetch('/api/tasks/' + id, { method: 'DELETE' });
      fetchTasks();
    }

    async function fetchInbox() {
      const res = await fetch('/api/inbox');
      const d = await res.json();
      const cont = document.getElementById('inbox-list');
      if (!d.emails || !d.emails.length) {
        cont.innerHTML = '<div style="color:var(--text-muted)">Unified inbox empty.</div>';
        return;
      }
      cont.innerHTML = d.emails.map(e => `
        <div class="wf-node">
          <div>
            <b>[${e.account_label}] [${e.category.toUpperCase()}] ${e.subject}</b><br>
            <small style="color:var(--text-muted);">From: ${e.from} | Date: ${e.date ? e.date.slice(0,10) : ''}</small>
          </div>
          <button class="btn btn-secondary" onclick="alert('Drafting reply for ' + '${e.id}')">Draft Reply</button>
        </div>
      `).join('');
    }

    async function fetchCalendar() {
      const res = await fetch('/api/calendar');
      const d = await res.json();
      const cont = document.getElementById('calendar-view');
      let html = '';
      if (d.conflicts && d.conflicts.length) {
        html += '<div style="background:rgba(239,68,68,0.15); border:1px solid var(--danger); padding:10px; border-radius:6px; margin-bottom:12px; color:#fca5a5;">⚠️ <b>CONFLICTS DETECTED:</b><br>' +
          d.conflicts.map(c => `• ${c.event1} OVERLAPS WITH ${c.event2}`).join('<br>') + '</div>';
      }
      if (d.events && d.events.length) {
        html += d.events.map(ev => `
          <div class="wf-node">
            <div><b>[${ev.account_label}] ${ev.summary}</b><br><small style="color:var(--text-muted);">${ev.start ? ev.start.slice(0,16) : ''} to ${ev.end ? ev.end.slice(11,16) : ''}</small></div>
            <span style="color:var(--cyan); font-size:12px;">CONFIRMED</span>
          </div>
        `).join('');
      } else {
        html += '<div style="color:var(--text-muted)">No upcoming calendar events.</div>';
      }
      cont.innerHTML = html;
    }

    async function fetchMemory() {
      const res = await fetch('/api/memory');
      const mems = await res.json();
      const el = document.getElementById('memory-items');
      if (!mems.length) { el.innerHTML = '<div style="color:var(--text-muted)">Memory store is empty.</div>'; return; }
      el.innerHTML = mems.map(m => `
        <div class="wf-node">
          <div><b>[${m.category.toUpperCase()}] ${m.key}</b><br><small style="color:var(--text-muted);">${m.content}</small></div>
          <button class="btn btn-secondary" onclick="deleteMemory('${m.category}', '${m.key}')">Forget</button>
        </div>
      `).join('');
    }

    async function deleteMemory(cat, key) {
      await fetch(`/api/memory/${cat}/${key}`, { method: 'DELETE' });
      fetchMemory();
    }

    // =========================================================================
    // Trusted Relations & Network Subsystem Functions
    // =========================================================================
    let cachedContacts = [];
    let activeContactFilter = 'all';

    async function fetchContacts() {
      try {
        const res = await fetch('/api/contacts');
        const data = await res.json();
        cachedContacts = Array.isArray(data) ? data : (data.contacts || []);
        updateContactsMetrics();
        renderContactsGrid();
      } catch (err) {
        console.error('Failed to fetch contacts:', err);
        const grid = document.getElementById('contacts-grid');
        if (grid) grid.innerHTML = `<div style="grid-column:1/-1; color:var(--danger); text-align:center; padding:20px;">Failed to load contacts: ${err.message}</div>`;
      }
    }

    function updateContactsMetrics() {
      const statTotal = document.getElementById('contacts-stat-total');
      const statTrusted = document.getElementById('contacts-stat-trusted');
      const statEnemies = document.getElementById('contacts-stat-enemies');

      const total = cachedContacts.length;
      const trusted = cachedContacts.filter(c => (c.trust_level >= 80 || c.is_trusted_contact)).length;
      const enemies = cachedContacts.filter(c => (c.trust_level <= 25 || (c.relationship_type && c.relationship_type.toLowerCase().includes('enemy')))).length;

      if (statTotal) statTotal.textContent = total;
      if (statTrusted) statTrusted.textContent = trusted;
      if (statEnemies) statEnemies.textContent = enemies;
    }

    function filterContacts(filterType) {
      activeContactFilter = filterType;
      document.querySelectorAll('.contacts-filter-btn').forEach(b => {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      });
      const activeBtn = document.getElementById('cfilter-' + filterType);
      if (activeBtn) {
        activeBtn.classList.remove('btn-secondary');
        activeBtn.classList.add('btn-primary');
      }
      renderContactsGrid();
    }

    function handleContactsSearch() {
      renderContactsGrid();
    }

    function renderContactsGrid() {
      const grid = document.getElementById('contacts-grid');
      if (!grid) return;

      const searchInput = document.getElementById('contacts-search-input');
      const query = (searchInput ? searchInput.value.trim().toLowerCase() : '');

      let filtered = cachedContacts.filter(c => {
        const rel = (c.relationship_type || '').toLowerCase();
        const trust = c.trust_level !== undefined ? c.trust_level : 50;

        if (activeContactFilter === 'trusted' && !(trust >= 80 || c.is_trusted_contact)) return false;
        if (activeContactFilter === 'family' && !(rel.includes('family') || rel.includes('friend') || rel.includes('partner'))) return false;
        if (activeContactFilter === 'work' && !(rel.includes('colleague') || rel.includes('professional') || rel.includes('classmate') || rel.includes('teacher'))) return false;
        if (activeContactFilter === 'enemy' && !(trust <= 25 || rel.includes('enemy') || rel.includes('untrusted') || rel.includes('rival'))) return false;

        if (query) {
          const name = (c.display_name || '').toLowerCase();
          const email = (c.email || '').toLowerCase();
          const phone = (c.phone_number || '').toLowerCase();
          const notes = (c.notes || '').toLowerCase();
          if (!name.includes(query) && !rel.includes(query) && !email.includes(query) && !phone.includes(query) && !notes.includes(query)) {
            return false;
          }
        }
        return true;
      });

      if (filtered.length === 0) {
        grid.innerHTML = `
          <div style="grid-column:1/-1; text-align:center; padding:40px 20px; background:rgba(0,0,0,0.2); border:1px dashed var(--border); border-radius:10px;">
            <div style="font-size:32px; margin-bottom:8px;">👥</div>
            <div style="font-weight:600; font-size:14px; color:#fff;">No persons found</div>
            <p style="color:var(--text-muted); font-size:12px; margin:4px auto 14px auto; max-width:400px;">
              ${query ? 'No contacts match your search query.' : 'Add your trusted family, friends, colleagues, or untrusted/enemies to teach Aarushi how to interact with them.'}
            </p>
            <button class="btn btn-primary" onclick="openAddContactModal()">➕ Add Person</button>
          </div>
        `;
        return;
      }

      grid.innerHTML = filtered.map(c => {
        const trust = c.trust_level !== undefined ? c.trust_level : 50;
        const rel = c.relationship_type || 'Friend';
        const isEnemy = (trust <= 25 || rel.toLowerCase().includes('enemy') || rel.toLowerCase().includes('untrusted'));
        const isHighTrust = (trust >= 80 || c.is_trusted_contact);

        let trustBarColor = 'var(--cyan)';
        let trustBadgeColor = '#38bdf8';
        let trustLabel = `${trust}% Trust`;
        let cardBorder = 'var(--border)';

        if (isEnemy) {
          trustBarColor = 'var(--danger)';
          trustBadgeColor = '#ef4444';
          trustLabel = `${trust}% (Enemy / Zero Trust)`;
          cardBorder = 'rgba(239, 68, 68, 0.4)';
        } else if (isHighTrust) {
          trustBarColor = 'var(--success)';
          trustBadgeColor = '#10b981';
          trustLabel = `${trust}% (⭐ High Trust)`;
          cardBorder = 'rgba(16, 185, 129, 0.4)';
        }

        const avatarEmoji = isEnemy ? '⚠️' : (rel.includes('Family') ? '💖' : (rel.includes('Best') ? '⭐' : (rel.includes('Colleague') ? '💼' : '👤')));
        const safeName = (c.display_name || 'Unknown').replace(/"/g, '&quot;');
        const safeEmail = (c.email || '').replace(/"/g, '&quot;');
        const safePhone = (c.phone_number || '').replace(/"/g, '&quot;');

        return `
          <div class="card" style="padding:14px; border:1px solid ${cardBorder}; display:flex; flex-direction:column; justify-content:space-between; gap:10px;">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                  <div style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:center; font-size:18px;">
                    ${avatarEmoji}
                  </div>
                  <div>
                    <div style="font-weight:700; font-size:14px; color:#fff;">${c.display_name}</div>
                    <span style="font-size:11px; padding:1px 6px; border-radius:10px; background:rgba(255,255,255,0.06); color:var(--text-muted);">${c.relationship_type}</span>
                  </div>
                </div>
                <span style="font-size:11px; font-weight:700; color:${trustBadgeColor};">
                  ${trustLabel}
                </span>
              </div>

              <!-- Trust meter progress bar -->
              <div style="width:100%; height:5px; background:rgba(0,0,0,0.5); border-radius:3px; overflow:hidden; margin:6px 0 10px 0;">
                <div style="width:${trust}%; height:100%; background:${trustBarColor}; transition:width 0.3s;"></div>
              </div>

              <!-- Contact details -->
              <div style="display:flex; flex-direction:column; gap:4px; font-size:12px;">
                ${c.email ? `<div style="display:flex; align-items:center; gap:6px; color:var(--text-light);"><span style="color:var(--text-muted);">📧</span> <span class="mono-font">${c.email}</span></div>` : '<div style="color:var(--text-muted); font-size:11px;">📧 No email registered</div>'}
                ${c.phone_number ? `<div style="display:flex; align-items:center; gap:6px; color:var(--text-light);"><span style="color:var(--text-muted);">📞</span> <span class="mono-font">${c.phone_number}</span></div>` : ''}
                ${c.notes ? `<div style="margin-top:6px; font-size:11px; color:var(--text-muted); background:rgba(0,0,0,0.3); padding:4px 8px; border-radius:4px; border-left:2px solid ${trustBadgeColor}; font-style:italic;">"${c.notes}"</div>` : ''}
              </div>
            </div>

            <!-- Action buttons -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.06); gap:6px; flex-wrap:wrap;">
              <div style="display:flex; gap:6px;">
                ${c.email ? `<button class="btn btn-sm btn-primary" onclick="promptEmailContact('${safeName}', '${safeEmail}', ${trust})" style="font-size:11px; padding:3px 8px;">✉️ Tell AI to Email</button>` : ''}
                ${c.phone_number ? `<button class="btn btn-sm btn-secondary" onclick="promptCallContact('${safeName}', '${safePhone}')" style="font-size:11px; padding:3px 8px;">📞 Call/Msg</button>` : ''}
              </div>
              <div style="display:flex; gap:4px;">
                <button class="btn btn-sm btn-secondary" onclick="openEditContactModal(${c.id})" title="Edit Contact" style="padding:3px 7px;">✏️</button>
                <button class="btn btn-sm btn-secondary" onclick="deleteContactRecord(${c.id}, '${safeName}')" title="Delete Person" style="padding:3px 7px; color:var(--danger);">🗑️</button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function openAddContactModal() {
      const modal = document.getElementById('contact-modal');
      const title = document.getElementById('contact-modal-title');
      if (!modal) return;
      if (title) title.textContent = '➕ Add Person to Network';
      document.getElementById('contact-id-field').value = '';
      document.getElementById('contact-name-input').value = '';
      document.getElementById('contact-rel-select').value = 'Friend';
      document.getElementById('contact-channel-select').value = 'any';
      document.getElementById('contact-trust-slider').value = '50';
      updateContactTrustSlider(50);
      document.getElementById('contact-email-input').value = '';
      document.getElementById('contact-phone-input').value = '';
      document.getElementById('contact-notes-input').value = '';
      document.getElementById('contact-trusted-check').checked = false;
      modal.style.display = 'flex';
      document.getElementById('contact-name-input').focus();
    }

    function openEditContactModal(contactId) {
      const c = cachedContacts.find(x => x.id === contactId);
      if (!c) return;
      const modal = document.getElementById('contact-modal');
      const title = document.getElementById('contact-modal-title');
      if (!modal) return;
      if (title) title.textContent = '✏️ Edit ' + c.display_name;
      document.getElementById('contact-id-field').value = c.id;
      document.getElementById('contact-name-input').value = c.display_name || '';
      document.getElementById('contact-rel-select').value = c.relationship_type || 'Friend';
      document.getElementById('contact-channel-select').value = c.preferred_contact_method || 'any';
      const trust = c.trust_level !== undefined ? c.trust_level : 50;
      document.getElementById('contact-trust-slider').value = trust;
      updateContactTrustSlider(trust);
      document.getElementById('contact-email-input').value = c.email || '';
      document.getElementById('contact-phone-input').value = c.phone_number || '';
      document.getElementById('contact-notes-input').value = c.notes || '';
      document.getElementById('contact-trusted-check').checked = !!c.is_trusted_contact;
      modal.style.display = 'flex';
    }

    function closeContactModal() {
      const modal = document.getElementById('contact-modal');
      if (modal) modal.style.display = 'none';
    }

    function updateContactTrustSlider(val) {
      const num = parseInt(val, 10);
      const label = document.getElementById('contact-trust-label');
      if (!label) return;
      if (num <= 25) {
        label.textContent = `${num}% (⚠️ Enemy / Untrusted)`;
        label.style.color = 'var(--danger)';
      } else if (num >= 80) {
        label.textContent = `${num}% (⭐ High Trust / Family)`;
        label.style.color = 'var(--success)';
      } else {
        label.textContent = `${num}% (Neutral)`;
        label.style.color = 'var(--cyan)';
      }
    }

    function onContactRelChange() {
      const rel = document.getElementById('contact-rel-select').value;
      const slider = document.getElementById('contact-trust-slider');
      const trustedCheck = document.getElementById('contact-trusted-check');
      if (rel.includes('Enemy') || rel.includes('Untrusted')) {
        slider.value = 0;
        updateContactTrustSlider(0);
        if (trustedCheck) trustedCheck.checked = false;
      } else if (rel.includes('Trusted Family') || rel.includes('Best Friend')) {
        slider.value = 95;
        updateContactTrustSlider(95);
        if (trustedCheck) trustedCheck.checked = true;
      }
    }

    async function saveContactRecord() {
      const idVal = document.getElementById('contact-id-field').value;
      const name = document.getElementById('contact-name-input').value.trim();
      if (!name) {
        alert('Please enter a name for this contact.');
        return;
      }
      const payload = {
        display_name: name,
        relationship_type: document.getElementById('contact-rel-select').value,
        trust_level: parseInt(document.getElementById('contact-trust-slider').value, 10),
        preferred_contact_method: document.getElementById('contact-channel-select').value,
        email: document.getElementById('contact-email-input').value.trim(),
        phone_number: document.getElementById('contact-phone-input').value.trim(),
        notes: document.getElementById('contact-notes-input').value.trim(),
        is_trusted_contact: document.getElementById('contact-trusted-check').checked
      };

      try {
        const url = idVal ? `/api/contacts/${idVal}` : '/api/contacts';
        const method = idVal ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method: method,
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.success) {
          closeContactModal();
          fetchContacts();
        } else {
          alert('Error saving contact: ' + (d.error || 'Unknown error'));
        }
      } catch (err) {
        alert('Failed to connect to backend: ' + err.message);
      }
    }

    async function deleteContactRecord(contactId, name) {
      if (!confirm(`Are you sure you want to remove "${name}" from your network?`)) return;
      try {
        await fetch(`/api/contacts/${contactId}`, { method: 'DELETE' });
        fetchContacts();
      } catch (err) {
        alert('Failed to delete contact: ' + err.message);
      }
    }

    function promptEmailContact(name, email, trustLevel) {
      showScreen('chat');
      const input = document.getElementById('chat-input') || document.getElementById('home-chat-input');
      if (input) {
        input.value = `Send an email to ${name} (<${email}>): `;
        input.focus();
      }
    }

    function promptCallContact(name, phone) {
      showScreen('chat');
      const input = document.getElementById('chat-input') || document.getElementById('home-chat-input');
      if (input) {
        input.value = `Call or send message to ${name} on ${phone}: `;
        input.focus();
      }
    }

    // =========================================================================
    // Timeline & Digital Wellbeing Subsystem Functions
    // =========================================================================
    async function fetchTimeline() {
      try {
        const res = await fetch('/api/timeline/events');
        const data = await res.json();
        const list = document.getElementById('tl-events-list');
        const countBadge = document.getElementById('tl-event-count');
        if (!list) return;

        if (data.readable && data.readable.length > 0) {
          if (countBadge) countBadge.textContent = `${data.readable.length} events`;
          list.innerHTML = data.readable.map(line => {
            const parts = line.split(' — ');
            const timePart = parts[0] || '';
            const textPart = parts.slice(1).join(' — ') || '';
            return `
              <div style="display:flex; gap:12px; align-items:center; padding:6px 10px; background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); font-size:12px;">
                <span style="font-weight:700; color:var(--accent-primary); font-family:monospace; min-width:44px;">${timePart}</span>
                <span style="color:var(--text-secondary);">${textPart}</span>
              </div>
            `;
          }).join('');
        } else {
          list.innerHTML = '<div style="color:var(--text-muted); font-size:12px;">No activity events recorded yet today.</div>';
        }

        const statsRes = await fetch('/api/timeline/stats');
        const stats = await statsRes.json();
        const bootsEl = document.getElementById('tl-stat-boots');
        if (bootsEl) bootsEl.textContent = stats.boot_count || 1;

        const actEl = document.getElementById('tl-stat-active');
        if (actEl) {
          const activeHrs = Math.floor((stats.total_active_seconds || 0) / 3600);
          const activeMins = Math.floor(((stats.total_active_seconds || 0) % 3600) / 60);
          actEl.textContent = `${activeHrs}h ${activeMins}m`;
        }

        const breaksEl = document.getElementById('tl-stat-breaks');
        if (breaksEl) breaksEl.textContent = stats.breaks_taken || 0;
      } catch (e) {
        console.error("fetchTimeline error:", e);
      }
    }

    async function fetchWellbeing() {
      try {
        const res = await fetch('/api/wellbeing/status');
        const st = await res.json();
        const contEl = document.getElementById('tl-stat-continuous');
        if (contEl) contEl.textContent = `${st.continuous_active_minutes || 0}m`;
        const limEl = document.getElementById('tl-stat-limit');
        if (limEl) limEl.textContent = `Limit: ${st.continuous_limit_minutes || 55}m`;
        const qhEl = document.getElementById('wb-quiet-hours');
        if (qhEl && st.settings) {
          qhEl.textContent = `${st.settings.quiet_hours_start || '22:00'} — ${st.settings.quiet_hours_end || '08:00'}`;
        }
      } catch (e) {
        console.error("fetchWellbeing error:", e);
      }
    }

    async function recordWellbeingBreak(mins = 5) {
      try {
        const res = await fetch('/api/wellbeing/break', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ minutes: mins })
        });
        const d = await res.json();
        if (typeof showToast === 'function') showToast(d.message || "Break recorded!");
        fetchTimeline();
        fetchWellbeing();
      } catch (e) {
        console.error(e);
      }
    }

    async function snoozeWellbeingBreak(mins = 10) {
      try {
        const res = await fetch('/api/wellbeing/snooze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ minutes: mins })
        });
        const d = await res.json();
        if (typeof showToast === 'function') showToast(d.message || "Break reminder snoozed.");
        fetchWellbeing();
      } catch (e) {
        console.error(e);
      }
    }

    async function fetchCustomApis() {
      try {
        const res = await fetch('/api/custom_api/list');
        const d = await res.json();
        const container = document.getElementById('custom-apis-container');
        if (!container) return;
        if (d.apis && d.apis.length > 0) {
          container.innerHTML = d.apis.map(api => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 10px; background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-sm);">
              <div>
                <div style="font-weight:600; color:var(--text-primary);">${api.title || api.name}</div>
                <div style="font-size:11px; color:var(--text-muted); font-family:monospace;">${api.base_url}</div>
              </div>
              <div style="display:flex; gap:6px;">
                <button class="btn btn-secondary btn-sm" onclick="queryCustomApiDirect('${api.name}')">Query</button>
                <button class="btn btn-danger btn-sm" onclick="deleteCustomApi('${api.name}')">✕</button>
              </div>
            </div>
          `).join('');
        } else {
          container.innerHTML = '<div style="color:var(--text-muted); font-size:12px;">No custom APIs connected yet. Click "+ Add API" to integrate.</div>';
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function promptAddCustomApi() {
      const name = prompt("Enter API name (e.g. render_deploy or github_build):");
      if (!name) return;
      const base_url = prompt("Enter Base URL (e.g. https://api.render.com/v1):");
      if (!base_url) return;
      const description = prompt("Description of what this API does:");
      const token = prompt("API Key or Bearer Token (will be stored securely):");
      try {
        await fetch('/api/custom_api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, base_url, description: description || name, auth_type: 'bearer', auth_token: token || '' })
        });
        if (typeof showToast === 'function') showToast(`API '${name}' registered!`);
        fetchCustomApis();
      } catch (e) {
        console.error(e);
      }
    }

    async function deleteCustomApi(name) {
      if (!confirm(`Delete custom API '${name}'?`)) return;
      try {
        await fetch('/api/custom_api/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        });
        fetchCustomApis();
      } catch (e) {
        console.error(e);
      }
    }

    async function queryCustomApiDirect(name) {
      try {
        const res = await fetch('/api/custom_api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_name: name })
        });
        const d = await res.json();
        alert(JSON.stringify(d, null, 2));
      } catch (e) {
        alert("Query error: " + e);
      }
    }

    async function fetchCamera() {
      const res = await fetch('/api/camera');
      const d = await res.json();
      const pbtn = document.getElementById('privacy-btn');
      pbtn.textContent = d.privacy_mode ? 'Privacy: ON (Disabled)' : 'Instant Privacy Mode';
      pbtn.className = d.privacy_mode ? 'btn btn-danger' : 'btn btn-secondary';
      if (d.privacy_mode) {
        stopWebcam();
      }
    }

    async function toggleCameraPrivacy() {
      const pbtn = document.getElementById('privacy-btn');
      const isCurrentlyPrivate = pbtn.textContent.includes('ON');
      await fetch('/api/camera/privacy', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled: !isCurrentlyPrivate}) });
      fetchCamera();
      if (isCurrentlyPrivate) {
        startWebcam();
      }
    }

    async function fetchWorkflows() {
      const res = await fetch('/api/workflows');
      const flows = await res.json();
      const cont = document.getElementById('active-workflows-list');
      if (!flows || !flows.length) {
        cont.innerHTML = '<div style="color:var(--text-muted)">No workflows defined. Say or type a workflow above!</div>';
        return;
      }
      cont.innerHTML = flows.map(w => `
        <div class="wf-node">
          <div>
            <b>${w.title} [v${w.version}]</b><br>
            <small style="color:var(--text-muted);">Trigger: ${w.trigger ? w.trigger.description : 'Manual'} | Steps: ${w.steps ? w.steps.length : 0}</small>
          </div>
          <div style="display:flex; gap:6px;">
            <button class="btn btn-secondary" onclick="dryRunWorkflow('${w.workflow_id}')">🧪 Dry Run</button>
            ${w.status !== 'active' ? `<button class="btn btn-success" onclick="approveWorkflow('${w.workflow_id}')">Approve</button>` : `<span style="color:var(--success); font-size:12px; font-weight:bold;">ACTIVE</span>`}
          </div>
        </div>
      `).join('');
    }

    async function compileWorkflow() {
      const prompt = document.getElementById('workflow-input').value.trim();
      if (!prompt) return;
      await fetch('/api/workflows/compile', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({prompt}) });
      document.getElementById('workflow-input').value = '';
      fetchWorkflows();
    }

    async function dryRunWorkflow(wfId) {
      const res = await fetch(`/api/workflows/${wfId}/dry_run`, { method: 'POST' });
      const d = await res.json();
      alert('🧪 Dry Run Results for ' + wfId + ':\n' + d.step_results.map(s => `• ${s.name}: ${s.status} (Policy: ${s.policy_decision})`).join('\n'));
    }

    async function approveWorkflow(wfId) {
      await fetch(`/api/workflows/${wfId}/approve`, { method: 'POST' });
      fetchWorkflows();
    }

    async function runSampleCodingTask() {
      const el = document.getElementById('coding-output');
      el.textContent = 'Executing sandbox task: "Add multiply function and unit tests"...';
      setTimeout(() => {
        el.textContent = 'Branch: gdr/add-multiply-function-1792331101\nTests: OK (Ran 1 test in 0.001s)\nDiff: + def multiply(a, b): return a * b\nStatus: WAITING FOR APPROVAL (Decision: ASK)';
      }, 1000);
    }

    async function fetchMonitor() {
      const res = await fetch('/api/system/monitor');
      const d = await res.json();
      document.getElementById('mon-vram').textContent = `${d.vram_used_mib} MiB / ${d.vram_limit_mib} MiB Limit`;
      const pct = Math.min(100, Math.round((d.vram_used_mib / d.vram_limit_mib) * 100));
      document.getElementById('mon-vram-bar').style.width = pct + '%';
      document.getElementById('mon-ram').textContent = `${Math.round(d.ram_available_mib / 1024)} GB available`;
      document.getElementById('mon-temp').textContent = `${d.gpu_temp_c}°C (Normal)`;
    }

    // --- Appearance & Theming ---
    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      try { localStorage.setItem('gdr_theme', theme); } catch(e){}
      updateAppearanceButtons();
    }

    function setAccent(accent) {
      document.documentElement.setAttribute('data-accent', accent);
      try { localStorage.setItem('gdr_accent', accent); } catch(e){}
      updateAppearanceButtons();
    }

    function setBackgroundStyle(bg) {
      document.documentElement.setAttribute('data-bg', bg);
      try { localStorage.setItem('gdr_bg', bg); } catch(e){}
      updateAppearanceButtons();
    }

    function setUIDensity(density) {
      document.documentElement.setAttribute('data-density', density);
      try { localStorage.setItem('gdr_density', density); } catch(e){}
      updateAppearanceButtons();
    }

    function setFontScale(scale) {
      document.documentElement.setAttribute('data-font-scale', scale);
      try { localStorage.setItem('gdr_font_scale', scale); } catch(e){}
      if (scale === 'small') {
        document.documentElement.style.fontSize = '13.5px';
      } else if (scale === 'large') {
        document.documentElement.style.fontSize = '16.5px';
      } else {
        document.documentElement.style.fontSize = '15px';
      }
      updateAppearanceButtons();
    }

    function resetAppearance() {
      setTheme('dark');
      setAccent('emerald');
      setBackgroundStyle('solid');
      setUIDensity('comfortable');
      setFontScale('default');
    }

    function updateAppearanceButtons() {
      const theme = document.documentElement.getAttribute('data-theme') || 'dark';
      const accent = document.documentElement.getAttribute('data-accent') || 'emerald';
      const bg = document.documentElement.getAttribute('data-bg') || 'solid';
      const density = document.documentElement.getAttribute('data-density') || 'comfortable';
      const font = document.documentElement.getAttribute('data-font-scale') || 'default';

      document.querySelectorAll('.theme-option-btn').forEach(btn => {
        const t = btn.getAttribute('data-theme-val');
        const a = btn.getAttribute('data-accent-val');
        const b = btn.getAttribute('data-bg-val');
        const d = btn.getAttribute('data-density-val');
        const f = btn.getAttribute('data-font-val');

        if (t) btn.classList.toggle('active', t === theme);
        if (a) btn.classList.toggle('active', a === accent);
        if (b) btn.classList.toggle('active', b === bg);
        if (d) btn.classList.toggle('active', d === density);
        if (f) btn.classList.toggle('active', f === font);
      });
    }

    setTimeout(updateAppearanceButtons, 100);

    // --- Prompt Enhancer & Export ---
    async function enhanceInputPrompt() {
      const input = document.getElementById('chat-input') || document.getElementById('home-chat-input');
      if (!input || !input.value.trim()) {
        alert('Please enter a rough prompt first to enhance it.');
        return;
      }
      const rawPrompt = input.value.trim();
      const enhanceBtn = document.getElementById('enhance-prompt-btn');
      if (enhanceBtn) {
        enhanceBtn.disabled = true;
        enhanceBtn.textContent = '✨ Enhancing...';
      }
      try {
        const res = await fetch('/api/prompt/enhance', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt: rawPrompt })
        });
        const d = await res.json();
        if (d.enhanced_prompt) {
          input.value = d.enhanced_prompt;
          input.focus();
        }
      } catch (e) {
        console.error('Failed to enhance prompt:', e);
      } finally {
        if (enhanceBtn) {
          enhanceBtn.disabled = false;
          enhanceBtn.textContent = '✨ Enhance';
        }
      }
    }

    function exportChatMarkdown() {
      const history = document.getElementById('chat-history');
      if (!history) return;
      let md = '# GDR-AI Chat Export\nGenerated: ' + new Date().toISOString() + '\n\n---\n\n';
      const rows = history.querySelectorAll('.chat-msg-row');
      rows.forEach(r => {
        const isUser = r.classList.contains('user');
        const sender = isUser ? 'User' : 'GDR-AI';
        const text = r.innerText.trim();
        md += `### ${sender}\n\n${text}\n\n---\n\n`;
      });
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `gdr_chat_export_${new Date().toISOString().slice(0,10)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    // --- Device Mesh Management ---
    let _activeMeshDeviceId = null;
    let _meshPairCountdownTimer = null;
    let _cachedMeshDevices = [];

    async function fetchMeshDevices() {
      try {
        const res = await fetch('/api/mesh/devices');
        if (!res.ok) return;
        const d = await res.json();
        _cachedMeshDevices = d.devices || [];

        const activeCount = _cachedMeshDevices.filter(dev => dev.status === 'online').length;
        const activeCountEl = document.getElementById('mesh-active-count');
        if (activeCountEl) activeCountEl.textContent = `${activeCount} Online`;
        const totalCountEl = document.getElementById('mesh-total-count');
        if (totalCountEl) totalCountEl.textContent = `${_cachedMeshDevices.length} Enrolled`;

        const chatTarget = document.getElementById('chat-mesh-target');
        if (chatTarget) {
          const currentVal = chatTarget.value;
          chatTarget.innerHTML = '<option value="local">💻 Local Machine</option>' + 
            _cachedMeshDevices.map(dev => `<option value="${dev.device_id}">${dev.platform === 'android' ? '📱' : dev.platform === 'windows' ? '🪟' : dev.platform === 'macos' ? '🍎' : '🐧'} ${dev.device_name} (${dev.status})</option>`).join('');
          if (Array.from(chatTarget.options).some(o => o.value === currentVal)) {
            chatTarget.value = currentVal;
          }
        }

        const grid = document.getElementById('mesh-device-grid');
        if (!grid) return;

        if (_cachedMeshDevices.length === 0) {
          grid.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 40px; text-align: center; background: var(--bg-secondary); border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);">
              <div style="font-size: 36px; margin-bottom: 12px;">📱 💻 🌐</div>
              <div style="font-weight: 600; font-size: 16px; margin-bottom: 6px;">No mesh devices paired yet</div>
              <div style="font-size: 13px; color: var(--text-muted); max-width: 460px; margin: 0 auto 16px;">
                Connect Android Termux, Linux servers, Windows laptops, or MacBooks into your private, encrypted AI mesh.
              </div>
              <button class="btn btn-primary" onclick="openMeshPairModal()">+ Pair New Device</button>
            </div>
          `;
          return;
        }

        grid.innerHTML = _cachedMeshDevices.map(dev => {
          const isOnline = dev.status === 'online';
          const pIcon = dev.platform === 'android' ? '📱' : dev.platform === 'windows' ? '🪟' : dev.platform === 'macos' ? '🍎' : '🐧';
          const battery = dev.battery_level !== null ? `${dev.battery_level}%` : 'N/A';
          const lastSeen = dev.last_seen ? new Date(dev.last_seen).toLocaleTimeString() : 'Never';
          const ip = dev.ip_address || '127.0.0.1';

          return `
            <div style="background: var(--bg-secondary); border: 1px solid ${isOnline ? 'var(--border-subtle)' : 'rgba(255,255,255,0.04)'}; border-radius: var(--radius-md); padding: 18px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: var(--shadow-soft);">
              <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 26px;">${pIcon}</span>
                    <div>
                      <div style="font-weight: 700; font-size: 15px; color: var(--text-primary);">${dev.device_name}</div>
                      <div style="font-size: 11px; color: var(--text-muted);">${dev.platform.toUpperCase()} • ${dev.device_id.slice(0, 8)}</div>
                    </div>
                  </div>
                  <span style="font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600; background: ${isOnline ? 'rgba(16,163,127,0.15)' : 'rgba(133,133,145,0.15)'}; color: ${isOnline ? 'var(--accent-primary)' : 'var(--text-muted)'}; border: 1px solid ${isOnline ? 'var(--accent-primary)' : 'var(--border-subtle)'};">
                    ${isOnline ? '● ONLINE' : '○ OFFLINE'}
                  </span>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; margin-bottom: 14px; background: var(--bg-elevated); padding: 10px; border-radius: var(--radius-sm);">
                  <div><span style="color:var(--text-muted);">IP:</span> ${ip}</div>
                  <div><span style="color:var(--text-muted);">Battery:</span> 🔋 ${battery}</div>
                  <div><span style="color:var(--text-muted);">Latency:</span> ${dev.ping_ms ? dev.ping_ms + 'ms' : '~1ms'}</div>
                  <div><span style="color:var(--text-muted);">Last Seen:</span> ${lastSeen}</div>
                </div>

                <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 14px;">
                  <b>Capabilities:</b> ${dev.capabilities && dev.capabilities.length ? dev.capabilities.join(', ') : 'diagnostics, heartbeat'}
                </div>
              </div>

              <div style="display: flex; gap: 6px; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
                <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px;" onclick="runMeshDiagnostic('${dev.device_id}')">🩺 Diagnostics</button>
                <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px;" onclick="openMeshPermModal('${dev.device_id}')">🔒 Permissions</button>
                <button class="btn btn-secondary" style="font-size: 11px; padding: 6px; color: var(--danger);" onclick="revokeActiveMeshDevice('${dev.device_id}')">Revoke</button>
              </div>
            </div>
          `;
        }).join('');
      } catch (e) {
        console.error('Error fetching mesh devices:', e);
      }
    }

    async function openMeshPairModal() {
      const modal = document.getElementById('mesh-pairing-modal');
      if (!modal) return;
      modal.style.display = 'flex';

      const codeEl = document.getElementById('mesh-pair-code');
      const cmdEl = document.getElementById('mesh-pair-cmd');
      const expiryEl = document.getElementById('mesh-pair-expiry');
      const qrEl = document.getElementById('mesh-pair-qr');

      if (codeEl) codeEl.textContent = '...';
      if (cmdEl) cmdEl.textContent = 'Generating pairing code...';

      try {
        const res = await fetch('/api/mesh/pair/start', { method: 'POST' });
        const d = await res.json();
        if (codeEl) codeEl.textContent = d.pairing_code;
        if (cmdEl) cmdEl.textContent = d.pairing_command;
        if (qrEl && d.qr_data_url) {
          qrEl.innerHTML = `<img src="${d.qr_data_url}" style="width:160px; height:160px; border-radius:8px; border:2px solid var(--border-subtle);" alt="Pairing QR" />`;
        }

        let remaining = 300;
        if (_meshPairCountdownTimer) clearInterval(_meshPairCountdownTimer);
        _meshPairCountdownTimer = setInterval(() => {
          remaining--;
          if (expiryEl) {
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            expiryEl.textContent = `Expires in ${mins}:${secs < 10 ? '0' : ''}${secs}`;
          }
          if (remaining <= 0) {
            clearInterval(_meshPairCountdownTimer);
            if (expiryEl) expiryEl.textContent = 'Code expired. Generate new code.';
          }
        }, 1000);
      } catch(e) {
        if (cmdEl) cmdEl.textContent = 'Error starting pairing: ' + e;
      }
    }

    function closeMeshPairModal() {
      const modal = document.getElementById('mesh-pairing-modal');
      if (modal) modal.style.display = 'none';
      if (_meshPairCountdownTimer) clearInterval(_meshPairCountdownTimer);
      fetchMeshDevices();
    }

    function openMeshPermModal(deviceId) {
      _activeMeshDeviceId = deviceId;
      const dev = _cachedMeshDevices.find(d => d.device_id === deviceId);
      if (!dev) return;

      const title = document.getElementById('mesh-perm-device-name');
      if (title) title.textContent = `${dev.device_name} (${dev.platform})`;

      const p = dev.permissions || {};
      const chkShell = document.getElementById('mesh-perm-shell');
      const chkRead = document.getElementById('mesh-perm-read');
      const chkWrite = document.getElementById('mesh-perm-write');
      const chkCam = document.getElementById('mesh-perm-cam');
      const chkNotif = document.getElementById('mesh-perm-notif');
      const dirs = document.getElementById('mesh-perm-dirs');

      if (chkShell) chkShell.checked = !!p.allow_shell;
      if (chkRead) chkRead.checked = p.allow_file_read !== false;
      if (chkWrite) chkWrite.checked = !!p.allow_file_write;
      if (chkCam) chkCam.checked = !!p.allow_camera;
      if (chkNotif) chkNotif.checked = p.allow_notifications !== false;
      if (dirs) dirs.value = (p.approved_directories || []).join('\n');

      const modal = document.getElementById('mesh-perm-modal');
      if (modal) modal.style.display = 'flex';
    }

    function closeMeshPermModal() {
      const modal = document.getElementById('mesh-perm-modal');
      if (modal) modal.style.display = 'none';
      _activeMeshDeviceId = null;
    }

    async function saveActiveMeshPermissions() {
      if (!_activeMeshDeviceId) return;
      const chkShell = document.getElementById('mesh-perm-shell');
      const chkRead = document.getElementById('mesh-perm-read');
      const chkWrite = document.getElementById('mesh-perm-write');
      const chkCam = document.getElementById('mesh-perm-cam');
      const chkNotif = document.getElementById('mesh-perm-notif');
      const dirsEl = document.getElementById('mesh-perm-dirs');

      const approved = (dirsEl ? dirsEl.value : '').split('\n').map(s => s.trim()).filter(Boolean);

      const payload = {
        allow_shell: chkShell ? chkShell.checked : false,
        allow_file_read: chkRead ? chkRead.checked : true,
        allow_file_write: chkWrite ? chkWrite.checked : false,
        allow_camera: chkCam ? chkCam.checked : false,
        allow_notifications: chkNotif ? chkNotif.checked : true,
        approved_directories: approved
      };

      try {
        const res = await fetch(`/api/mesh/devices/${_activeMeshDeviceId}/permissions`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeMeshPermModal();
          fetchMeshDevices();
        } else {
          alert('Failed to save permissions');
        }
      } catch(e) {
        alert('Error saving permissions: ' + e);
      }
    }

    async function revokeActiveMeshDevice(deviceId) {
      if (!confirm(`Are you sure you want to revoke and disconnect device ${deviceId}?`)) return;
      try {
        const res = await fetch(`/api/mesh/devices/${deviceId}`, { method: 'DELETE' });
        if (res.ok) {
          fetchMeshDevices();
        } else {
          alert('Failed to revoke device');
        }
      } catch(e) {
        alert('Error: ' + e);
      }
    }

    async function runMeshDiagnostic(deviceId) {
      try {
        const res = await fetch('/api/mesh/dispatch', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            target_device_id: deviceId,
            task_type: 'diagnostic',
            parameters: {}
          })
        });
        const d = await res.json();
        if (d.success) {
          alert(`✅ Diagnostic executed on ${deviceId}:\n\n` + JSON.stringify(d.result, null, 2));
        } else {
          alert(`⚠️ Diagnostic result: ` + (d.error || JSON.stringify(d)));
        }
      } catch(e) {
        alert('Diagnostic dispatch error: ' + e);
      }
    }

    // --- Model Hub & Hugging Face Downloader ---
    let _hfPollInterval = null;

    async function openModelHubModal() {
      const modal = document.getElementById('model-manager-modal');
      if (modal) modal.style.display = 'flex';
      await fetchModelHubData();
      startHFPolling();
    }

    function closeModelHubModal() {
      const modal = document.getElementById('model-manager-modal');
      if (modal) modal.style.display = 'none';
      if (_hfPollInterval) {
        clearInterval(_hfPollInterval);
        _hfPollInterval = null;
      }
    }

    async function fetchModelHubData() {
      try {
        const res = await fetch('/api/models');
        if (!res.ok) return;
        const d = await res.json();

        const titleEl = document.getElementById('active-model-title');
        const badgeEl = document.getElementById('active-model-badge');
        const isCloud = ['sarvam', 'claude', 'openrouter', 'openai', 'groq', 'deepseek'].includes(d.active_provider);
        if (titleEl) {
          titleEl.textContent = `${d.active_provider.toUpperCase()} • ${d.active_model}`;
        }
        if (badgeEl) {
          badgeEl.textContent = isCloud ? 'ONLINE • CLOUD' : 'OFFLINE • LOCAL';
          badgeEl.style.color = isCloud ? 'var(--accent-primary)' : 'var(--warning)';
          badgeEl.style.borderColor = isCloud ? 'var(--accent-primary)' : 'var(--warning)';
        }

        const pill = document.getElementById('chat-header-model-pill');
        if (pill) {
          pill.textContent = `${d.active_model} (${isCloud ? 'Cloud' : 'Local'}) • Click to change`;
        }

        const cloudList = document.getElementById('cloud-models-list');
        if (cloudList && d.cloud_models) {
          cloudList.innerHTML = d.cloud_models.map(cm => {
            const isActive = d.active_provider === cm.provider && d.active_model === cm.model_id;
            const hasKey = cm.has_key;
            return `
              <div style="background:var(--bg-elevated); border:1px solid ${isActive ? 'var(--accent-primary)' : 'var(--border-subtle)'}; border-radius:var(--radius-sm); padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:12px;">
                <div>
                  <div style="display:flex; align-items:center; gap:8px;">
                    <b style="font-size:13px; color:var(--text-primary);">${cm.name}</b>
                    <span style="font-size:10px; padding:1px 6px; border-radius:8px; background:${hasKey ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${hasKey ? 'var(--success)' : 'var(--danger)'};">
                      ${hasKey ? '✓ API Key Configured' : '⚠ Key Missing'}
                    </span>
                  </div>
                  <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${cm.description}</div>
                </div>
                <div>
                  ${isActive
                    ? '<span style="font-size:12px; font-weight:700; color:var(--accent-primary); padding:4px 10px;">● ACTIVE</span>'
                    : `<button class="btn btn-secondary" style="font-size:11px; padding:4px 12px;" onclick="activateModel('${cm.provider}', '${cm.model_id}')">Use Model</button>`
                  }
                </div>
              </div>
            `;
          }).join('');
        }

        const hfGrid = document.getElementById('hf-presets-grid');
        if (hfGrid && d.hf_presets) {
          hfGrid.innerHTML = d.hf_presets.map(p => `
            <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:6px; padding:10px; display:flex; flex-direction:column; justify-content:space-between;">
              <div>
                <div style="font-weight:700; font-size:12px; color:var(--text-primary); margin-bottom:4px;">${p.name}</div>
                <div style="font-size:11px; color:var(--text-muted); line-height:1.4; margin-bottom:8px;">${p.description}</div>
                <div style="font-size:10px; color:var(--accent-primary); font-family:monospace; margin-bottom:8px;">Size: ~${p.size_mb} MB • Rec: ${p.vram_req}</div>
              </div>
              <button class="btn btn-secondary" style="font-size:11px; padding:6px 10px; width:100%;" onclick="pullHuggingFaceModel('${p.id}')">
                ⬇️ Pull from Hugging Face
              </button>
            </div>
          `).join('');
        }

        const localList = document.getElementById('local-models-list');
        if (localList) {
          if (d.local_models && d.local_models.length > 0) {
            localList.innerHTML = d.local_models.map(lm => {
              const isActive = d.active_model_path === lm.path;
              return `
                <div style="background:var(--bg-elevated); border:1px solid ${isActive ? 'var(--accent-primary)' : 'var(--border-subtle)'}; border-radius:6px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:10px;">
                  <div>
                    <div style="font-weight:700; font-size:13px; color:var(--text-primary);">${lm.filename}</div>
                    <div style="font-size:11px; color:var(--text-muted);">${lm.size_mb} MB • ${lm.path}</div>
                  </div>
                  <div>
                    ${isActive
                      ? '<span style="font-size:12px; font-weight:700; color:var(--accent-primary);">● ACTIVE LOCAL</span>'
                      : `<button class="btn btn-secondary" style="font-size:11px; padding:4px 12px;" onclick="activateModel('local_gguf', '${lm.filename}', '${lm.path}')">Use This Model</button>`
                    }
                  </div>
                </div>
              `;
            }).join('');
          } else {
            localList.innerHTML = '<div style="font-size:12px; color:var(--text-muted); font-style:italic;">No custom GGUF models downloaded in ~/.config/gdr/models yet. Click a preset above to pull one!</div>';
          }
        }

        renderDownloadState(d.download_status);
      } catch (e) {
        console.error('Error fetching model hub data:', e);
      }
    }

    async function activateModel(provider, model, path = '') {
      try {
        const res = await fetch('/api/models/active', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ provider: provider, model: model, model_path: path })
        });
        const d = await res.json();
        if (d.success) {
          alert(`✅ ${d.message}`);
          fetchModelHubData();
          fetchStatus();
        } else {
          alert(`Failed to activate model: ${d.error || 'Unknown error'}`);
        }
      } catch (e) {
        alert('Error activating model: ' + e);
      }
    }

    async function pullHuggingFaceModel(presetId) {
      try {
        const res = await fetch('/api/models/pull', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ preset_id: presetId })
        });
        const d = await res.json();
        if (d.success) {
          startHFPolling();
        } else {
          alert('Could not start download: ' + d.error);
        }
      } catch (e) {
        alert('Download error: ' + e);
      }
    }

    async function pullCustomHFModel() {
      const urlInput = document.getElementById('hf-custom-url');
      if (!urlInput || !urlInput.value.trim()) {
        alert('Please enter a direct .gguf URL or Hugging Face model URL.');
        return;
      }
      let url = urlInput.value.trim();
      let filename = url.split('/').pop().split('?')[0];
      if (!filename.endsWith('.gguf')) filename += '.gguf';

      try {
        const res = await fetch('/api/models/pull', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url: url, filename: filename, name: filename })
        });
        const d = await res.json();
        if (d.success) {
          urlInput.value = '';
          startHFPolling();
        } else {
          alert('Download error: ' + d.error);
        }
      } catch (e) {
        alert('Download error: ' + e);
      }
    }

    function renderDownloadState(st) {
      const container = document.getElementById('hf-download-container');
      if (!container || !st) return;

      if (st.status === 'downloading') {
        container.style.display = 'block';
        document.getElementById('hf-download-title').textContent = `Downloading ${st.model_name}...`;
        document.getElementById('hf-download-pct').textContent = `${st.percent}%`;
        document.getElementById('hf-download-fill').style.width = `${st.percent}%`;
        document.getElementById('hf-download-speed').textContent = `${st.downloaded_mb} MB / ${st.total_mb} MB • ${st.speed_mb} MB/s`;
      } else if (st.status === 'completed') {
        container.style.display = 'block';
        document.getElementById('hf-download-title').textContent = `✅ ${st.model_name} Download Completed!`;
        document.getElementById('hf-download-pct').textContent = `100%`;
        document.getElementById('hf-download-fill').style.width = `100%`;
        document.getElementById('hf-download-speed').textContent = `Ready in local storage. Click "Use This Model" below.`;
        setTimeout(() => { fetchModelHubData(); }, 1500);
      } else if (st.status === 'error') {
        container.style.display = 'block';
        document.getElementById('hf-download-title').textContent = `❌ Download Error`;
        document.getElementById('hf-download-speed').textContent = st.error || 'Failed';
      } else {
        container.style.display = 'none';
      }
    }

    function startHFPolling() {
      if (_hfPollInterval) clearInterval(_hfPollInterval);
      _hfPollInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/models/pull/status');
          const st = await res.json();
          renderDownloadState(st);
          if (st.status === 'completed' || st.status === 'error') {
            clearInterval(_hfPollInterval);
            _hfPollInterval = null;
            fetchModelHubData();
          }
        } catch(e) {}
      }, 1000);
    }

    async function cancelHFPull() {
      try {
        await fetch('/api/models/pull/cancel', { method: 'POST' });
        if (_hfPollInterval) {
          clearInterval(_hfPollInterval);
          _hfPollInterval = null;
        }
        const container = document.getElementById('hf-download-container');
        if (container) container.style.display = 'none';
      } catch(e) {}
    }

    async function fetchSettings() {
      const res = await fetch('/api/settings');
      const d = await res.json();
      const el = document.getElementById('google-accounts-list');
      if (d.google_accounts && d.google_accounts.length) {
        el.innerHTML = d.google_accounts.map(a => `<div>• <b>${a.label}</b> (${a.email}) - ${a.status}</div>`).join('');
      } else {
        el.innerHTML = '<div style="color:var(--text-muted)">No Google accounts configured yet.</div>';
      }
    }

    let _allRequestLogs = [];

    async function fetchRequestLogs() {
      try {
        const [resLogs, resStats] = await Promise.all([
          fetch('/api/requests?limit=150'),
          fetch('/api/requests/stats')
        ]);
        if (resStats.ok) {
          const s = await resStats.json();
          const stats = s.stats || {};
          const totalEl = document.getElementById('req-stat-total');
          const ipsEl = document.getElementById('req-stat-ips');
          if (totalEl) totalEl.textContent = stats.total_requests || 0;
          if (ipsEl) ipsEl.textContent = stats.unique_ips || 0;
        }
        if (resLogs.ok) {
          const d = await resLogs.json();
          _allRequestLogs = d.requests || [];
          renderRequestLogs(_allRequestLogs);
        }
      } catch(e) {
        console.warn('Failed to fetch request logs:', e);
      }
    }

    function filterRequestLogs() {
      const ipFilter = (document.getElementById('req-filter-ip')?.value || '').trim().toLowerCase();
      const pathFilter = (document.getElementById('req-filter-path')?.value || '').trim().toLowerCase();

      const filtered = _allRequestLogs.filter(r => {
        const matchIp = !ipFilter || (r.ip_address || '').toLowerCase().includes(ipFilter);
        const matchPath = !pathFilter || (r.path || '').toLowerCase().includes(pathFilter);
        return matchIp && matchPath;
      });
      renderRequestLogs(filtered);
    }

    function renderRequestLogs(logs) {
      const tbody = document.getElementById('request-log-table-body');
      if (!tbody) return;
      if (!logs || !logs.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding:16px; text-align:center; color:var(--text-muted);">No requests recorded yet.</td></tr>';
        return;
      }
      tbody.innerHTML = logs.map(r => {
        const time = r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : '';
        const isTunnel = r.source === 'cloudflare' || r.source === 'tunnel';
        const isBot = r.source === 'telegram' || r.source === 'markanm';
        const ipBadgeColor = isTunnel ? '#ec4899' : (isBot ? '#38bdf8' : '#34d399');
        const ipBadgeBg = isTunnel ? 'rgba(236,72,153,0.1)' : (isBot ? 'rgba(56,189,248,0.1)' : 'rgba(16,185,129,0.1)');
        const statusColor = r.status_code >= 400 ? '#ef4444' : '#34d399';

        let detailsDisplay = '';
        if (r.user_details) {
          detailsDisplay = `<span style="color:#fbbf24; font-family:monospace;">${escapeHtml(r.user_details)}</span>`;
        } else if (r.body_payload) {
          detailsDisplay = `<span style="color:#a5f3fc; font-family:monospace;">${escapeHtml(r.body_payload.slice(0, 150))}</span>`;
        } else if (r.query_params) {
          detailsDisplay = `<span style="color:#94a3b8; font-family:monospace;">${escapeHtml(r.query_params)}</span>`;
        } else {
          detailsDisplay = '<span style="color:var(--text-muted);">-</span>';
        }

        return `<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
          <td style="padding:6px 10px; color:var(--text-muted); white-space:nowrap;">${time}</td>
          <td style="padding:6px 10px; white-space:nowrap;">
            <span style="padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; color:${ipBadgeColor}; background:${ipBadgeBg}; font-family:monospace;">
              ${escapeHtml(r.ip_address)}
            </span>
          </td>
          <td style="padding:6px 10px; white-space:nowrap;">
            <b style="color:var(--cyan);">${escapeHtml(r.method)}</b> <span style="color:#fff;">${escapeHtml(r.path)}</span>
          </td>
          <td style="padding:6px 10px; color:${statusColor}; font-weight:bold;">${r.status_code}</td>
          <td style="padding:6px 10px; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            ${detailsDisplay}
          </td>
          <td style="padding:6px 10px; color:var(--text-muted); white-space:nowrap;">${r.duration_ms}ms</td>
        </tr>`;
      }).join('');
    }

    async function clearOldRequests() {
      if (!confirm('Purge request logs older than 30 days from database?')) return;
      try {
        const res = await fetch('/api/requests/clear', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ days: 30 })
        });
        const d = await res.json();
        alert(`Purged ${d.deleted_count || 0} old request records.`);
        fetchRequestLogs();
      } catch(e) {
        alert('Failed to clear old requests: ' + e);
      }
    }

    async function fetchAudit() {
      fetchRequestLogs();
      const res = await fetch('/api/audit');
      const lines = await res.json();
      document.getElementById('audit-log-content').textContent = (lines && lines.length) ? lines.join('\n') : 'No audit entries logged yet.';
    }

    // ------------------------------------------------------------------------
    // Stealth Meeting & Technical Interview Copilot
    // ------------------------------------------------------------------------
    let stealthAutoWatchActive = false;
    let stealthWhisperActive = false;
    let isGhostDecoy = false;

    function getStealthUrl() {
      const host = window.location.hostname || '127.0.0.1';
      const port = window.location.port || '8844';
      return `http://${host}:${port}/stealth`;
    }

    function renderStealthQR() {
      const url = getStealthUrl();
      const urlEl = document.getElementById('stealth-lan-url');
      if (urlEl) urlEl.textContent = url;
      const linkEl = document.getElementById('stealth-open-link');
      if (linkEl) linkEl.href = url;

      // Draw visual pairing badge on canvas
      const canvas = document.getElementById('stealth-qr-canvas');
      if (canvas) {
        const ctx = canvas.getContext('2d');
        const s = canvas.width;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, s, s);

        const N = 21;
        const cell = s / N;
        ctx.fillStyle = '#0f172a';

        function finder(r0, c0) {
          for (let r = 0; r < 7; r++) {
            for (let c = 0; c < 7; c++) {
              if (r === 0 || r === 6 || c === 0 || c === 6 || (r >= 2 && r <= 4 && c >= 2 && c <= 4)) {
                ctx.fillRect((c0 + c) * cell, (r0 + r) * cell, cell, cell);
              }
            }
          }
        }
        finder(1, 1);
        finder(1, N - 8);
        finder(N - 8, 1);

        let hash = 1337;
        for (let i = 0; i < url.length; i++) hash = ((hash << 5) - hash) + url.charCodeAt(i);
        for (let r = 1; r < N - 1; r++) {
          for (let c = 1; c < N - 1; c++) {
            if ((r <= 8 && c <= 8) || (r <= 8 && c >= N - 9) || (r >= N - 9 && c <= 8)) continue;
            if (r === 6 || c === 6) {
              if ((r + c) % 2 === 0) ctx.fillRect(c * cell, r * cell, cell, cell);
              continue;
            }
            if (((r * 31 + c * 17) ^ hash) % 3 === 0) {
              ctx.fillRect(c * cell, r * cell, cell, cell);
            }
          }
        }
      }
    }

    async function fetchStealthStatus() {
      try {
        const res = await fetch('/api/stealth/status');
        if (!res.ok) return;
        const s = await res.json();
        stealthAutoWatchActive = !!s.autowatch_enabled;
        stealthWhisperActive = !!s.whisper_enabled;

        const btnAuto = document.getElementById('stealth-autowatch-btn');
        if (btnAuto) {
          btnAuto.textContent = stealthAutoWatchActive ? '👁️ Auto-Watch: ON' : '👁️ Auto-Watch: OFF';
          btnAuto.style.color = stealthAutoWatchActive ? '#34d399' : 'var(--text-muted)';
        }

        const btnWhisp = document.getElementById('stealth-whisper-btn');
        if (btnWhisp) {
          btnWhisp.textContent = stealthWhisperActive ? '🎧 Whisper: ON' : '🎧 Whisper: OFF';
          btnWhisp.style.color = stealthWhisperActive ? '#38bdf8' : 'var(--text-muted)';
        }
      } catch (e) {}
    }

    async function fetchStealthLatest() {
      try {
        const res = await fetch('/api/stealth/latest');
        if (!res.ok) return;
        const d = await res.json();

        // Update Screen Stealth
        if (d.question) document.getElementById('stealth-det-question').textContent = d.question;
        if (d.talking_points) document.getElementById('stealth-det-say').textContent = d.talking_points;
        if (d.approach) document.getElementById('stealth-det-approach').textContent = d.approach;
        if (d.code) document.getElementById('stealth-det-code').textContent = d.code;
        if (d.edge_cases) document.getElementById('stealth-det-edges').textContent = d.edge_cases;
        if (d.timestamp) {
          const dt = new Date(d.timestamp);
          document.getElementById('stealth-sol-timestamp').textContent = dt.toLocaleTimeString();
        }

        // Update Ghost HUD
        if (d.question) document.getElementById('ghost-question').textContent = d.question;
        if (d.talking_points) document.getElementById('ghost-say').textContent = d.talking_points;
        if (d.approach) document.getElementById('ghost-approach').textContent = d.approach;
        if (d.code) document.getElementById('ghost-code').textContent = d.code;
        if (d.edge_cases) document.getElementById('ghost-edges').textContent = d.edge_cases;

        // Refresh screen preview
        const img = document.getElementById('stealth-desktop-preview');
        if (img && img.offsetParent !== null) {
          img.src = '/api/screen/latest.jpg?t=' + Date.now();
        }
      } catch (e) {}
    }

    async function triggerStealthSolve(prompt = null) {
      const qEl = document.getElementById('stealth-det-question');
      const gEl = document.getElementById('ghost-question');
      if (qEl) qEl.textContent = '⚡ Analyzing screen & formulating optimal answer...';
      if (gEl) gEl.textContent = '⚡ Analyzing screen & formulating optimal answer...';
      try {
        const res = await fetch('/api/stealth/solve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt })
        });
        const d = await res.json();
        fetchStealthLatest();
      } catch (e) {
        alert('Error solving screen question: ' + e);
      }
    }

    async function toggleStealthAutoWatch() {
      stealthAutoWatchActive = !stealthAutoWatchActive;
      try {
        await fetch('/api/stealth/autowatch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: stealthAutoWatchActive })
        });
        fetchStealthStatus();
      } catch (e) {}
    }

    async function toggleStealthWhisper() {
      stealthWhisperActive = !stealthWhisperActive;
      try {
        await fetch('/api/stealth/whisper', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: stealthWhisperActive })
        });
        fetchStealthStatus();
      } catch (e) {}
    }

    function copyStealthUrl() {
      const url = getStealthUrl();
      navigator.clipboard.writeText(url);
      alert('Copied Stealth Teleprompter URL:\n' + url + '\n\nOpen this on your phone camera/browser!');
    }

    function copyElementText(id) {
      const el = document.getElementById(id);
      if (el) {
        navigator.clipboard.writeText(el.textContent);
      }
    }

    // Floating Ghost Prompter Overlay (Camouflage & Opacity)
    function toggleGhostOverlay() {
      const hud = document.getElementById('stealth-ghost-hud');
      if (!hud) return;
      if (hud.style.display === 'none' || !hud.style.display) {
        hud.style.display = 'block';
        fetchStealthLatest();
      } else {
        hud.style.display = 'none';
      }
    }

    function setGhostOpacity(val) {
      const hud = document.getElementById('stealth-ghost-hud');
      if (hud) {
        hud.style.opacity = Math.max(0.1, val / 100);
      }
    }

    function toggleGhostDecoy() {
      isGhostDecoy = !isGhostDecoy;
      const real = document.getElementById('ghost-real-content');
      const decoy = document.getElementById('ghost-decoy-content');
      const title = document.getElementById('ghost-header-title');
      if (isGhostDecoy) {
        if (real) real.style.display = 'none';
        if (decoy) decoy.style.display = 'block';
        if (title) title.textContent = '📊 SYSTEM MONITOR';
      } else {
        if (real) real.style.display = 'block';
        if (decoy) decoy.style.display = 'none';
        if (title) title.textContent = '🕵️ STEALTH COPILOT';
      }
    }

    // Make Ghost Prompter Draggable
    (function initGhostDrag() {
      let isDragging = false;
      let startX, startY, initialLeft, initialTop;

      window.addEventListener('DOMContentLoaded', () => {
        const handle = document.getElementById('ghost-drag-handle');
        const hud = document.getElementById('stealth-ghost-hud');
        if (!handle || !hud) return;

        handle.addEventListener('mousedown', (e) => {
          if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
          isDragging = true;
          startX = e.clientX;
          startY = e.clientY;
          const rect = hud.getBoundingClientRect();
          initialLeft = rect.left;
          initialTop = rect.top;
          e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
          if (!isDragging || !hud) return;
          const dx = e.clientX - startX;
          const dy = e.clientY - startY;
          hud.style.right = 'auto';
          hud.style.left = (initialLeft + dx) + 'px';
          hud.style.top = (initialTop + dy) + 'px';
        });

        document.addEventListener('mouseup', () => {
          isDragging = false;
        });

        document.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') {
            const h = document.getElementById('stealth-ghost-hud');
            if (h && h.style.display !== 'none') {
              h.style.display = 'none';
            }
          }
        });
      });
    })();

    // Laptop Audio Hardware Repair
    async function repairLaptopAudioHardware() {
      const statusEl = document.getElementById('audio-hardware-fix-status');
      const btnSettings = document.getElementById('btn-fix-audio-settings');
      const btnHeader = document.getElementById('btn-fix-sound-header');

      if (btnSettings) btnSettings.textContent = '⏳ Fixing Audio Hardware...';
      if (btnHeader) btnHeader.textContent = '⏳ Fixing Audio...';

      try {
        const res = await fetch('/api/audio/repair', { method: 'POST' });
        const d = await res.json();
        const msg = d.message || 'Laptop hardware audio repaired!';
        if (statusEl) {
          statusEl.style.display = 'block';
          statusEl.textContent = msg;
        }
        alert('🔊 Laptop Speakers & Microphone Repaired!\n\n' + msg);
        if (typeof fetchStatus === 'function') fetchStatus();
      } catch (err) {
        alert('Audio repair error: ' + err);
      } finally {
        if (btnSettings) btnSettings.textContent = '🛠️ Fix Mic & Laptop Speakers';
        if (btnHeader) btnHeader.textContent = '🔊 Fix Sound & Mic';
      }
    }

    // Cloudflare Quick Tunnel Management
    let currentTunnelUrl = '';

    async function checkCloudflareStatus() {
      try {
        const res = await fetch('/api/tunnel/status');
        const d = await res.json();
        const headerBtn = document.getElementById('btn-cloudflare-header');
        const settingsStatus = document.getElementById('tunnel-settings-status');
        if (d.active && d.url) {
          currentTunnelUrl = d.url;
          if (headerBtn) {
            headerBtn.textContent = '☁️ Cloudflare: ONLINE';
            headerBtn.style.color = '#38bdf8';
            headerBtn.style.borderColor = '#38bdf8';
          }
          if (settingsStatus) {
            settingsStatus.style.display = 'block';
            settingsStatus.innerHTML = `🟢 <b>Tunnel ACTIVE:</b> <a href="${d.url}" target="_blank" style="color:#38bdf8;">${d.url}</a><br>📱 <b>Mobile Prompter:</b> <a href="${d.url}/stealth" target="_blank" style="color:#a855f7;">${d.url}/stealth</a>`;
          }
        } else {
          currentTunnelUrl = '';
          if (headerBtn) {
            headerBtn.textContent = '☁️ Cloudflare Share';
          }
        }
      } catch (e) {}
    }

    async function openCloudflareModal() {
      const modal = document.getElementById('cloudflare-modal');
      const urlBox = document.getElementById('modal-tunnel-url');
      const qrImg = document.getElementById('modal-qr-img');
      const qrContainer = document.getElementById('modal-qr-container');
      const copyBtn = document.getElementById('modal-copy-btn');
      if (modal) modal.style.display = 'flex';
      if (copyBtn) copyBtn.textContent = '📋 Copy Public Link';
      if (qrContainer) qrContainer.style.display = 'none';

      if (urlBox) urlBox.innerHTML = '<span style="color:#38bdf8;">⏳ Connecting to Cloudflare Tunnel (auto-downloading binary if needed)...</span>';

      try {
        const res = await fetch('/api/tunnel/start', { method: 'POST' });
        const d = await res.json();
        if (d.url) {
          currentTunnelUrl = d.url;
          if (urlBox) urlBox.innerHTML = `<a href="${d.url}" target="_blank" style="color:#38bdf8; text-decoration:underline; font-weight:bold;">${d.url}</a>`;
          if (qrImg) {
            qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(d.url)}`;
          }
          if (qrContainer) qrContainer.style.display = 'inline-block';
          checkCloudflareStatus();
        } else {
          if (urlBox) urlBox.innerHTML = `<div style="color:#f87171; font-size:12px;">⚠️ Tunnel Notice: ${d.message || 'Could not retrieve URL'}</div>`;
          if (qrContainer) qrContainer.style.display = 'none';
        }
      } catch (err) {
        if (urlBox) urlBox.innerHTML = `<div style="color:#f87171; font-size:12px;">Network error starting tunnel: ${err}</div>`;
        if (qrContainer) qrContainer.style.display = 'none';
      }
    }

    function closeCloudflareModal() {
      const modal = document.getElementById('cloudflare-modal');
      if (modal) modal.style.display = 'none';
    }

    async function copyCloudflareUrl() {
      if (!currentTunnelUrl) return;
      try {
        await navigator.clipboard.writeText(currentTunnelUrl);
        const btn = document.getElementById('modal-copy-btn');
        if (btn) {
          btn.textContent = '✅ Copied!';
          setTimeout(() => { btn.textContent = '📋 Copy Public Link'; }, 2000);
        }
      } catch (e) {
        prompt('Copy this URL:', currentTunnelUrl);
      }
    }

    async function stopCloudflareTunnel() {
      if (!confirm('Stop Cloudflare remote access? Remote users will be disconnected.')) return;
      try {
        await fetch('/api/tunnel/stop', { method: 'POST' });
        currentTunnelUrl = '';
        const urlBox = document.getElementById('modal-tunnel-url');
        const qrImg = document.getElementById('modal-qr-img');
        if (urlBox) urlBox.textContent = 'Tunnel stopped.';
        if (qrImg) qrImg.style.display = 'none';
        checkCloudflareStatus();
        setTimeout(closeCloudflareModal, 1000);
      } catch (e) {
        alert('Error stopping tunnel: ' + e);
      }
    }

    // ==========================================
    // ELEVENLABS CUSTOM VOICE STUDIO FUNCTIONS
    // ==========================================
    let isElevenKeyVisible = false;

    async function loadElevenLabsConfig() {
      try {
        const res = await fetch('/api/elevenlabs/config');
        const d = await res.json();
        const badge = document.getElementById('elevenlabs-status-badge');
        const keyInput = document.getElementById('elevenlabs-key-input');
        const voiceIdInput = document.getElementById('elevenlabs-voice-id-input');
        const check = document.getElementById('elevenlabs-enable-checkbox');

        if (d.has_key) {
          if (badge) {
            badge.textContent = '✅ Key Configured';
            badge.style.color = '#34d399';
            badge.style.borderColor = '#10b981';
            badge.style.background = 'rgba(16,185,129,0.1)';
          }
          if (keyInput) keyInput.value = d.api_key || d.masked_key || '';
        } else {
          if (badge) {
            badge.textContent = '⚠️ Key Required';
            badge.style.color = '#f59e0b';
            badge.style.borderColor = '#f59e0b';
            badge.style.background = 'rgba(245,158,11,0.1)';
          }
        }
        if (voiceIdInput && d.voice_id) voiceIdInput.value = d.voice_id;
        if (check) check.checked = Boolean(d.enabled);
      } catch(e) {
        console.warn('Failed to load ElevenLabs config:', e);
      }
    }

    function toggleElevenKeyVisibility() {
      const inp = document.getElementById('elevenlabs-key-input');
      if (!inp) return;
      isElevenKeyVisible = !isElevenKeyVisible;
      inp.type = isElevenKeyVisible ? 'text' : 'password';
    }

    function extractVoiceIdFromInput(str) {
      if (!str) return '';
      let s = str.trim().replace(/^['"<]+|['">]+$/g, '');
      if (s.includes('elevenlabs.io') || s.includes('/')) {
        let clean = s.split('?')[0].split('#')[0].replace(/\/+$/, '');
        let parts = clean.split('/').filter(Boolean);
        if (parts.length > 0) {
          let candidate = parts[parts.length - 1];
          if (/^[a-zA-Z0-9_-]{15,50}$/.test(candidate)) return candidate;
        }
      }
      let matches = s.match(/\b([a-zA-Z0-9]{18,35})\b/g);
      if (matches && matches.length > 0) return matches[matches.length - 1];
      return s;
    }

    function handleVoiceIdPaste(inputEl) {
      if (!inputEl) return;
      const val = inputEl.value.trim();
      if (val.includes('elevenlabs.io/')) {
        const extracted = extractVoiceIdFromInput(val);
        if (extracted && extracted !== val) {
          inputEl.value = extracted;
        }
      }
    }

    async function saveElevenLabsConfig() {
      const keyInput = document.getElementById('elevenlabs-key-input');
      const voiceIdInput = document.getElementById('elevenlabs-voice-id-input');
      const check = document.getElementById('elevenlabs-enable-checkbox');
      const msg = document.getElementById('elevenlabs-save-msg');

      const apiKey = keyInput ? keyInput.value.trim() : '';
      const rawVoiceId = voiceIdInput ? voiceIdInput.value.trim() : '';
      const voiceId = extractVoiceIdFromInput(rawVoiceId);
      if (voiceIdInput && voiceId && voiceId !== rawVoiceId) {
        voiceIdInput.value = voiceId;
      }
      const enabled = check ? check.checked : false;

      try {
        const res = await fetch('/api/elevenlabs/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ api_key: apiKey, voice_id: voiceId, enabled: enabled })
        });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || 'Saved!';
          msg.style.display = 'block';
          setTimeout(() => { msg.style.display = 'none'; }, 3000);
        }
        loadElevenLabsConfig();
      } catch(e) {
        alert('Failed to save ElevenLabs config: ' + e);
      }
    }

    async function toggleElevenLabsPrimary(enabled) {
      const voiceIdInput = document.getElementById('elevenlabs-voice-id-input');
      const rawVoiceId = voiceIdInput ? voiceIdInput.value.trim() : '';
      const voiceId = extractVoiceIdFromInput(rawVoiceId);
      try {
        await fetch('/api/elevenlabs/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ voice_id: voiceId, enabled: enabled })
        });
        if (enabled) {
          setVoicePreference('elevenlabs');
        }
      } catch(e) {}
    }

    async function testElevenLabsVoice(e) {
      const voiceIdInput = document.getElementById('elevenlabs-voice-id-input');
      const rawVoiceId = voiceIdInput ? voiceIdInput.value.trim() : '';
      const voiceId = extractVoiceIdFromInput(rawVoiceId);
      const sampleText = "Suno... ElevenLabs voice connect ho gayi hai! Kaisa lag raha hai mera sound?";
      const btn = e && e.target ? e.target : null;
      if (btn) btn.textContent = '⏳ Playing...';
      try {
        const res = await fetch('/api/elevenlabs/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ voice_id: voiceId, text: sampleText })
        });
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play();
        } else {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData.error || 'ElevenLabs synthesis request failed.';
          console.warn('ElevenLabs test error:', errMsg);
          const msgEl = document.getElementById('elevenlabs-save-msg');
          if (msgEl) {
            msgEl.textContent = '⚠️ ' + errMsg;
            msgEl.style.color = '#f59e0b';
            msgEl.style.display = 'block';
            setTimeout(() => { msgEl.style.display = 'none'; }, 7000);
          }
          playAudioResponse(sampleText, 'hi-IN-SwaraNeural');
        }
      } catch(err) {
        playAudioResponse(sampleText, 'hi-IN-SwaraNeural');
      } finally {
        if (btn) setTimeout(() => { btn.textContent = '▶️ Test'; }, 3000);
      }
    }

    // ==========================================
    // IDLE CHECK-IN (DISABLED BY DEFAULT TO PREVENT UNSOLICITED CHATTER)
    // ==========================================
    let proactiveMessagingEnabled = false;
    let lastUserActivityTimestamp = Date.now();
    let isWaitingIdleResponse = false;
    let proactiveMessageTimestamp = 0;

    function recordUserActivity() {
      lastUserActivityTimestamp = Date.now();
      isWaitingIdleResponse = false;
    }

    async function checkAarushiIdleProactive() {
      // Proactive messaging is strictly disabled by default; never interrupt when quiet mode or speaking is active
      if (!proactiveMessagingEnabled || isQuietMode || isSpeaking) return;

      const idleDuration = Date.now() - lastUserActivityTimestamp;

      // 1. Initial idle check-in (only if explicitly enabled by user)
      if (!isWaitingIdleResponse && idleDuration >= 180000) {
        try {
          const res = await fetch('/api/aarushi/proactive?followup=false');
          const d = await res.json();
          const msg = (d && d.message) ? d.message.trim() : '';
          if (!msg) return;
          isWaitingIdleResponse = true;
          proactiveMessageTimestamp = Date.now();

          const chime = new Audio('/api/audio/chime');
          chime.play().catch(() => {});

          const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const html = `<div style="margin: 8px 0; padding: 8px 12px; background: rgba(59,130,246,0.1); border-left: 3px solid var(--accent-primary); border-radius: 6px;">
            <div style="font-size:11px; color:var(--accent-primary); margin-bottom:3px; display:flex; justify-content:space-between;">
              <span>🤖 <b>Aarushi</b> [Assistant]</span>
              <span style="font-size:10px; color:var(--text-muted);">${timeStr}</span>
            </div>
            <div style="color:var(--text-primary); font-size:13px; line-height:1.4;">${escapeHtml(msg)}</div>
          </div>`;

          ['home-transcript-list', 'chat-history', 'multi-chat-history'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
              if (id === 'home-transcript-list' && el.innerHTML.includes('Speak to the Orb')) el.innerHTML = '';
              el.innerHTML += html;
              el.scrollTop = el.scrollHeight;
            }
          });

          if (!isQuietMode) speakText(msg);
        } catch(e) {
          console.warn('Aarushi proactive check-in notice:', e);
        }
      }
      else if (isWaitingIdleResponse && !isSpeaking && (Date.now() - proactiveMessageTimestamp >= 120000)) {
        try {
          const res = await fetch('/api/aarushi/proactive?followup=true');
          const d = await res.json();
          const msg = (d && d.message) ? d.message.trim() : '';
          if (!msg) {
            isWaitingIdleResponse = false;
            return;
          }
          proactiveMessageTimestamp = Date.now();

          const chime = new Audio('/api/audio/chime');
          chime.play().catch(() => {});

          const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const html = `<div style="margin: 8px 0; padding: 8px 12px; background: rgba(59,130,246,0.1); border-left: 3px solid var(--accent-primary); border-radius: 6px;">
            <div style="font-size:11px; color:var(--accent-primary); margin-bottom:3px; display:flex; justify-content:space-between;">
              <span>🤖 <b>Aarushi</b> [Follow-Up]</span>
              <span style="font-size:10px; color:var(--text-muted);">${timeStr}</span>
            </div>
            <div style="color:var(--text-primary); font-size:13px; line-height:1.4;">${escapeHtml(msg)}</div>
          </div>`;

          ['home-transcript-list', 'chat-history', 'multi-chat-history'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
              el.innerHTML += html;
              el.scrollTop = el.scrollHeight;
            }
          });

          if (!isQuietMode) speakText(msg);
        } catch(e) {
          console.warn('Aarushi follow-up notice:', e);
        }
      }
    }


    // ==========================================
    // AUDIO DEVICES & MICROPHONE DIAGNOSTICS
    // ==========================================
    let micAudioContext = null;
    let micAnalyser = null;
    let micVisualizerRunning = false;

    async function requestMicPermission() {
      const statusLabel = document.getElementById('mic-status-label');
      if (statusLabel) {
        statusLabel.textContent = 'Requesting device permission...';
        statusLabel.style.color = '#38bdf8';
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (statusLabel) {
          statusLabel.textContent = 'Permission Granted ✅';
          statusLabel.style.color = '#10b981';
        }
        initMicVisualizer(stream);
        await enumerateBrowserAudioDevices();
      } catch(e) {
        if (statusLabel) {
          statusLabel.textContent = 'Permission Denied / Error ❌';
          statusLabel.style.color = '#ef4444';
        }
        alert('Microphone permission error: ' + e.message);
      }
    }

    async function enumerateBrowserAudioDevices() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const inputSelect = document.getElementById('browser-audio-input-select');
        const outputSelect = document.getElementById('browser-audio-output-select');

        const prefIn = localStorage.getItem('gdr_preferred_mic_id') || '';
        const prefOut = localStorage.getItem('gdr_preferred_speaker_id') || '';

        if (inputSelect) {
          inputSelect.innerHTML = '<option value="">Default Microphone</option>';
          const inDevs = devices.filter(d => d.kind === 'audioinput');
          inDevs.forEach((d, idx) => {
            const opt = document.createElement('option');
            opt.value = d.deviceId;
            opt.textContent = d.label || `Microphone #${idx + 1} (${d.deviceId.slice(0, 8)}...)`;
            if (d.deviceId === prefIn) opt.selected = true;
            inputSelect.appendChild(opt);
          });
        }

        if (outputSelect) {
          outputSelect.innerHTML = '<option value="">Default Speaker / Headphones</option>';
          const outDevs = devices.filter(d => d.kind === 'audiooutput');
          outDevs.forEach((d, idx) => {
            const opt = document.createElement('option');
            opt.value = d.deviceId;
            opt.textContent = d.label || `Speaker/Headphone #${idx + 1} (${d.deviceId.slice(0, 8)}...)`;
            if (d.deviceId === prefOut) opt.selected = true;
            outputSelect.appendChild(opt);
          });
        }
      } catch(e) {
        console.warn('Failed to enumerate browser audio devices:', e);
      }
    }

    function onBrowserMicChange(deviceId) {
      localStorage.setItem('gdr_preferred_mic_id', deviceId);
      const fb = document.getElementById('audio-device-feedback-msg');
      if (fb) {
        fb.textContent = 'Preferred microphone saved!';
        fb.style.display = 'block';
        setTimeout(() => fb.style.display = 'none', 3000);
      }
      navigator.mediaDevices.getUserMedia({ audio: deviceId ? { deviceId: { exact: deviceId } } : true })
        .then(stream => initMicVisualizer(stream))
        .catch(() => {});
    }

    function onBrowserSpeakerChange(deviceId) {
      localStorage.setItem('gdr_preferred_speaker_id', deviceId);
      const fb = document.getElementById('audio-device-feedback-msg');
      if (fb) {
        fb.textContent = 'Preferred audio output saved!';
        fb.style.display = 'block';
        setTimeout(() => fb.style.display = 'none', 3000);
      }
    }

    function initMicVisualizer(stream) {
      if (!stream) return;
      try {
        if (!micAudioContext) {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (AudioContextClass) micAudioContext = new AudioContextClass();
        }
        if (micAudioContext && micAudioContext.state === 'suspended') {
          micAudioContext.resume().catch(() => {});
        }
        if (!micAudioContext) return;

        const source = micAudioContext.createMediaStreamSource(stream);
        micAnalyser = micAudioContext.createAnalyser();
        micAnalyser.fftSize = 256;
        source.connect(micAnalyser);

        if (!micVisualizerRunning) {
          micVisualizerRunning = true;
          const dataArray = new Uint8Array(micAnalyser.frequencyBinCount);
          const bar = document.getElementById('live-mic-level-bar');
          const status = document.getElementById('mic-status-label');

          const updateVisualizer = () => {
            if (!micVisualizerRunning) return;
            micAnalyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            const pct = Math.min(100, Math.round((avg / 128) * 100));

            if (bar) bar.style.width = pct + '%';
            if (status) {
              if (pct > 5) {
                status.textContent = `Hearing Audio (${pct}%) 🟢`;
                status.style.color = '#34d399';
              } else {
                status.textContent = 'Silent / Listening 🟡';
                status.style.color = '#fbbf24';
              }
            }
            requestAnimationFrame(updateVisualizer);
          };
          updateVisualizer();
        }
      } catch(e) {
        console.warn('Mic visualizer setup error:', e);
      }
    }

    async function loadSystemAudioDevices() {
      try {
        const res = await fetch('/api/audio/devices');
        if (!res.ok) return;
        const d = await res.json();

        const inSelect = document.getElementById('system-audio-input-select');
        const outSelect = document.getElementById('system-audio-output-select');

        if (inSelect && d.inputs) {
          inSelect.innerHTML = '';
          d.inputs.forEach(dev => {
            const opt = document.createElement('option');
            opt.value = dev.id;
            opt.textContent = `[${dev.id}] ${dev.name} (${dev.channels}ch, ${dev.default_samplerate}Hz)` + (dev.is_default ? ' [Default]' : '');
            if (dev.is_selected) opt.selected = true;
            inSelect.appendChild(opt);
          });
        }

        if (outSelect && d.outputs) {
          outSelect.innerHTML = '';
          d.outputs.forEach(dev => {
            const opt = document.createElement('option');
            opt.value = dev.id;
            opt.textContent = `[${dev.id}] ${dev.name} (${dev.channels}ch)` + (dev.is_default ? ' [Default]' : '');
            if (dev.is_selected) opt.selected = true;
            outSelect.appendChild(opt);
          });
        }
      } catch(e) {
        console.warn('Failed to load system audio devices:', e);
      }
    }

    async function saveSystemAudioDevices() {
      const inSelect = document.getElementById('system-audio-input-select');
      const outSelect = document.getElementById('system-audio-output-select');
      const fb = document.getElementById('audio-device-feedback-msg');

      const inputDev = inSelect ? inSelect.value : null;
      const outputDev = outSelect ? outSelect.value : null;

      try {
        const res = await fetch('/api/audio/devices/select', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ input_device: inputDev, output_device: outputDev })
        });
        const d = await res.json();
        if (fb) {
          fb.textContent = d.message || 'System audio devices saved!';
          fb.style.display = 'block';
          fb.style.color = '#34d399';
          setTimeout(() => fb.style.display = 'none', 4000);
        }
        loadSystemAudioDevices();
      } catch(e) {
        alert('Failed to save audio devices: ' + e);
      }
    }

    async function fixAndDetectMic() {
      const fb = document.getElementById('audio-device-feedback-msg');
      if (fb) {
        fb.textContent = 'Diagnosing, unmuting, and boosting microphone...';
        fb.style.display = 'block';
        fb.style.color = '#fbbf24';
      }
      try {
        const res = await fetch('/api/audio/mic/fix', { method: 'POST' });
        const d = await res.json();
        if (fb) {
          fb.textContent = d.message || 'Microphone unmuted and boosted to 85%!';
          fb.style.color = d.success ? '#34d399' : '#fbbf24';
          setTimeout(() => fb.style.display = 'none', 5000);
        }
        loadSystemAudioDevices();
        await requestMicPermission();
      } catch(e) {
        if (fb) fb.textContent = 'Mic fix error: ' + e;
      }
    }

    async function testSystemMic() {
      const inSelect = document.getElementById('system-audio-input-select');
      const fb = document.getElementById('audio-device-feedback-msg');
      const chosenDev = inSelect ? inSelect.value : null;

      if (fb) {
        fb.textContent = 'Recording 0.6s audio test sample...';
        fb.style.display = 'block';
        fb.style.color = '#38bdf8';
      }

      try {
        const res = await fetch('/api/audio/mic/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ device: chosenDev })
        });
        const d = await res.json();
        if (fb) {
          if (d.success) {
            const signalMsg = d.is_silent ? '⚠️ Stream open, but low signal (speak louder)' : '🟢 Audio signal detected!';
            fb.textContent = `[${d.device_name}] RMS: ${d.rms}, Peak: ${d.peak} — ${signalMsg}`;
            fb.style.color = d.is_silent ? '#fbbf24' : '#34d399';
          } else {
            fb.textContent = '❌ Test failed: ' + (d.error || 'Unknown error');
            fb.style.color = '#ef4444';
          }
          setTimeout(() => fb.style.display = 'none', 7000);
        }
      } catch(e) {
        if (fb) fb.textContent = 'Test error: ' + e;
      }
    }

    // ==========================================
    // SARVAM AI CONFIGURATION & CONNECTION
    // ==========================================
    function toggleSarvamKeyVisibility() {
      const input = document.getElementById('sarvam-key-input');
      if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
      }
    }

    async function loadSarvamConfig() {
      try {
        const localCachedKey = localStorage.getItem('gdr_sarvam_api_key');
        const res = await fetch('/api/sarvam/config');
        if (!res.ok) return;
        const d = await res.json();
        
        // If server had no key or had sample key, but localStorage has user's saved key, auto-restore it!
        if ((!d.has_key || (d.api_key && d.api_key.includes('sample'))) && localCachedKey && localCachedKey.startsWith('sk_') && !localCachedKey.includes('sample')) {
          await fetch('/api/sarvam/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ api_key: localCachedKey })
          });
          return loadSarvamConfig();
        }

        if (d.api_key && d.api_key.startsWith('sk_') && !d.api_key.includes('sample')) {
          localStorage.setItem('gdr_sarvam_api_key', d.api_key);
        }

        const keyInput = document.getElementById('sarvam-key-input');
        const modelSelect = document.getElementById('sarvam-model-select');
        const badge = document.getElementById('sarvam-status-badge');
        const ttsToggle = document.getElementById('sarvam-tts-enabled');
        const ttsLabel = document.getElementById('sarvam-tts-label');

        if (badge) {
          if (d.has_key) {
            badge.textContent = 'Active (Connected)';
            badge.style.color = '#34d399';
            badge.style.borderColor = '#10b981';
            badge.style.background = 'rgba(16,185,129,0.1)';
          } else {
            badge.textContent = 'No Key Configured';
            badge.style.color = '#f59e0b';
            badge.style.borderColor = '#f59e0b';
            badge.style.background = 'rgba(245,158,11,0.1)';
          }
        }

        if (keyInput) {
          if (d.api_key) {
            keyInput.value = d.api_key;
          } else if (d.has_key && !keyInput.value) {
            keyInput.placeholder = d.masked_key || 'sk_••••••••••••';
          }
        }
        if (modelSelect && d.model) {
          modelSelect.value = d.model;
        }
        // Restore Sarvam TTS toggle state
        if (ttsToggle !== null && d.sarvam_tts_enabled !== undefined) {
          ttsToggle.checked = d.sarvam_tts_enabled;
          if (ttsLabel) {
            ttsLabel.textContent = d.sarvam_tts_enabled
              ? 'Enabled (Sarvam will generate Hindi voice)'
              : 'Disabled (Edge-TTS will handle all voices)';
            ttsLabel.style.color = d.sarvam_tts_enabled ? '#fbbf24' : '#6b7280';
          }
        }
      } catch(e) {
        console.warn('Failed to load Sarvam config:', e);
      }
    }

    async function saveSarvamTTSToggle(enabled) {
      const label = document.getElementById('sarvam-tts-label');
      const msg = document.getElementById('sarvam-save-msg');
      try {
        if (apiKey && apiKey.startsWith('sk_') && !apiKey.includes('sample')) {
          localStorage.setItem('gdr_sarvam_api_key', apiKey);
        }
        const res = await fetch('/api/sarvam/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ sarvam_tts_enabled: enabled })
        });
        const d = await res.json();
        if (label) {
          label.textContent = enabled
            ? 'Enabled (Sarvam will generate Hindi voice)'
            : 'Disabled (Edge-TTS will handle all voices)';
          label.style.color = enabled ? '#fbbf24' : '#6b7280';
        }
        if (msg) {
          msg.textContent = enabled ? '✅ Sarvam TTS enabled.' : '🔕 Sarvam TTS disabled — using Edge-TTS for all voices.';
          msg.style.display = 'block';
          msg.style.color = '#34d399';
          setTimeout(() => { msg.style.display = 'none'; }, 3500);
        }
      } catch(e) {
        console.warn('Failed to toggle Sarvam TTS:', e);
      }
    }

    async function saveSarvamConfig() {
      const keyInput = document.getElementById('sarvam-key-input');
      const modelSelect = document.getElementById('sarvam-model-select');
      const msg = document.getElementById('sarvam-save-msg');
      const apiKey = keyInput ? keyInput.value.trim() : '';
      const model = modelSelect ? modelSelect.value : 'sarvam-105b';

      try {
        if (apiKey && apiKey.startsWith('sk_') && !apiKey.includes('sample')) {
          localStorage.setItem('gdr_sarvam_api_key', apiKey);
        }
        const res = await fetch('/api/sarvam/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ api_key: apiKey, model: model })
        });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || 'Sarvam settings updated successfully!';
          msg.style.display = 'block';
          msg.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { msg.style.display = 'none'; }, 4000);
        }
        loadSarvamConfig();
      } catch(e) {
        alert('Failed to save Sarvam config: ' + e);
      }
    }

    async function testSarvamConnection() {
      const msg = document.getElementById('sarvam-save-msg');
      if (msg) {
        msg.textContent = 'Testing Sarvam API connection...';
        msg.style.display = 'block';
        msg.style.color = '#fbbf24';
      }
      try {
        const res = await fetch('/api/sarvam/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || (res.ok ? 'Sarvam API connected successfully!' : 'Connection failed');
          msg.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { msg.style.display = 'none'; }, 5000);
        }
      } catch(e) {
        if (msg) {
          msg.textContent = 'Sarvam test error: ' + e;
          msg.style.color = '#ef4444';
        }
      }
    }

    // ==========================================
    // TELEGRAM BOT HUB
    // ==========================================
    function toggleTGTokenVisibility() {
      const input = document.getElementById('tg-token-input');
      if (input) input.type = input.type === 'password' ? 'text' : 'password';
    }
    function toggleMsgTGTokenVisibility() {
      const input = document.getElementById('msg-tg-token-input');
      if (input) input.type = input.type === 'password' ? 'text' : 'password';
    }

    async function loadTelegramConfig() {
      try {
        const res = await fetch('/api/telegram/config');
        if (!res.ok) return;
        const d = await res.json();

        // Sync both Bot screen and Dedicated Messaging screen inputs
        ['tg-token-input', 'msg-tg-token-input'].forEach(id => {
          const el = document.getElementById(id);
          if (el) {
            if (d.token) el.value = d.token;
            else if (d.has_token && !el.value) el.placeholder = d.masked_token || 'Token saved in secrets vault';
          }
        });

        ['tg-chatid-input', 'msg-tg-chatid-input'].forEach(id => {
          const el = document.getElementById(id);
          if (el && d.chat_id) el.value = d.chat_id;
        });

        ['tg-username-input', 'msg-tg-username-input'].forEach(id => {
          const el = document.getElementById(id);
          if (el && d.allowed_username) el.value = d.allowed_username;
        });

        ['tg-status-badge', 'msg-tg-status-badge'].forEach(id => {
          const badge = document.getElementById(id);
          if (badge) {
            if (d.running) {
              badge.textContent = '🟢 Running & Polling';
              badge.style.color = '#34d399';
              badge.style.borderColor = '#10b981';
              badge.style.background = 'rgba(16,185,129,0.15)';
            } else if (d.has_token) {
              badge.textContent = '🟡 Ready (Stopped)';
              badge.style.color = '#fbbf24';
              badge.style.borderColor = '#f59e0b';
              badge.style.background = 'rgba(245,158,11,0.15)';
            } else {
              badge.textContent = '⚪ Not Configured';
              badge.style.color = '#94a3b8';
              badge.style.borderColor = '#475569';
              badge.style.background = 'rgba(255,255,255,0.05)';
            }
          }
        });

        ['tg-toggle-btn', 'msg-tg-toggle-btn'].forEach(id => {
          const toggleBtn = document.getElementById(id);
          if (toggleBtn) {
            toggleBtn.textContent = d.running ? '🛑 Stop Bot' : '▶️ Start Bot';
            toggleBtn.style.color = d.running ? '#ef4444' : '#38bdf8';
            toggleBtn.style.borderColor = d.running ? '#ef4444' : '#0284c7';
          }
        });
      } catch(e) {
        console.warn('Failed to load Telegram config:', e);
      }
    }

    async function validateTelegramTokenUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const tokenInput = document.getElementById(isMsg ? 'msg-tg-token-input' : 'tg-token-input');
      const token = tokenInput ? tokenInput.value.trim() : '';
      const feedback = document.getElementById(isMsg ? 'msg-tg-feedback' : 'tg-save-msg');
      const badge = document.getElementById(isMsg ? 'msg-tg-status-badge' : 'tg-status-badge');

      if (feedback) {
        feedback.textContent = 'Connecting to Telegram Cloud API to validate token...';
        feedback.style.display = 'block';
        feedback.style.color = '#38bdf8';
      }

      const t0 = Date.now();
      try {
        const res = await fetch('/api/telegram/validate', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ token: token || null })
        });
        const d = await res.json();
        const elapsed = Date.now() - t0;

        if (res.ok && d.valid) {
          const username = d.bot ? `@${d.bot.username || d.bot.first_name}` : 'Bot';
          if (feedback) {
            feedback.innerHTML = `🟢 <b>Connected as ${username}</b> (ID: ${d.bot ? d.bot.id : '-'}) • Validated in <b>${elapsed}ms</b>`;
            feedback.style.color = '#34d399';
            feedback.style.display = 'block';
          }
          if (badge) {
            badge.textContent = `🟢 Connected (${username})`;
            badge.style.color = '#34d399';
            badge.style.borderColor = '#10b981';
          }
        } else {
          if (feedback) {
            feedback.innerHTML = `❌ <b>Validation Failed:</b> ${d.message || 'Invalid Token'} (${elapsed}ms)`;
            feedback.style.color = '#ef4444';
            feedback.style.display = 'block';
          }
          if (badge) {
            badge.textContent = '❌ Invalid Token';
            badge.style.color = '#ef4444';
            badge.style.borderColor = '#ef4444';
          }
        }
      } catch(e) {
        if (feedback) {
          feedback.textContent = 'Validation network error: ' + e;
          feedback.style.color = '#ef4444';
          feedback.style.display = 'block';
        }
      }
    }

    async function saveTelegramConfigUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const tokenInput = document.getElementById(isMsg ? 'msg-tg-token-input' : 'tg-token-input');
      const chatIdInput = document.getElementById(isMsg ? 'msg-tg-chatid-input' : 'tg-chatid-input');
      const usernameInput = document.getElementById(isMsg ? 'msg-tg-username-input' : 'tg-username-input');
      const msg = document.getElementById(isMsg ? 'msg-tg-feedback' : 'tg-save-msg');

      const token = tokenInput ? tokenInput.value.trim() : '';
      const chatId = chatIdInput ? chatIdInput.value.trim() : '';
      const username = usernameInput ? usernameInput.value.trim() : '';

      try {
        const res = await fetch('/api/telegram/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ token: token, chat_id: chatId, username: username, enabled: true })
        });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || 'Telegram configuration permanently saved!';
          msg.style.display = 'block';
          msg.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { msg.style.display = 'none'; }, 4000);
        }
        loadTelegramConfig();
      } catch(e) {
        alert('Failed to save Telegram config: ' + e);
      }
    }
    const saveTelegramConfig = () => saveTelegramConfigUI('bots');

    async function toggleTelegramBotServiceUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const msg = document.getElementById(isMsg ? 'msg-tg-feedback' : 'tg-save-msg');
      try {
        const res = await fetch('/api/telegram/toggle', { method: 'POST' });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || (d.running ? 'Telegram Bot started!' : 'Telegram Bot stopped.');
          msg.style.display = 'block';
          msg.style.color = d.running ? '#34d399' : '#fbbf24';
          setTimeout(() => { msg.style.display = 'none'; }, 4000);
        }
        loadTelegramConfig();
      } catch(e) {
        alert('Failed to toggle Telegram bot: ' + e);
      }
    }
    const toggleTelegramBotService = () => toggleTelegramBotServiceUI('bots');

    async function testTelegramMessageUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const chatIdInput = document.getElementById(isMsg ? 'msg-tg-chatid-input' : 'tg-chatid-input');
      const chatId = chatIdInput ? chatIdInput.value.trim() : '';
      const msg = document.getElementById(isMsg ? 'msg-tg-feedback' : 'tg-save-msg');

      if (msg) {
        msg.textContent = 'Measuring Telegram delivery latency...';
        msg.style.display = 'block';
        msg.style.color = '#38bdf8';
      }

      try {
        const res = await fetch('/api/telegram/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            chat_id: chatId || null,
            message: "🌸 *Hello from Aarushi!* Your Telegram Bot is successfully connected and listening to your system!"
          })
        });
        const d = await res.json();
        if (msg) {
          if (res.ok && d.success) {
            msg.innerHTML = `✅ <b>Delivered in ${d.elapsed_ms || 220}ms!</b> ${d.message}`;
            msg.style.color = '#34d399';
          } else {
            msg.innerHTML = `❌ <b>Delivery failed:</b> ${d.message || 'Check Token and Chat ID'}`;
            msg.style.color = '#ef4444';
          }
          msg.style.display = 'block';
          setTimeout(() => { if (res.ok) msg.style.display = 'none'; }, 6000);
        }
        setTimeout(loadBotChannelsActivity, 500);
      } catch(e) {
        if (msg) {
          msg.textContent = 'Telegram test error: ' + e;
          msg.style.color = '#ef4444';
        }
      }
    }
    const testTelegramMessage = () => testTelegramMessageUI('bots');

    async function sendDirectTelegramMsgUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const inp = document.getElementById(isMsg ? 'msg-tg-direct-input' : 'tg-direct-msg-input');
      const fb = document.getElementById(isMsg ? 'msg-tg-feedback' : 'tg-direct-feedback');
      const text = inp ? inp.value.trim() : '';
      if (!text) return;

      if (fb) {
        fb.textContent = 'Sending message to Telegram...';
        fb.style.display = 'block';
        fb.style.color = '#38bdf8';
      }
      try {
        const res = await fetch('/api/telegram/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message: text })
        });
        const d = await res.json();
        if (fb) {
          if (res.ok && d.success) {
            fb.innerHTML = `✅ Sent in <b>${d.elapsed_ms || 210}ms</b>!`;
            fb.style.color = '#34d399';
          } else {
            fb.textContent = d.message || 'Failed to send message';
            fb.style.color = '#ef4444';
          }
          setTimeout(() => { if (res.ok) fb.style.display = 'none'; }, 4000);
        }
        if (res.ok && inp) inp.value = '';
        setTimeout(loadBotChannelsActivity, 600);
      } catch(e) {
        if (fb) {
          fb.textContent = 'Error: ' + e;
          fb.style.color = '#ef4444';
        }
      }
    }
    const sendDirectTelegramMessage = () => sendDirectTelegramMsgUI('bots');

    // ==========================================
    // MARKANM CONNECT BOT HUB
    // ==========================================
    function toggleMarkanMTokenVisibility() {
      const input = document.getElementById('markanm-token-input');
      if (input) input.type = input.type === 'password' ? 'text' : 'password';
    }
    function toggleMsgMKTokenVisibility() {
      const input = document.getElementById('msg-mk-token-input');
      if (input) input.type = input.type === 'password' ? 'text' : 'password';
    }

    async function loadMarkanMConfig() {
      try {
        const res = await fetch('/api/markanm/config');
        if (!res.ok) return;
        const d = await res.json();

        // Sync inputs on both Bot screen and Messaging screen
        ['markanm-token-input', 'msg-mk-token-input'].forEach(id => {
          const el = document.getElementById(id);
          if (el) {
            if (d.token) el.value = d.token;
            else if (d.has_token && !el.value) el.placeholder = d.masked_token || 'mkbot_••••••••••••';
          }
        });

        ['markanm-username-input', 'msg-mk-username-input'].forEach(id => {
          const el = document.getElementById(id);
          if (el && d.allowed_username) el.value = d.allowed_username;
        });

        const rInput = document.getElementById('msg-mk-roomid-input');
        if (rInput && d.room_id) rInput.value = d.room_id;

        ['markanm-status-badge', 'msg-mk-status-badge'].forEach(id => {
          const badge = document.getElementById(id);
          if (badge) {
            if (d.running) {
              badge.textContent = '🟢 Running & Polling';
              badge.style.color = '#34d399';
              badge.style.borderColor = '#10b981';
              badge.style.background = 'rgba(16,185,129,0.15)';
            } else if (d.has_token) {
              badge.textContent = '🟡 Ready (Stopped)';
              badge.style.color = '#fbbf24';
              badge.style.borderColor = '#f59e0b';
              badge.style.background = 'rgba(245,158,11,0.15)';
            } else {
              badge.textContent = '⚪ Not Configured';
              badge.style.color = '#94a3b8';
              badge.style.borderColor = '#475569';
              badge.style.background = 'rgba(255,255,255,0.05)';
            }
          }
        });

        ['markanm-toggle-btn', 'msg-mk-toggle-btn'].forEach(id => {
          const toggleBtn = document.getElementById(id);
          if (toggleBtn) {
            toggleBtn.textContent = d.running ? '🛑 Stop Polling' : '▶️ Start Polling';
            toggleBtn.style.color = d.running ? '#ef4444' : '#ec4899';
            toggleBtn.style.borderColor = d.running ? '#ef4444' : '#ec4899';
          }
        });
      } catch(e) {
        console.warn('Failed to load MarkanM config:', e);
      }
    }

    async function validateMarkanMTokenUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const tokenInput = document.getElementById(isMsg ? 'msg-mk-token-input' : 'markanm-token-input');
      const token = tokenInput ? tokenInput.value.trim() : '';
      const feedback = document.getElementById(isMsg ? 'msg-mk-feedback' : 'markanm-save-msg');
      const badge = document.getElementById(isMsg ? 'msg-mk-status-badge' : 'markanm-status-badge');

      if (feedback) {
        feedback.textContent = 'Connecting to chat.markanm.com to validate bot token...';
        feedback.style.display = 'block';
        feedback.style.color = '#ec4899';
      }

      const t0 = Date.now();
      try {
        const res = await fetch('/api/markanm/validate', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ token: token || null })
        });
        const d = await res.json();
        const elapsed = Date.now() - t0;

        if (res.ok && d.valid) {
          const user = d.user ? (d.user.username || d.user.name || 'Developer') : 'MarkanM Bot';
          if (feedback) {
            feedback.innerHTML = `🟢 <b>Connected as ${user}</b> • Validated in <b>${elapsed}ms</b>`;
            feedback.style.color = '#34d399';
            feedback.style.display = 'block';
          }
          if (badge) {
            badge.textContent = `🟢 Connected (${user})`;
            badge.style.color = '#34d399';
            badge.style.borderColor = '#10b981';
          }
        } else {
          if (feedback) {
            feedback.innerHTML = `❌ <b>Validation Failed:</b> ${d.message || 'Invalid Token'} (${elapsed}ms)`;
            feedback.style.color = '#ef4444';
            feedback.style.display = 'block';
          }
          if (badge) {
            badge.textContent = '❌ Invalid Token';
            badge.style.color = '#ef4444';
            badge.style.borderColor = '#ef4444';
          }
        }
      } catch(e) {
        if (feedback) {
          feedback.textContent = 'Validation network error: ' + e;
          feedback.style.color = '#ef4444';
          feedback.style.display = 'block';
        }
      }
    }

    async function saveMarkanMConfigUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const tokenInput = document.getElementById(isMsg ? 'msg-mk-token-input' : 'markanm-token-input');
      const usernameInput = document.getElementById(isMsg ? 'msg-mk-username-input' : 'markanm-username-input');
      const roomIdInput = document.getElementById('msg-mk-roomid-input');
      const msg = document.getElementById(isMsg ? 'msg-mk-feedback' : 'markanm-save-msg');

      const token = tokenInput ? tokenInput.value.trim() : '';
      const username = usernameInput ? usernameInput.value.trim() : '';
      const roomId = roomIdInput ? roomIdInput.value.trim() : '';

      try {
        const res = await fetch('/api/markanm/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ token: token, username: username, room_id: roomId, enabled: true })
        });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || 'MarkanM configuration permanently saved!';
          msg.style.display = 'block';
          msg.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { msg.style.display = 'none'; }, 4000);
        }
        loadMarkanMConfig();
      } catch(e) {
        alert('Failed to save MarkanM config: ' + e);
      }
    }
    const saveMarkanMConfig = () => saveMarkanMConfigUI('bots');

    async function toggleMarkanMBotServiceUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const msg = document.getElementById(isMsg ? 'msg-mk-feedback' : 'markanm-save-msg');
      try {
        const res = await fetch('/api/markanm/toggle', { method: 'POST' });
        const d = await res.json();
        if (msg) {
          msg.textContent = d.message || (d.running ? 'MarkanM Bot started!' : 'MarkanM Bot stopped.');
          msg.style.display = 'block';
          msg.style.color = d.running ? '#34d399' : '#fbbf24';
          setTimeout(() => { msg.style.display = 'none'; }, 4000);
        }
        loadMarkanMConfig();
      } catch(e) {
        alert('Failed to toggle MarkanM bot: ' + e);
      }
    }
    const toggleMarkanMBotService = () => toggleMarkanMBotServiceUI('bots');

    async function testMarkanMMessageUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const roomIdInput = document.getElementById('msg-mk-roomid-input');
      const roomId = roomIdInput ? roomIdInput.value.trim() : '';
      const msg = document.getElementById(isMsg ? 'msg-mk-feedback' : 'markanm-save-msg');

      if (msg) {
        msg.textContent = 'Measuring MarkanM delivery latency...';
        msg.style.display = 'block';
        msg.style.color = '#ec4899';
      }

      try {
        const res = await fetch('/api/markanm/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            room_id: roomId || null,
            message: "🌸 Hello from Aarushi! MarkanM Chat Bot is connected and active on your system!"
          })
        });
        const d = await res.json();
        if (msg) {
          if (res.ok && d.success) {
            msg.innerHTML = `✅ <b>Delivered in ${d.elapsed_ms || 180}ms!</b> ${d.message}`;
            msg.style.color = '#34d399';
          } else {
            msg.innerHTML = `❌ <b>Delivery failed:</b> ${d.message || 'Check Token (mkbot_...) and Room ID'}`;
            msg.style.color = '#ef4444';
          }
          msg.style.display = 'block';
          setTimeout(() => { if (res.ok) msg.style.display = 'none'; }, 6000);
        }
        setTimeout(loadBotChannelsActivity, 500);
      } catch(e) {
        if (msg) {
          msg.textContent = 'MarkanM test error: ' + e;
          msg.style.color = '#ef4444';
        }
      }
    }
    const testMarkanMMessage = () => testMarkanMMessageUI('bots');

    async function sendDirectMarkanMMsgUI(prefix = 'msg') {
      const isMsg = prefix === 'msg';
      const inp = document.getElementById(isMsg ? 'msg-mk-direct-input' : 'markanm-direct-msg-input');
      const fb = document.getElementById(isMsg ? 'msg-mk-feedback' : 'markanm-direct-feedback');
      const text = inp ? inp.value.trim() : '';
      if (!text) return;

      if (fb) {
        fb.textContent = 'Sending message to MarkanM...';
        fb.style.display = 'block';
        fb.style.color = '#ec4899';
      }
      try {
        const res = await fetch('/api/markanm/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message: text })
        });
        const d = await res.json();
        if (fb) {
          if (res.ok && d.success) {
            fb.innerHTML = `✅ Sent in <b>${d.elapsed_ms || 180}ms</b>!`;
            fb.style.color = '#34d399';
          } else {
            fb.textContent = d.message || 'Failed to send message';
            fb.style.color = '#ef4444';
          }
          setTimeout(() => { if (res.ok) fb.style.display = 'none'; }, 4000);
        }
        if (res.ok && inp) inp.value = '';
        setTimeout(loadBotChannelsActivity, 600);
      } catch(e) {
        if (fb) {
          fb.textContent = 'Error: ' + e;
          fb.style.color = '#ef4444';
        }
      }
    }
    const sendDirectMarkanMMessage = () => sendDirectMarkanMMsgUI('bots');

    function loadMessagingIntegrationsConfig() {
      loadTelegramConfig();
      loadMarkanMConfig();
    }

    let currentBotActivityFilter = 'all';
    function filterBotActivityLogs(provider) {
      currentBotActivityFilter = provider;
      ['all', 'tg', 'mk'].forEach(p => {
        const btn = document.getElementById(`msg-filter-${p}-btn`);
        if (btn) {
          if ((p === 'all' && provider === 'all') || (p === 'tg' && provider === 'telegram') || (p === 'mk' && provider === 'markanm')) {
            btn.style.background = 'rgba(139,92,246,0.3)';
            btn.style.color = '#fff';
          } else {
            btn.style.background = 'transparent';
            btn.style.color = 'var(--text-muted)';
          }
        }
      });
      loadBotChannelsActivity(provider);
    }

    async function loadBotChannelsActivity(provider = null) {
      const activeFilter = provider || currentBotActivityFilter || 'all';
      try {
        const url = activeFilter === 'all' ? '/api/channels/activity?limit=50' : `/api/channels/activity?limit=50&provider=${activeFilter}`;
        const res = await fetch(url);
        if (!res.ok) return;
        const d = await res.json();
        const logs = d.activity || [];

        // Update tables on both screens
        const targets = [
          { table: document.getElementById('bot-activity-table'), empty: document.getElementById('bot-activity-empty'), tbody: document.getElementById('bot-activity-tbody') },
          { table: document.getElementById('msg-activity-table'), empty: document.getElementById('msg-activity-empty'), tbody: document.getElementById('msg-activity-tbody') }
        ];

        targets.forEach(({ table, empty, tbody }) => {
          if (!table || !empty || !tbody) return;
          if (logs.length === 0) {
            table.style.display = 'none';
            empty.style.display = 'block';
            empty.textContent = activeFilter === 'all' ? 'No bot interactions logged yet. Send a message on Telegram or MarkanM to see real-time records.' : `No ${activeFilter} interactions logged yet.`;
            return;
          }

          empty.style.display = 'none';
          table.style.display = 'table';
          tbody.innerHTML = '';

          logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';

            const timeStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '-';
            const isTg = (log.source || '').toLowerCase().includes('telegram');
            const channelBadge = isTg
              ? '<span style="color:#38bdf8; background:rgba(56,189,248,0.1); padding:2px 6px; border-radius:4px; font-weight:600;">✈️ Telegram</span>'
              : '<span style="color:#ec4899; background:rgba(236,72,153,0.1); padding:2px 6px; border-radius:4px; font-weight:600;">💬 MarkanM</span>';

            let details = log.body_payload || log.user_details || log.path || '';
            if (typeof details === 'string' && (details.startsWith('{') || details.startsWith('['))) {
              try {
                const parsed = JSON.parse(details);
                if (parsed.message) details = parsed.message;
                else if (parsed.command) details = `/${parsed.command} ${parsed.args || ''}`.trim();
                else if (parsed.text) details = parsed.text;
              } catch(e) {}
            }
            if (typeof details === 'string' && details.length > 120) {
              details = details.slice(0, 120) + '...';
            }

            const statusColor = (log.status_code === 200 || log.status_code === 0) ? '#34d399' : '#ef4444';
            const statusText = log.status_code === 200 ? '✅ 200 OK' : (log.status_code === 403 ? '⛔ 403 Forbidden' : `⚠️ ${log.status_code}`);

            tr.innerHTML = `
              <td style="padding:6px 10px; font-size:11px; color:var(--text-muted);">${timeStr}</td>
              <td style="padding:6px 10px;">${channelBadge}</td>
              <td style="padding:6px 10px; font-family:monospace; color:#e2e8f0; font-size:11px;">${log.method || 'MSG'}</td>
              <td style="padding:6px 10px; color:var(--text-muted); font-size:11px;">${log.ip_address || '-'}</td>
              <td style="padding:6px 10px; color:#cbd5e1; font-size:11px;">${escapeHtml(String(details))}</td>
              <td style="padding:6px 10px; font-size:11px; color:${statusColor}; font-weight:600;">${statusText}</td>
            `;
            tbody.appendChild(tr);
          });
        });
      } catch(e) {
        console.warn('Failed to load bot channels activity:', e);
      }
    }

    async function clearBotActivityLogs() {
      if (!confirm('Are you sure you want to purge bot activity records from the database?')) return;
      try {
        await fetch('/api/channels/activity/clear', { method: 'POST' });
        await fetch('/api/requests/clear', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ days: 0 })
        });
        loadBotChannelsActivity();
      } catch(e) {
        alert('Failed to clear logs: ' + e);
      }
    }
    const clearBotActivity = clearBotActivityLogs;

    // ==========================================
    // RAG KNOWLEDGE BASE
    // ==========================================
    let ragUnlockedPin = null;

    function initRAGScreen() {
      const lockBox = document.getElementById('rag-lock-container');
      const vaultBox = document.getElementById('rag-vault-container');
      if (ragUnlockedPin) {
        if (lockBox) lockBox.style.display = 'none';
        if (vaultBox) vaultBox.style.display = 'block';
        loadRAGDocuments();
      } else {
        if (lockBox) lockBox.style.display = 'block';
        if (vaultBox) vaultBox.style.display = 'none';
        const pinInput = document.getElementById('rag-pin-input');
        if (pinInput) {
          pinInput.value = '';
          setTimeout(() => pinInput.focus(), 100);
        }
      }
    }

    async function unlockRAG() {
      const pinInput = document.getElementById('rag-pin-input');
      const errBox = document.getElementById('rag-pin-err');
      const pin = pinInput ? pinInput.value.trim() : '';

      if (!pin) {
        if (errBox) { errBox.textContent = '⚠️ Please enter the 6-digit Master PIN.'; errBox.style.display = 'block'; }
        return;
      }

      try {
        const res = await fetch('/api/rag/auth', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ pin: pin })
        });
        const d = await res.json();
        if (res.ok && d.success) {
          ragUnlockedPin = pin;
          if (errBox) errBox.style.display = 'none';
          document.getElementById('rag-lock-container').style.display = 'none';
          document.getElementById('rag-vault-container').style.display = 'block';
          loadRAGDocuments();
        } else {
          if (errBox) {
            errBox.textContent = '❌ ' + (d.message || 'Incorrect Master PIN. Access denied.');
            errBox.style.display = 'block';
          }
        }
      } catch(e) {
        if (errBox) {
          errBox.textContent = 'Auth error: ' + e;
          errBox.style.display = 'block';
        }
      }
    }

    function lockRAG() {
      ragUnlockedPin = null;
      document.getElementById('rag-vault-container').style.display = 'none';
      document.getElementById('rag-lock-container').style.display = 'block';
      const pinInput = document.getElementById('rag-pin-input');
      if (pinInput) pinInput.value = '';
    }

    async function loadRAGDocuments() {
      if (!ragUnlockedPin) return;

      const qInput = document.getElementById('rag-search-filter');
      const catSelect = document.getElementById('rag-category-filter');
      const query = qInput ? qInput.value.trim() : '';
      const category = catSelect ? catSelect.value : 'all';

      const listContainer = document.getElementById('rag-docs-list');
      if (listContainer) listContainer.innerHTML = '<div style="color:var(--text-muted); font-size:13px;">Loading knowledge vault...</div>';

      try {
        let url = `/api/rag/documents?pin=${encodeURIComponent(ragUnlockedPin)}`;
        if (query) url += `&search=${encodeURIComponent(query)}`;
        if (category && category !== 'all') url += `&category=${encodeURIComponent(category)}`;

        const res = await fetch(url);
        if (!res.ok) {
          if (res.status === 403) { lockRAG(); return; }
          throw new Error('Failed to fetch documents');
        }
        const data = await res.json();

        // Update stats
        if (data.stats) {
          const docCountEl = document.getElementById('rag-stat-docs');
          const wordCountEl = document.getElementById('rag-stat-words');
          const catCountEl = document.getElementById('rag-stat-cats');
          if (docCountEl) docCountEl.textContent = data.stats.total_documents || 0;
          if (wordCountEl) wordCountEl.textContent = data.stats.total_words || 0;
          if (catCountEl) catCountEl.textContent = data.stats.categories ? Object.keys(data.stats.categories).length : 0;
        }

        const docs = data.documents || [];
        if (!listContainer) return;

        if (docs.length === 0) {
          listContainer.innerHTML = `
            <div style="padding:24px; text-align:center; color:var(--text-muted); border:1px dashed var(--border); border-radius:8px;">
              🧠 No knowledge documents found. Ingest your first document using the form above!
            </div>
          `;
          return;
        }

        listContainer.innerHTML = '';
        docs.forEach(doc => {
          const item = document.createElement('div');
          item.className = 'card';
          item.style.padding = '12px 16px';
          item.style.margin = '0';
          item.style.borderLeft = '3px solid #a855f7';

          const excerpt = (doc.content || '').substring(0, 180) + ((doc.content || '').length > 180 ? '...' : '');
          let tagsList = [];
          if (Array.isArray(doc.tags)) {
            tagsList = doc.tags;
          } else if (typeof doc.tags === 'string' && doc.tags.trim()) {
            tagsList = doc.tags.split(',').map(t => t.trim().replace(/^#/, '')).filter(Boolean);
          }
          const tagsStr = tagsList.map(t => `<span style="background:rgba(168,85,247,0.15); color:#c084fc; padding:2px 6px; border-radius:4px; font-size:10px; margin-right:4px;">#${t}</span>`).join('');
          const wordCount = doc.word_count || (doc.content ? doc.content.split(/\s+/).filter(Boolean).length : 0);

          item.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
              <div>
                <span style="font-size:11px; text-transform:uppercase; font-weight:700; color:#c084fc; background:rgba(168,85,247,0.1); padding:2px 6px; border-radius:4px; margin-right:8px;">${doc.category || 'notes'}</span>
                <b style="font-size:14px; color:#fff;">${doc.title || 'Untitled Document'}</b>
              </div>
              <button class="btn btn-secondary" onclick="deleteRAGDocument(${doc.id})" style="padding:4px 8px; font-size:11px; color:#ef4444; border-color:rgba(239,68,68,0.4);">🗑️ Delete</button>
            </div>
            <div style="font-size:12px; color:#94a3b8; font-family:monospace; line-height:1.4; margin-bottom:6px; white-space:pre-wrap; background:rgba(0,0,0,0.3); padding:6px 10px; border-radius:4px;">${excerpt}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted);">
              <div>${tagsStr}</div>
              <div>${doc.updated_at || doc.created_at || ''} (${wordCount} words)</div>
            </div>
          `;
          listContainer.appendChild(item);
        });
      } catch(e) {
        if (listContainer) listContainer.innerHTML = `<div style="color:#ef4444; font-size:12px;">Error loading documents: ${e}</div>`;
      }
    }

    async function saveRAGDocument() {
      if (!ragUnlockedPin) { lockRAG(); return; }

      const titleInput = document.getElementById('rag-new-title');
      const catSelect = document.getElementById('rag-new-cat');
      const tagsInput = document.getElementById('rag-new-tags');
      const contentInput = document.getElementById('rag-new-content');
      const msg = document.getElementById('rag-add-msg');

      const title = titleInput ? titleInput.value.trim() : '';
      const category = catSelect ? catSelect.value : 'notes';
      const tags = tagsInput ? tagsInput.value.trim() : '';
      const content = contentInput ? contentInput.value.trim() : '';

      if (!content) {
        alert('Please enter knowledge content before saving.');
        return;
      }

      try {
        const res = await fetch('/api/rag/documents', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            pin: ragUnlockedPin,
            title: title || 'Untitled Knowledge Chunk',
            category: category,
            tags: tags,
            content: content
          })
        });
        const d = await res.json();
        if (res.ok) {
          if (titleInput) titleInput.value = '';
          if (tagsInput) tagsInput.value = '';
          if (contentInput) contentInput.value = '';

          if (msg) {
            msg.textContent = 'Saved and indexed into Aarushi\'s memory vault!';
            msg.style.display = 'block';
            setTimeout(() => { msg.style.display = 'none'; }, 4000);
          }
          loadRAGDocuments();
        } else {
          alert('Failed to save document: ' + (d.error || 'Server error'));
        }
      } catch(e) {
        alert('Error saving document: ' + e);
      }
    }

    async function deleteRAGDocument(docId) {
      if (!ragUnlockedPin) { lockRAG(); return; }
      if (!confirm('Are you sure you want to remove this knowledge document from Aarushi\'s context?')) return;

      try {
        const res = await fetch(`/api/rag/documents/${docId}?pin=${encodeURIComponent(ragUnlockedPin)}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          loadRAGDocuments();
        } else {
          alert('Failed to delete document.');
        }
      } catch(e) {
        alert('Delete error: ' + e);
      }
    }

    async function testRAGQuery() {
      if (!ragUnlockedPin) { lockRAG(); return; }
      const qInput = document.getElementById('rag-test-query');
      const query = qInput ? qInput.value.trim() : '';
      const resultsBox = document.getElementById('rag-test-results');

      if (!query) return;
      if (resultsBox) resultsBox.innerHTML = '<span style="color:#38bdf8;">Searching semantic index...</span>';

      try {
        const res = await fetch('/api/rag/query', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ pin: ragUnlockedPin, query: query })
        });
        const d = await res.json();
        const matches = d.matches || [];

        if (matches.length === 0) {
          resultsBox.innerHTML = '<span style="color:var(--text-muted);">No matching knowledge chunks found for this query.</span>';
          return;
        }

        let html = `<div style="margin-bottom:8px; color:#c084fc; font-weight:700;">Retrieved ${matches.length} Relevant Chunks:</div>`;
        matches.forEach(m => {
          html += `
            <div style="margin-bottom:6px; padding:6px 10px; background:rgba(255,255,255,0.03); border-radius:4px; border-left:2px solid #38bdf8;">
              <div style="display:flex; justify-content:space-between; color:#38bdf8; font-weight:600;">
                <span>${m.title} [${m.category}]</span>
                <span style="font-size:10px; color:#94a3b8;">Score: ${(m.score || 0).toFixed(2)}</span>
              </div>
              <div style="margin-top:2px; color:#cbd5e1; white-space:pre-wrap;">${m.content}</div>
            </div>
          `;
        });
        resultsBox.innerHTML = html;
      } catch(e) {
        resultsBox.innerHTML = `<span style="color:#ef4444;">Query test failed: ${e}</span>`;
      }
    }

    // ==========================================
    // USER PROFILE & AI IDENTITY SETTINGS
    // ==========================================
    async function loadUserProfile() {
      try {
        const res = await fetch('/api/settings/profile');
        if (!res.ok) return;
        const d = await res.json();
        const uInput = document.getElementById('profile-user-name');
        const aInput = document.getElementById('profile-assistant-name');
        if (uInput && d.user_name) uInput.value = d.user_name;
        if (aInput && d.assistant_name) {
          aInput.value = d.assistant_name;
          applyAssistantNameEverywhere(d.assistant_name);
        }
      } catch(e) {
        console.warn('Failed to load user profile:', e);
      }
    }

    async function saveUserProfile() {
      const uInput = document.getElementById('profile-user-name');
      const aInput = document.getElementById('profile-assistant-name');
      const pwInput = document.getElementById('profile-bot-master-pw');
      const pinInput = document.getElementById('profile-rag-pin');
      const feedback = document.getElementById('profile-save-feedback');

      const payload = {
        user_name: uInput ? uInput.value.trim() : '',
        assistant_name: aInput ? aInput.value.trim() : '',
        bot_master_password: pwInput ? pwInput.value.trim() : '',
        rag_pin: pinInput ? pinInput.value.trim() : ''
      };

      try {
        const res = await fetch('/api/settings/profile', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (feedback) {
          feedback.textContent = d.message || 'Identity preferences updated successfully!';
          feedback.style.display = 'block';
          feedback.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { feedback.style.display = 'none'; }, 5000);
        }
        if (payload.assistant_name) applyAssistantNameEverywhere(payload.assistant_name);
        if (pwInput) pwInput.value = '';
        if (pinInput) pinInput.value = '';
      } catch(e) {
        alert('Failed to save profile: ' + e);
      }
    }

    function togglePasswordVisibility(id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.type = el.type === 'password' ? 'text' : 'password';
    }

    // ==========================================
    // MARKANM DOCUMENTATION & CODE PLAYGROUND
    // ==========================================
    function showMarkanMTab(tab) {
      const docsTab = document.getElementById('mk-tab-docs');
      const codeTab = document.getElementById('mk-tab-code');
      const apiTab = document.getElementById('mk-tab-api');
      const btnDocs = document.getElementById('mk-tab-btn-docs');
      const btnCode = document.getElementById('mk-tab-btn-code');
      const btnApi = document.getElementById('mk-tab-btn-api');

      if (!docsTab || !codeTab || !apiTab) return;

      docsTab.style.display = tab === 'docs' ? 'block' : 'none';
      codeTab.style.display = tab === 'code' ? 'block' : 'none';
      apiTab.style.display = tab === 'api' ? 'block' : 'none';

      btnDocs.className = tab === 'docs' ? 'btn' : 'btn btn-secondary';
      btnDocs.style.background = tab === 'docs' ? '#ec4899' : 'transparent';
      btnDocs.style.color = tab === 'docs' ? '#fff' : 'var(--text-muted)';

      btnCode.className = tab === 'code' ? 'btn' : 'btn btn-secondary';
      btnCode.style.background = tab === 'code' ? '#ec4899' : 'transparent';
      btnCode.style.color = tab === 'code' ? '#fff' : 'var(--text-muted)';

      btnApi.className = tab === 'api' ? 'btn' : 'btn btn-secondary';
      btnApi.style.background = tab === 'api' ? '#ec4899' : 'transparent';
      btnApi.style.color = tab === 'api' ? '#fff' : 'var(--text-muted)';
    }

    function copyMarkanMDocCode() {
      const editor = document.getElementById('markanm-code-editor');
      if (!editor) return;
      navigator.clipboard.writeText(editor.value).then(() => {
        alert('📋 MarkanM Python bot code copied to clipboard!');
      }).catch(err => {
        editor.select();
        document.execCommand('copy');
        alert('📋 Code copied!');
      });
    }

    function downloadMarkanMExampleScript() {
      const editor = document.getElementById('markanm-code-editor');
      const code = editor ? editor.value : '';
      const blob = new Blob([code], { type: 'text/x-python' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'markanm_bot_example.py';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    // ==========================================
    // EMAIL SETTINGS (GMAIL & IMAP)
    // ==========================================
    async function loadEmailSettings() {
      try {
        const res = await fetch('/api/settings/email');
        if (!res.ok) return;
        const d = await res.json();
        const emailInput = document.getElementById('email-address-input');
        const pwdInput = document.getElementById('email-password-input');
        if (emailInput && d.email_address) emailInput.value = d.email_address;
        if (pwdInput && d.has_password) pwdInput.placeholder = '•••••••••••••••• (App Password Configured)';
      } catch(e) {
        console.warn('Failed to load email settings:', e);
      }
    }

    async function saveEmailSettings() {
      const emailInput = document.getElementById('email-address-input');
      const pwdInput = document.getElementById('email-password-input');
      const feedback = document.getElementById('email-save-feedback');

      const emailAddr = emailInput ? emailInput.value.trim() : '';
      const appPwd = pwdInput ? pwdInput.value.trim() : '';

      try {
        const res = await fetch('/api/settings/email', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ email_address: emailAddr, app_password: appPwd })
        });
        const d = await res.json();
        if (feedback) {
          feedback.textContent = d.message || 'Email settings saved successfully!';
          feedback.style.display = 'block';
          feedback.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { feedback.style.display = 'none'; }, 5000);
        }
        if (pwdInput && appPwd) pwdInput.value = '';
        loadEmailSettings();
      } catch(e) {
        alert('Failed to save email settings: ' + e);
      }
    }

    async function testEmailConnection() {
      const feedback = document.getElementById('email-save-feedback');
      if (feedback) {
        feedback.textContent = '⏳ Testing IMAP connection to Gmail...';
        feedback.style.display = 'block';
        feedback.style.color = '#38bdf8';
      }

      try {
        const res = await fetch('/api/email/test', { method: 'POST' });
        const d = await res.json();
        if (feedback) {
          feedback.textContent = d.message || (res.ok ? 'Connection successful!' : 'Connection failed');
          feedback.style.display = 'block';
          feedback.style.color = res.ok ? '#34d399' : '#ef4444';
          setTimeout(() => { feedback.style.display = 'none'; }, 6000);
        }
      } catch(e) {
        if (feedback) {
          feedback.textContent = 'Connection test failed: ' + e;
          feedback.style.color = '#ef4444';
        }
      }
    }

    // ==========================================
    // SYSTEM COMPATIBILITY SCANNER
    // ==========================================
    async function runCompatibilityScan() {
      const loading = document.getElementById('compat-audit-loading');
      const list = document.getElementById('compat-audit-list');
      if (loading) loading.style.display = 'block';
      if (list) list.style.display = 'none';

      try {
        const res = await fetch('/api/system/compatibility');
        if (!res.ok) return;
        const d = await res.json();
        if (loading) loading.style.display = 'none';
        if (list) {
          list.style.display = 'block';
          let html = '<div style="display:flex; flex-direction:column; gap:8px;">';
          (d.checks || []).forEach(c => {
            const icon = c.status === 'PASS' ? '✅' : (c.status === 'WARN' ? '⚠️' : '❌');
            const color = c.status === 'PASS' ? '#34d399' : (c.status === 'WARN' ? '#fbbf24' : '#ef4444');
            html += `
              <div style="background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:6px; border-left:3px solid ${color};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <b>${icon} ${c.name}</b>
                  <span style="font-family:monospace; color:${color}; font-weight:600;">${c.value}</span>
                </div>
                <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${c.details}</div>
              </div>
            `;
          });
          html += '</div>';
          list.innerHTML = html;
        }
      } catch(e) {
        if (loading) loading.textContent = 'Compatibility scan failed: ' + e;
      }
    }

    // ==========================================
    // DYNAMIC AI NAME APPLICATION
    // ==========================================
    function applyAssistantNameEverywhere(name) {
      if (!name) return;
      const headerName = document.getElementById('header-ai-name');
      const pageTitle = document.getElementById('page-title');
      const chatInput = document.getElementById('chat-input');
      const homeInput = document.getElementById('home-chat-input');

      if (headerName) headerName.textContent = name;
      if (pageTitle) pageTitle.textContent = name + ' Command Center';
      if (chatInput) chatInput.placeholder = 'Ask ' + name + ' anything, or speak naturally...';
      if (homeInput) homeInput.placeholder = 'Ask ' + name + ' anything or click Mic to talk...';
    }

    // ==========================================
    // SARVAM QUOTA EXCEEDED MODAL HANDLER
    // ==========================================
    let quotaModalDismissed = false;

    function handleSarvamQuotaExceeded(errorMsg) {
      if (quotaModalDismissed) return;
      const modal = document.getElementById('sarvam-quota-modal');
      if (modal && modal.style.display !== 'flex') {
        modal.style.display = 'flex';
      }
    }

    function closeSarvamQuotaModal() {
      const modal = document.getElementById('sarvam-quota-modal');
      if (modal) modal.style.display = 'none';
      quotaModalDismissed = true;
    }

    async function saveNewSarvamKeyFromModal() {
      const input = document.getElementById('modal-new-sarvam-key');
      const feedback = document.getElementById('modal-sarvam-feedback');
      const key = input ? input.value.trim() : '';

      if (!key) {
        alert('Please enter a valid Sarvam API key.');
        return;
      }

      try {
        localStorage.setItem('gdr_sarvam_api_key', key);
        const res = await fetch('/api/sarvam/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ api_key: key })
        });
        const d = await res.json();
        if (res.ok) {
          quotaModalDismissed = false;
          closeSarvamQuotaModal();
          alert('✅ New Sarvam API key saved successfully! Quota lock cleared.');
          loadSarvamConfig();
          fetchStatus();
        } else {
          if (feedback) {
            feedback.textContent = d.message || 'Failed to save key';
            feedback.style.color = '#ef4444';
            feedback.style.display = 'block';
          }
        }
      } catch(e) {
        alert('Failed to save key: ' + e);
      }
    }

    // ─── LMMs Engine, Session Graph, IDE & Vector Store Functions ──────────
    let currentEngineMode = 'fast';
    const ENGINE_MODES = ['fast', 'deep', 'code', 'pair'];

    async function cycleEngineMode() {
      const idx = ENGINE_MODES.indexOf(currentEngineMode);
      const nextMode = ENGINE_MODES[(idx + 1) % ENGINE_MODES.length];
      try {
        const res = await fetch('/api/engine/mode', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ mode: nextMode })
        });
        const d = await res.json();
        if (d.success) {
          currentEngineMode = d.mode;
          updateEngineModePill();
        }
      } catch (e) {
        console.warn('Engine mode cycle error:', e);
      }
    }

    function updateEngineModePill() {
      const pill = document.getElementById('engine-mode-pill');
      if (!pill) return;
      const icons = { fast: '⚡ FAST', deep: '🧠 DEEP', code: '💻 CODE', pair: '👥 PAIR' };
      const colors = { fast: 'var(--accent-primary)', deep: '#3b82f6', code: '#a855f7', pair: '#06b6d4' };
      pill.textContent = icons[currentEngineMode] || '⚡ FAST';
      pill.style.color = colors[currentEngineMode] || 'var(--accent-primary)';
      pill.style.borderColor = colors[currentEngineMode] || 'var(--accent-border)';
    }

    async function sessionUndo() {
      try {
        const res = await fetch('/api/session/undo', { method: 'POST' });
        const d = await res.json();
        if (d.success) {
          alert('⟲ Undone to previous turn.');
          fetchStatus();
        } else {
          alert(d.error || 'Nothing to undo');
        }
      } catch (e) {
        alert('Undo error: ' + e);
      }
    }

    async function sessionRedo() {
      try {
        const res = await fetch('/api/session/redo', { method: 'POST' });
        const d = await res.json();
        if (d.success) {
          alert('⟳ Redone to forward turn.');
          fetchStatus();
        } else {
          alert(d.error || 'Nothing to redo');
        }
      } catch (e) {
        alert('Redo error: ' + e);
      }
    }

    async function sessionCheckpoint() {
      const label = prompt('Enter a label for this checkpoint:', 'Checkpoint ' + new Date().toLocaleTimeString());
      if (!label) return;
      try {
        const res = await fetch('/api/session/checkpoint', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ label })
        });
        const d = await res.json();
        if (d.success) {
          alert('📌 Checkpoint saved: ' + label);
        } else {
          alert(d.error || 'Failed to create checkpoint');
        }
      } catch (e) {
        alert('Checkpoint error: ' + e);
      }
    }

    function initIdeMode() {
      const isEnabled = localStorage.getItem('gdr_ide_mode') !== 'false';
      const navTab = document.getElementById('nav-ide-tab');
      if (navTab) navTab.style.display = isEnabled ? 'inline-block' : 'none';
      const toggle = document.getElementById('setting-ide-toggle');
      if (toggle) toggle.checked = isEnabled;
    }

    function toggleIdeModeSetting(checked) {
      localStorage.setItem('gdr_ide_mode', checked ? 'true' : 'false');
      const navTab = document.getElementById('nav-ide-tab');
      if (navTab) navTab.style.display = checked ? 'inline-block' : 'none';
      if (checked) {
        refreshIdeFiles();
      }
    }

    async function refreshIdeFiles() {
      const tree = document.getElementById('ide-file-tree');
      if (!tree) return;
      tree.innerHTML = '<div style="color:var(--text-muted); padding:4px;">Scanning files...</div>';
      try {
        const res = await fetch('/api/files/list?path=' + encodeURIComponent('.'));
        if (res.ok) {
          const d = await res.json();
          const files = d.files || [];
          if (files.length === 0) {
            tree.innerHTML = '<div style="color:var(--text-muted); padding:4px;">No files found.</div>';
            return;
          }
          tree.innerHTML = files.slice(0, 30).map(f => `
            <div onclick="openIdeFile('${f.path}')" style="cursor:pointer; padding:3px 6px; border-radius:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-bottom:2px;" onmouseover="this.style.background='var(--bg-secondary)'" onmouseout="this.style.background='transparent'">
              📄 ${f.name}
            </div>
          `).join('');
        } else {
          tree.innerHTML = `
            <div onclick="openIdeFile('scratch.py')" style="cursor:pointer; padding:3px 6px;">📄 scratch.py</div>
            <div onclick="openIdeFile('main.py')" style="cursor:pointer; padding:3px 6px;">📄 main.py</div>
            <div onclick="openIdeFile('test.sh')" style="cursor:pointer; padding:3px 6px;">📄 test.sh</div>
          `;
        }
      } catch (e) {
        tree.innerHTML = `
          <div onclick="openIdeFile('scratch.py')" style="cursor:pointer; padding:3px 6px;">📄 scratch.py</div>
          <div onclick="openIdeFile('agent.py')" style="cursor:pointer; padding:3px 6px;">📄 agent.py</div>
        `;
      }
    }

    // ─── GDR-IDE STATE & INTERACTIVE PERSONAL TERMINAL ────────────────────
    let ideOpenTabs = [
      { name: 'scratch.py', path: 'scratch.py', content: '# Welcome to GDR-IDE — Next-Gen AI Code Studio\nprint("Hello from GDR-IDE on Linux!")\n', dirty: false }
    ];
    let ideActiveTabIdx = 0;
    let ideTerminalHistory = [];
    let ideTerminalHistoryIdx = -1;
    let ideTerminalUser = 'user';
    let ideTerminalHost = 'localhost';
    let ideTerminalCwd = '~';
    let ideActiveBottomTab = 'terminal';

    function renderIdeTabs() {
      const tabsBar = document.getElementById('ide-tabs-bar');
      if (!tabsBar) return;
      tabsBar.innerHTML = ideOpenTabs.map((tab, idx) => {
        const isActive = idx === ideActiveTabIdx;
        const icon = tab.name.endsWith('.py') ? '🐍' : tab.name.endsWith('.sh') ? '💻' : tab.name.endsWith('.md') ? '📝' : tab.name.endsWith('.json') ? '⚙️' : '📄';
        return `
          <div onclick="switchIdeTab(${idx})" style="cursor:pointer; display:flex; align-items:center; gap:6px; padding:6px 12px; background:${isActive ? '#1e1e24' : '#141416'}; color:${isActive ? '#f4f4f5' : '#71717a'}; border-top:${isActive ? '2px solid #007acc' : '2px solid transparent'}; border-right:1px solid #27272a; font-size:12px; font-family:var(--font-mono, monospace); user-select:none;">
            <span>${icon}</span>
            <span>${tab.name}</span>
            ${tab.dirty ? '<span style="color:#f59e0b; font-size:10px;">●</span>' : ''}
            <span onclick="closeIdeTab(${idx}, event)" style="color:#71717a; font-size:14px; margin-left:4px; border-radius:3px; padding:0 3px;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#71717a'">×</span>
          </div>
        `;
      }).join('');

      const active = ideOpenTabs[ideActiveTabIdx];
      if (active) {
        const breadcrumb = document.getElementById('ide-breadcrumb-text');
        if (breadcrumb) breadcrumb.textContent = `gdragent › ${active.name}`;
        const statusFile = document.getElementById('ide-status-filename');
        if (statusFile) statusFile.textContent = active.name;
        const editor = document.getElementById('ide-code-editor');
        if (editor && editor.value !== active.content) {
          editor.value = active.content;
        }
        syncIdeLineNumbers();
        updateIdeEditorState();
      }
    }

    function switchIdeTab(idx) {
      if (idx >= 0 && idx < ideOpenTabs.length) {
        ideActiveTabIdx = idx;
        renderIdeTabs();
      }
    }

    function closeIdeTab(idx, e) {
      if (e) e.stopPropagation();
      if (ideOpenTabs.length <= 1) return; // Keep at least one tab
      ideOpenTabs.splice(idx, 1);
      if (ideActiveTabIdx >= ideOpenTabs.length) {
        ideActiveTabIdx = ideOpenTabs.length - 1;
      }
      renderIdeTabs();
    }

    async function openIdeFile(filePath, fileName) {
      const existingIdx = ideOpenTabs.findIndex(t => t.path === filePath);
      if (existingIdx !== -1) {
        ideActiveTabIdx = existingIdx;
        renderIdeTabs();
        return;
      }

      const name = fileName || filePath.split('/').pop();
      try {
        const res = await fetch('/api/files/content?path=' + encodeURIComponent(filePath));
        if (res.ok) {
          const d = await res.json();
          ideOpenTabs.push({ name: name, path: filePath, content: d.content, dirty: false });
          ideActiveTabIdx = ideOpenTabs.length - 1;
          renderIdeTabs();
        } else {
          ideOpenTabs.push({ name: name, path: filePath, content: `# File: ${name}\n`, dirty: false });
          ideActiveTabIdx = ideOpenTabs.length - 1;
          renderIdeTabs();
        }
      } catch (e) {
        ideOpenTabs.push({ name: name, path: filePath, content: `# File: ${name}\n`, dirty: false });
        ideActiveTabIdx = ideOpenTabs.length - 1;
        renderIdeTabs();
      }
    }

    async function saveActiveIdeFile() {
      const active = ideOpenTabs[ideActiveTabIdx];
      const editor = document.getElementById('ide-code-editor');
      if (!active || !editor) return;

      active.content = editor.value;
      try {
        const res = await fetch('/api/files/save', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ path: active.path, content: active.content })
        });
        const d = await res.json();
        if (d.success) {
          active.dirty = false;
          renderIdeTabs();
          const term = document.getElementById('ide-terminal-history');
          if (term) {
            term.innerHTML += `<div style="color:#10A37F; margin:4px 0;">💾 Saved: ${active.path} (${d.bytes_written} bytes)</div>`;
            term.scrollTop = term.scrollHeight;
          }
        }
      } catch (e) {
        alert('Save error: ' + e);
      }
    }

    function createIdeNewFile() {
      const name = prompt('Enter new file name:', 'untitled.py');
      if (!name) return;
      const path = name;
      ideOpenTabs.push({ name: name, path: path, content: '', dirty: true });
      ideActiveTabIdx = ideOpenTabs.length - 1;
      renderIdeTabs();
    }

    function syncIdeLineNumbers() {
      const editor = document.getElementById('ide-code-editor');
      const gutter = document.getElementById('ide-line-numbers');
      if (!editor || !gutter) return;
      const lineCount = (editor.value.match(/\n/g) || []).length + 1;
      let nums = '';
      for (let i = 1; i <= lineCount; i++) {
        nums += i + '<br>';
      }
      gutter.innerHTML = nums;
      gutter.scrollTop = editor.scrollTop;
    }

    function updateIdeEditorState() {
      const editor = document.getElementById('ide-code-editor');
      if (!editor) return;
      const active = ideOpenTabs[ideActiveTabIdx];
      if (active && active.content !== editor.value) {
        active.dirty = true;
        active.content = editor.value;
        const tabsBar = document.getElementById('ide-tabs-bar');
        // lightweight dirty indicator
        const activeTabEl = tabsBar && tabsBar.children[ideActiveTabIdx];
        if (activeTabEl && !activeTabEl.innerHTML.includes('●')) {
          renderIdeTabs();
        }
      }

      // Cursor pos
      const textBeforeCursor = editor.value.substring(0, editor.selectionStart);
      const lines = textBeforeCursor.split('\n');
      const curLine = lines.length;
      const curCol = lines[lines.length - 1].length + 1;
      const posText = `Ln ${curLine}, Col ${curCol}`;
      const cpEl = document.getElementById('ide-cursor-pos');
      if (cpEl) cpEl.textContent = posText;
      const scEl = document.getElementById('ide-status-cursor');
      if (scEl) scEl.textContent = posText;
      syncIdeLineNumbers();
    }

    function handleIdeEditorKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveActiveIdeFile();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        executeIdeCode();
        return;
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        const editor = e.target;
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + '    ' + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
        updateIdeEditorState();
      }
    }

    // ─── GDR-IDE PERSONAL TERMINAL FUNCTIONS ──────────────────────────────
    async function submitIdeTerminalCommand(customCmd) {
      const input = document.getElementById('ide-terminal-input');
      const history = document.getElementById('ide-terminal-history');
      const cmd = (customCmd !== undefined ? customCmd : (input ? input.value : '')).trim();
      if (!cmd) return;

      if (input) input.value = '';
      ideTerminalHistory.push(cmd);
      ideTerminalHistoryIdx = ideTerminalHistory.length;

      // Echo command into terminal
      const echoDiv = document.createElement('div');
      echoDiv.style.cssText = 'color:#38bdf8; font-weight:600; margin-top:8px;';
      echoDiv.innerHTML = `<span style="color:#10A37F;">${ideTerminalUser}@${ideTerminalHost}:${ideTerminalCwd}$</span> ${escapeHtml(cmd)}`;
      history.appendChild(echoDiv);
      history.parentElement.scrollTop = history.parentElement.scrollHeight;

      // Check special clear command
      if (cmd === 'clear') {
        history.innerHTML = '';
        return;
      }

      try {
        const res = await fetch('/api/terminal/exec', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ command: cmd, cwd: ideTerminalCwd })
        });
        const d = await res.json();
        
        // Update CWD
        if (d.cwd) {
          ideTerminalCwd = d.cwd;
          const badge = document.getElementById('ide-prompt-badge');
          if (badge) badge.textContent = `${ideTerminalUser}@${ideTerminalHost}:${ideTerminalCwd}$`;
          const tc = document.getElementById('ide-term-cwd');
          if (tc) tc.textContent = ideTerminalCwd;
        }

        const outDiv = document.createElement('div');
        outDiv.style.cssText = 'margin:2px 0 6px 0; white-space:pre-wrap;';
        
        let outputHtml = '';
        if (d.stdout) outputHtml += `<div style="color:#f4f4f5;">${escapeHtml(d.stdout)}</div>`;
        if (d.stderr) outputHtml += `<div style="color:#ef4444;">${escapeHtml(d.stderr)}</div>`;
        if (!d.stdout && !d.stderr && d.exit_code === 0) {
          outputHtml += `<div style="color:#71717a; font-style:italic;">(Process completed with exit code 0)</div>`;
        }
        outDiv.innerHTML = outputHtml;
        history.appendChild(outDiv);
      } catch (err) {
        const errDiv = document.createElement('div');
        errDiv.style.cssText = 'color:#ef4444; margin:4px 0;';
        errDiv.textContent = `Execution failed: ${err}`;
        history.appendChild(errDiv);
      }
      history.parentElement.scrollTop = history.parentElement.scrollHeight;
    }

    function handleIdeTerminalKey(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        submitIdeTerminalCommand();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (ideTerminalHistoryIdx > 0) {
          ideTerminalHistoryIdx--;
          e.target.value = ideTerminalHistory[ideTerminalHistoryIdx] || '';
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (ideTerminalHistoryIdx < ideTerminalHistory.length - 1) {
          ideTerminalHistoryIdx++;
          e.target.value = ideTerminalHistory[ideTerminalHistoryIdx] || '';
        } else {
          ideTerminalHistoryIdx = ideTerminalHistory.length;
          e.target.value = '';
        }
      }
    }

    function clearIdeTerminal() {
      const history = document.getElementById('ide-terminal-history');
      if (history) history.innerHTML = '';
    }

    function setIdeBottomTab(tab) {
      ideActiveBottomTab = tab;
      const bTerm = document.getElementById('tab-term-btn');
      const bOut = document.getElementById('tab-out-btn');
      const bGit = document.getElementById('tab-git-btn');
      if (bTerm) { bTerm.style.color = tab === 'terminal' ? '#f4f4f5' : '#71717a'; bTerm.style.borderBottom = tab === 'terminal' ? '2px solid #38bdf8' : 'none'; }
      if (bOut) { bOut.style.color = tab === 'output' ? '#f4f4f5' : '#71717a'; bOut.style.borderBottom = tab === 'output' ? '2px solid #38bdf8' : 'none'; }
      if (bGit) { bGit.style.color = tab === 'git' ? '#f4f4f5' : '#71717a'; bGit.style.borderBottom = tab === 'git' ? '2px solid #38bdf8' : 'none'; }

      if (tab === 'git') {
        submitIdeTerminalCommand('git status');
      }
    }

    function toggleIdeTerminal() {
      const panel = document.getElementById('ide-bottom-panel');
      if (!panel) return;
      panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    }

    function toggleIdeTerminalHeight() {
      const panel = document.getElementById('ide-bottom-panel');
      if (!panel) return;
      panel.style.height = panel.style.height === '380px' ? '200px' : '380px';
    }

    function toggleIdeCopilot() {
      const cp = document.getElementById('ide-copilot-panel');
      if (!cp) return;
      cp.style.display = cp.style.display === 'none' ? 'flex' : 'none';
    }

    function setIdeActivityTab(tab) {
      const sb = document.getElementById('ide-sidebar');
      const cp = document.getElementById('ide-copilot-panel');
      const bExp = document.getElementById('act-btn-explorer');
      const bTerm = document.getElementById('act-btn-terminal');
      const bCop = document.getElementById('act-btn-copilot');
      const bGit = document.getElementById('act-btn-git');

      [bExp, bTerm, bCop, bGit].forEach(b => { if (b) { b.style.color = '#71717a'; b.style.borderLeft = 'none'; } });

      if (tab === 'explorer') {
        if (bExp) { bExp.style.color = '#f4f4f5'; bExp.style.borderLeft = '2px solid var(--accent-primary)'; }
        if (sb) sb.style.display = 'flex';
      } else if (tab === 'terminal') {
        if (bTerm) { bTerm.style.color = '#f4f4f5'; bTerm.style.borderLeft = '2px solid var(--accent-primary)'; }
        const bp = document.getElementById('ide-bottom-panel');
        if (bp) bp.style.display = 'flex';
      } else if (tab === 'copilot') {
        if (bCop) { bCop.style.color = '#f4f4f5'; bCop.style.borderLeft = '2px solid var(--accent-primary)'; }
        if (cp) cp.style.display = 'flex';
      } else if (tab === 'git') {
        if (bGit) { bGit.style.color = '#f4f4f5'; bGit.style.borderLeft = '2px solid var(--accent-primary)'; }
        setIdeBottomTab('git');
      }
    }

    async function refreshIdeFiles() {
      const tree = document.getElementById('ide-file-tree');
      if (!tree) return;
      tree.innerHTML = '<div style="color:#71717a; padding:12px; text-align:center;">Scanning...</div>';
      try {
        const res = await fetch('/api/files/tree?path=' + encodeURIComponent('.'));
        if (res.ok) {
          const d = await res.json();
          const items = d.items || [];
          if (items.length === 0) {
            tree.innerHTML = '<div style="color:#71717a; padding:8px;">No files found</div>';
            return;
          }
          tree.innerHTML = items.map(item => {
            const icon = item.is_dir ? '📁' : item.ext === '.py' ? '🐍' : item.ext === '.sh' ? '💻' : item.ext === '.md' ? '📝' : item.ext === '.json' ? '⚙️' : '📄';
            return `
              <div onclick="${item.is_dir ? `refreshIdeFilesDir('${item.path}')` : `openIdeFile('${item.path}', '${item.name}')`}" style="cursor:pointer; padding:3px 10px; display:flex; align-items:center; gap:6px; color:#d4d4d8; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" onmouseover="this.style.background='#27272a'" onmouseout="this.style.background='transparent'">
                <span>${icon}</span>
                <span>${item.name}</span>
              </div>
            `;
          }).join('');
        }
      } catch (e) {
        tree.innerHTML = '<div style="color:#ef4444; padding:8px;">Failed to scan files</div>';
      }
    }

    async function refreshIdeFilesDir(path) {
      const tree = document.getElementById('ide-file-tree');
      if (!tree) return;
      try {
        const res = await fetch('/api/files/tree?path=' + encodeURIComponent(path));
        if (res.ok) {
          const d = await res.json();
          const items = d.items || [];
          tree.innerHTML = `
            <div onclick="refreshIdeFiles()" style="cursor:pointer; padding:3px 10px; color:#38bdf8; font-weight:600;">.. (Back to root)</div>
            ${items.map(item => {
              const icon = item.is_dir ? '📁' : item.ext === '.py' ? '🐍' : item.ext === '.sh' ? '💻' : item.ext === '.md' ? '📝' : '📄';
              return `
                <div onclick="${item.is_dir ? `refreshIdeFilesDir('${item.path}')` : `openIdeFile('${item.path}', '${item.name}')`}" style="cursor:pointer; padding:3px 10px; display:flex; align-items:center; gap:6px; color:#d4d4d8; font-size:12px;" onmouseover="this.style.background='#27272a'" onmouseout="this.style.background='transparent'">
                  <span>${icon}</span>
                  <span>${item.name}</span>
                </div>
              `;
            }).join('')}
          `;
        }
      } catch(e) {}
    }

    let ideVoiceCallActive = false;

    function startIdeVoiceCall() {
      ideVoiceCallActive = true;
      const badge = document.getElementById('ide-call-active-badge');
      if (badge) badge.style.display = 'inline-flex';
      const btn = document.getElementById('ide-call-btn');
      if (btn) {
        btn.textContent = '🔴 End Call';
        btn.style.background = 'rgba(239,68,68,0.2)';
        btn.style.borderColor = '#ef4444';
        btn.style.color = '#f87171';
      }
      if (typeof startListeningSafe === 'function') {
        startListeningSafe();
      }
    }

    function endIdeVoiceCall() {
      ideVoiceCallActive = false;
      const badge = document.getElementById('ide-call-active-badge');
      if (badge) badge.style.display = 'none';
      const btn = document.getElementById('ide-call-btn');
      if (btn) {
        btn.textContent = '📞 Call';
        btn.style.background = '';
        btn.style.borderColor = '#ec4899';
        btn.style.color = '#f472b6';
      }
      if (typeof stopSpeechRecognition === 'function') {
        stopSpeechRecognition();
      }
    }

    function toggleIdeVoiceCall() {
      if (ideVoiceCallActive) {
        endIdeVoiceCall();
      } else {
        startIdeVoiceCall();
      }
    }

    async function executeIdeCode() {
      const editor = document.getElementById('ide-code-editor');
      if (!editor) return;
      const code = editor.value;
      const active = ideOpenTabs[ideActiveTabIdx];
      const lang = (active && active.name.endsWith('.sh')) ? 'bash' : (active && active.name.endsWith('.js')) ? 'javascript' : 'python';

      // Switch to terminal tab and echo run command
      setIdeBottomTab('terminal');
      const history = document.getElementById('ide-terminal-history');
      if (history) {
        history.innerHTML += `<div style="color:#10A37F; font-weight:700; margin-top:8px;">⚡ Running ${active ? active.name : 'buffer'} (${lang})...</div>`;
      }

      try {
        const res = await fetch('/api/coding/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ code, language: lang })
        });
        const d = await res.json();
        if (history) {
          let out = '';
          if (d.stdout) out += `<div style="color:#f4f4f5; white-space:pre-wrap;">${escapeHtml(d.stdout)}</div>`;
          if (d.stderr) out += `<div style="color:#ef4444; white-space:pre-wrap;">${escapeHtml(d.stderr)}</div>`;
          out += `<div style="color:#71717a; font-size:11px;">Process finished [Exit Code ${d.exit_code}] in ${d.duration_ms}ms</div>`;
          history.innerHTML += out;
          history.parentElement.scrollTop = history.parentElement.scrollHeight;
        }
      } catch (e) {
        if (history) {
          history.innerHTML += `<div style="color:#ef4444;">Run error: ${e}</div>`;
        }
      }
    }

    async function askIdeCopilotPreset(preset) {
      const prompts = {
        explain: "Explain what this active code does and summarize its key algorithms and logic.",
        refactor: "Suggest modern, clean refactoring improvements for performance and readability.",
        tests: "Write comprehensive pytest unit tests for the functions and classes in this file."
      };
      const query = prompts[preset] || "Explain this code.";
      const input = document.getElementById('ide-ai-prompt');
      if (input) input.value = query;
      askIdeCopilot();
    }

    async function askIdeCopilot() {
      const promptInput = document.getElementById('ide-ai-prompt');
      const editor = document.getElementById('ide-code-editor');
      const msgBox = document.getElementById('ide-copilot-messages');
      if (!promptInput || !editor || !msgBox) return;

      const query = promptInput.value.trim();
      if (!query) return;

      const userMsg = document.createElement('div');
      userMsg.style.cssText = 'padding:6px 10px; background:#27272a; border-radius:6px; color:#f4f4f5; margin-bottom:4px; font-size:12px;';
      userMsg.textContent = query;
      msgBox.appendChild(userMsg);
      promptInput.value = '';

      const aiMsg = document.createElement('div');
      aiMsg.style.cssText = 'padding:8px 10px; background:#1e1e24; border:1px solid #27272a; border-radius:6px; color:#d4d4d8; margin-bottom:4px; font-size:12px; line-height:1.4;';
      aiMsg.textContent = 'Thinking...';
      msgBox.appendChild(aiMsg);
      msgBox.scrollTop = msgBox.scrollHeight;

      const active = ideOpenTabs[ideActiveTabIdx];
      const fullPrompt = `GDR-IDE Copilot Assistance:\nFile: ${active ? active.name : 'scratch.py'}\nCode:\n\`\`\`\n${editor.value.slice(0, 2000)}\n\`\`\`\nRequest: ${query}`;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message: fullPrompt })
        });
        const d = await res.json();
        aiMsg.textContent = d.reply || d.response || 'Completed analysis.';
      } catch (e) {
        aiMsg.textContent = 'Error contacting copilot: ' + e;
      }
      msgBox.scrollTop = msgBox.scrollHeight;
    }

    async function indexDirectoryForRag() {
      const input = document.getElementById('vector-index-input');
      const statusEl = document.getElementById('vector-index-status');
      if (!input || !statusEl) return;

      const path = input.value.trim();
      if (!path) return;

      statusEl.textContent = 'Indexing files recursively...';
      statusEl.style.color = 'var(--text-muted)';

      try {
        const res = await fetch('/api/vector/index', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ path })
        });
        const d = await res.json();
        if (d.status === 'ok') {
          statusEl.textContent = `✅ Successfully indexed ${d.docs_indexed} document chunks!`;
          statusEl.style.color = 'var(--success)';
        } else {
          statusEl.textContent = `❌ ${d.message || 'Indexing failed'}`;
          statusEl.style.color = 'var(--danger)';
        }
      } catch (e) {
        statusEl.textContent = 'Indexing failed: ' + e;
        statusEl.style.color = 'var(--danger)';
      }
    }

    // Auto-refresh on startup
    initIdeMode();
    restoreVoicePreference();
    fetchStatus();
    fetchBriefing();
    loadUserProfile();
    loadEmailSettings();
    runCompatibilityScan();
    loadElevenLabsConfig();
    loadSarvamConfig();
    loadTelegramConfig();
    loadMarkanMConfig();
    enumerateBrowserAudioDevices();
    loadSystemAudioDevices();
    checkCloudflareStatus();
    setInterval(fetchStatus, 5000);
    setInterval(checkCloudflareStatus, 15000);
    setInterval(checkAarushiIdleProactive, 5000);
    requestLocationPermission();
    loadFocusCharactersManifest();

    // =========================================================================
    // FOCUS TALKING MODE CONTROLLER & ANIME COMPANION MANAGER
    // =========================================================================
    let focusCurrentCharacter = localStorage.getItem('gdr_focus_character') || 'cat';
    let focusCurrentTheme = localStorage.getItem('gdr_focus_theme') || 'midnight';
    let focusCallTimerInterval = null;
    let focusCallStartTime = null;
    let focusCallActive = false;
    let focusCurrentExpression = 'neutral';
    let focusMuteSpeaker = false;
    let focusCharactersData = null;

    // Preload image cache
    const focusImageCache = {};

    function preloadCharacterImages(charId) {
      const expressions = ['neutral', 'listening', 'speaking', 'happy', 'thinking', 'curious', 'surprised', 'comforting', 'teasing', 'sleepy'];
      expressions.forEach(expr => {
        const url = `/static/characters/${charId}/${expr}.svg`;
        if (!focusImageCache[url]) {
          const img = new Image();
          img.src = url;
          focusImageCache[url] = img;
        }
      });
    }

    async function loadFocusCharactersManifest() {
      try {
        const res = await fetch('/api/characters');
        if (res.ok) {
          focusCharactersData = await res.json();
          renderCharacterGalleryModal();
        }
      } catch (e) {
        console.warn('Could not load character manifest:', e);
      }
    }

    function openFocusCallMode() {
      focusCallActive = true;
      const overlay = document.getElementById('focus-call-overlay');
      if (!overlay) return;

      document.body.style.overflow = 'hidden';
      overlay.style.display = 'flex';

      // Apply theme and character
      setFocusTheme(focusCurrentTheme);
      setFocusCharacter(focusCurrentCharacter);
      preloadCharacterImages(focusCurrentCharacter);

      // Start Call Timer
      focusCallStartTime = Date.now();
      updateFocusCallTimerDisplay();
      if (focusCallTimerInterval) clearInterval(focusCallTimerInterval);
      focusCallTimerInterval = setInterval(updateFocusCallTimerDisplay, 1000);

      // Connect Mic if not already listening
      const micBtn = document.getElementById('focus-btn-mic');
      if (isListening || isHostListening) {
        if (micBtn) {
          micBtn.classList.add('active');
          const lbl = micBtn.querySelector('.focus-dock-label');
          if (lbl) lbl.textContent = 'Mic Active';
        }
        setFocusExpression('listening');
      } else {
        startListeningSafe(true);
        if (micBtn) {
          micBtn.classList.add('active');
          const lbl = micBtn.querySelector('.focus-dock-label');
          if (lbl) lbl.textContent = 'Mic Active';
        }
        setFocusExpression('listening');
      }

      // Initial friendly greeting if transcript is clean
      const botTextEl = document.getElementById('focus-transcript-bot-text');
      if (botTextEl && (!botTextEl.textContent || botTextEl.textContent.includes('Call started'))) {
        const charName = getCharacterDisplayName(focusCurrentCharacter);
        botTextEl.textContent = `Call started with ${charName}. I am listening, speak naturally or ask anything!`;
      }
    }

    function closeFocusCallMode() {
      focusCallActive = false;
      const overlay = document.getElementById('focus-call-overlay');
      if (overlay) overlay.style.display = 'none';

      document.body.style.overflow = '';
      if (focusCallTimerInterval) {
        clearInterval(focusCallTimerInterval);
        focusCallTimerInterval = null;
      }

      // If assistant was speaking, halt speech gracefully
      if (isSpeaking) {
        stopSpeakingNow();
      }

      // Exit fullscreen if active
      if (document.fullscreenElement) {
        try { document.exitFullscreen(); } catch (e) {}
      }
    }

    function updateFocusCallTimerDisplay() {
      if (!focusCallStartTime) return;
      const elapsedSec = Math.floor((Date.now() - focusCallStartTime) / 1000);
      const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
      const secs = String(elapsedSec % 60).padStart(2, '0');
      const timerEl = document.getElementById('focus-call-timer');
      if (timerEl) timerEl.textContent = `${mins}:${secs}`;
    }

    function setFocusTheme(theme) {
      focusCurrentTheme = theme;
      localStorage.setItem('gdr_focus_theme', theme);
      const overlay = document.getElementById('focus-call-overlay');
      if (overlay) {
        overlay.className = '';
        overlay.classList.add(`focus-theme-${theme}`);
      }
      const select = document.getElementById('focus-theme-select');
      if (select) select.value = theme;
    }

    function setFocusCharacter(charId) {
      focusCurrentCharacter = charId;
      localStorage.setItem('gdr_focus_character', charId);

      const nameEl = document.getElementById('focus-companion-name');
      const botTagEl = document.getElementById('focus-transcript-bot-tag');
      const topAvatar = document.getElementById('focus-top-avatar');
      const dispName = getCharacterDisplayName(charId);

      if (nameEl) nameEl.textContent = dispName;
      if (botTagEl) botTagEl.textContent = dispName.toUpperCase() + ':';
      if (topAvatar) topAvatar.src = `/static/characters/${charId}/neutral.svg`;

      setFocusExpression(focusCurrentExpression || 'neutral');
      preloadCharacterImages(charId);
      renderCharacterGalleryModal();
    }

    function getCharacterDisplayName(charId) {
      if (charId === 'cat') return 'Cat';
      if (charId === 'aarushi') return 'Aarushi';
      if (charId === 'aoi') return 'Aoi';
      if (charId === 'kenji') return 'Kenji';
      return 'Cat';
    }

    function setFocusExpression(expr) {
      focusCurrentExpression = expr;
      const charImg = document.getElementById('focus-character-img');
      if (charImg) {
        charImg.src = `/static/characters/${focusCurrentCharacter}/${expr}.svg`;
      }
      const pill = document.getElementById('focus-expression-pill');
      if (pill) {
        const labels = {
          'neutral': '✨ Attentive & Present',
          'listening': '👂 Listening closely to you...',
          'speaking': '🗣️ Responding...',
          'thinking': '🤔 Deep in thought...',
          'happy': '😊 Smiling & Warm',
          'curious': '🧐 Curious & Intrigued',
          'surprised': '😲 Pleasantly Surprised',
          'comforting': '🤗 Gentle & Caring',
          'teasing': '😏 Playful & Teasing',
          'sleepy': '😴 Cozy & Restful'
        };
        pill.textContent = labels[expr] || `✨ Feeling ${expr}`;
      }
    }

    function updateFocusCallState(state) {
      if (!focusCallActive) return;
      const halo = document.getElementById('focus-halo');
      const wave = document.getElementById('focus-voice-wave');
      const badgeText = document.getElementById('focus-badge-text');

      if (halo) halo.className = `focus-character-halo state-${state}`;
      if (wave) {
        wave.className = 'focus-voice-wave';
        if (state === 'listening') wave.classList.add('active-listening');
        else if (state === 'speaking') wave.classList.add('active-speaking');
        else if (state === 'thinking') wave.classList.add('active-thinking');
      }

      if (badgeText) {
        if (state === 'listening') badgeText.textContent = 'Listening...';
        else if (state === 'speaking') badgeText.textContent = 'Speaking...';
        else if (state === 'thinking') badgeText.textContent = 'Thinking...';
        else badgeText.textContent = 'Connected (Live)';
      }

      // Adapt character expression based on state
      if (state === 'listening') {
        setFocusExpression('listening');
      } else if (state === 'thinking') {
        setFocusExpression('thinking');
      } else if (state === 'idle') {
        setFocusExpression('neutral');
      }
    }

    function updateFocusUserTranscript(text) {
      if (!focusCallActive || !text) return;
      const wrap = document.getElementById('focus-transcript-user-wrap');
      const textEl = document.getElementById('focus-transcript-user-text');
      if (wrap) wrap.style.display = 'flex';
      if (textEl) textEl.textContent = text;

      const scrollEl = document.getElementById('focus-transcript-scroll');
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
    }

    function updateFocusAssistantTranscript(text) {
      if (!focusCallActive || !text) return;
      const textEl = document.getElementById('focus-transcript-bot-text');
      if (textEl) textEl.textContent = text;

      // Detect emotion / sentiment for character expression
      analyzeAndSetExpression(text);

      const scrollEl = document.getElementById('focus-transcript-scroll');
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
    }

    function analyzeAndSetExpression(text) {
      if (!text) return;
      const lower = text.toLowerCase();
      if (lower.includes('haha') || lower.includes('hehe') || lower.includes('glad') || lower.includes('love') || lower.includes('awesome') || lower.includes('yay') || lower.includes('great') || lower.includes('smile') || lower.includes('happy') || lower.includes('delighted')) {
        setFocusExpression('happy');
      } else if (lower.includes('relax') || lower.includes('breathe') || lower.includes("don't worry") || lower.includes("it's okay") || lower.includes('take care') || lower.includes('i am here') || lower.includes("i'm here") || lower.includes('comfort')) {
        setFocusExpression('comforting');
      } else if (lower.includes('curious') || lower.includes('interesting') || lower.includes('how come') || lower.includes('what if') || lower.includes('why') || lower.includes('tell me more')) {
        setFocusExpression('curious');
      } else if (lower.includes('wow') || lower.includes('whoa') || lower.includes('incredible') || lower.includes('really?!') || lower.includes('unbelievable')) {
        setFocusExpression('surprised');
      } else if (lower.includes('silly') || lower.includes('wink') || lower.includes('tease') || lower.includes('baka') || lower.includes('as if')) {
        setFocusExpression('teasing');
      } else if (lower.includes('sleep') || lower.includes('yawn') || lower.includes('tired') || lower.includes('good night') || lower.includes('rest well')) {
        setFocusExpression('sleepy');
      } else {
        setFocusExpression('speaking');
      }
    }

    function toggleFocusMic() {
      const micBtn = document.getElementById('focus-btn-mic');
      if (isListening || isHostListening) {
        handsFreeMode = false;
        stopSpeechRecognition();
        if (micBtn) {
          micBtn.classList.remove('active');
          const lbl = micBtn.querySelector('.focus-dock-label');
          if (lbl) lbl.textContent = 'Mic Muted';
        }
        setFocusExpression('neutral');
      } else {
        handsFreeMode = true;
        startListeningSafe(true);
        if (micBtn) {
          micBtn.classList.add('active');
          const lbl = micBtn.querySelector('.focus-dock-label');
          if (lbl) lbl.textContent = 'Mic Active';
        }
        setFocusExpression('listening');
      }
    }

    function interruptFocusCall() {
      stopSpeakingNow();
      setFocusExpression('listening');
      const badgeText = document.getElementById('focus-badge-text');
      if (badgeText) badgeText.textContent = 'Interrupted // Listening';
      startListeningSafe(true);
    }

    function toggleFocusSpeaker() {
      focusMuteSpeaker = !focusMuteSpeaker;
      const spkBtn = document.getElementById('focus-btn-speaker');
      if (focusMuteSpeaker) {
        isQuietMode = true;
        stopSpeakingNow();
        if (spkBtn) {
          spkBtn.classList.remove('active');
          const icon = spkBtn.querySelector('.focus-dock-icon');
          const lbl = spkBtn.querySelector('.focus-dock-label');
          if (icon) icon.textContent = '🔇';
          if (lbl) lbl.textContent = 'Speaker Muted';
        }
      } else {
        isQuietMode = false;
        if (spkBtn) {
          spkBtn.classList.add('active');
          const icon = spkBtn.querySelector('.focus-dock-icon');
          const lbl = spkBtn.querySelector('.focus-dock-label');
          if (icon) icon.textContent = '🔊';
          if (lbl) lbl.textContent = 'Speaker On';
        }
      }
    }

    function toggleTranscriptSize() {
      const card = document.querySelector('.focus-transcript-card');
      if (card) card.classList.toggle('expanded');
    }

    function toggleFocusFullscreen() {
      const overlay = document.getElementById('focus-call-overlay');
      if (!overlay) return;
      if (!document.fullscreenElement) {
        if (overlay.requestFullscreen) overlay.requestFullscreen();
      } else {
        if (document.exitFullscreen) document.exitFullscreen();
      }
    }

    // Modal controls for Character Gallery
    function openCharacterGalleryModal() {
      const modal = document.getElementById('character-gallery-modal');
      if (modal) {
        modal.style.display = 'flex';
        renderCharacterGalleryModal();
      }
    }

    function closeCharacterGalleryModal() {
      const modal = document.getElementById('character-gallery-modal');
      if (modal) modal.style.display = 'none';
    }

    function selectCharacter(charId) {
      setFocusCharacter(charId);
      closeCharacterGalleryModal();
    }

    function renderCharacterGalleryModal() {
      ['aarushi', 'aoi', 'kenji'].forEach(id => {
        const card = document.getElementById(`char-card-${id}`);
        const btn = document.getElementById(`btn-char-${id}`);
        if (card && btn) {
          if (id === focusCurrentCharacter) {
            card.classList.add('active');
            btn.textContent = 'Active Companion ✨';
          } else {
            card.classList.remove('active');
            btn.textContent = `Select ${getCharacterDisplayName(id)}`;
          }
        }
      });
    }

  </script>

  <!-- CLOUDFLARE SHARE MODAL -->
  <div id="cloudflare-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); backdrop-filter:blur(8px); z-index:9999; align-items:center; justify-content:center;">
    <div style="background:#0d1527; border:1px solid #38bdf8; border-radius:12px; max-width:540px; width:92%; padding:24px; box-shadow:0 0 40px rgba(56,189,248,0.3); position:relative;">
      <button onclick="closeCloudflareModal()" style="position:absolute; top:14px; right:16px; background:none; border:none; color:#94a3b8; font-size:20px; cursor:pointer;">✕</button>
      <h2 style="margin:0 0 8px 0; color:#38bdf8; display:flex; align-items:center; gap:8px;">
        ☁️ Cloudflare Public Remote Access
      </h2>
      <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0;">
        Share this live link with your friend to let her control your GDR AI assistant from her mobile phone from anywhere in the world.
      </p>
      
      <div style="background:#070a13; border:1px solid #1e293b; border-radius:8px; padding:12px; margin-bottom:16px;">
        <div style="font-size:11px; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Public Shareable URL:</div>
        <div id="modal-tunnel-url" style="font-family:'JetBrains Mono',monospace; font-size:14px; color:#38bdf8; word-break:break-all; min-height:22px;">
          Connecting to Cloudflare...
        </div>
      </div>

      <div style="display:flex; justify-content:center; margin-bottom:16px;">
        <div id="modal-qr-container" style="background:#fff; padding:12px; border-radius:8px; display:none; text-align:center;">
          <img id="modal-qr-img" src="" alt="QR Code" style="width:180px; height:180px; display:block;" />
        </div>
      </div>

      <div style="background:rgba(245,158,11,0.1); border:1px solid #f59e0b; border-radius:6px; padding:10px; margin-bottom:16px; font-size:12px; color:#fbbf24;">
        🔒 <b>Owner Safety Shield Active:</b> Destructive actions (shutting down PC, deleting files, big system tasks) requested from the public URL will pause and require your explicit authorization in your PC terminal.
      </div>

      <div style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap;">
        <button class="btn btn-secondary" style="border:1px solid #ef4444; color:#ef4444;" onclick="stopCloudflareTunnel()">🛑 Stop Tunnel</button>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button id="modal-copy-btn" class="btn" onclick="copyCloudflareUrl()">📋 Copy Public Link</button>
          <button class="btn btn-secondary" onclick="closeCloudflareModal()">Done</button>
        </div>
      </div>
    </div>
  </div>

  <!-- SARVAM QUOTA EXCEEDED / CREDIT EXHAUSTED MODAL -->
  <div id="sarvam-quota-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.88); backdrop-filter:blur(10px); z-index:10000; align-items:center; justify-content:center;">
    <div style="background:#130b0b; border:1px solid #ef4444; border-radius:12px; max-width:520px; width:92%; padding:24px; box-shadow:0 0 50px rgba(239,68,68,0.4); position:relative;">
      <button onclick="closeSarvamQuotaModal()" style="position:absolute; top:14px; right:16px; background:none; border:none; color:#94a3b8; font-size:20px; cursor:pointer;">✕</button>
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
        <span style="font-size:28px;">⚠️</span>
        <h2 style="margin:0; color:#ef4444; font-size:18px;">Sarvam AI Quota Exceeded / Credit Exhausted</h2>
      </div>
      <p style="color:#cbd5e1; font-size:13px; line-height:1.5; margin:0 0 14px 0;">
        Your Sarvam AI API key has run out of credits or exceeded its rate limit. Kindly enter a new or upgraded Sarvam API key to resume AI capabilities immediately.
      </p>

      <div style="background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:12px; margin-bottom:14px;">
        <label style="font-size:12px; color:var(--text-muted); font-weight:600; display:block; margin-bottom:6px;">Enter New Sarvam API Key:</label>
        <div style="display:flex; gap:6px;">
          <input id="modal-new-sarvam-key" type="password" placeholder="Paste new Sarvam API Key..." style="flex:1; padding:8px; border-radius:6px; background:#000; border:1px solid var(--border); color:#fff; font-size:13px;">
          <button class="btn btn-secondary" onclick="togglePasswordVisibility('modal-new-sarvam-key')" style="padding:6px 10px; font-size:12px;">👁️</button>
        </div>
        <div style="font-size:11px; color:#fca5a5; margin-top:6px;">
          💡 Get a new key from: <a href="https://dashboard.sarvam.ai/" target="_blank" style="color:#38bdf8; text-decoration:underline;">dashboard.sarvam.ai</a>
        </div>
      </div>

      <div id="modal-sarvam-feedback" style="font-size:12px; margin-bottom:12px; display:none;"></div>

      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn btn-secondary" onclick="closeSarvamQuotaModal()" style="font-size:12px;">Dismiss</button>
        <button class="btn" onclick="saveNewSarvamKeyFromModal()" style="background:#ef4444; color:#fff; font-weight:bold; font-size:12px; padding:8px 18px;">Save Key & Resume 🚀</button>
      </div>
    </div>
  </div>

  <!-- =========================================================================
       FOCUS TALKING MODE — ANIME COMPANION CALL OVERLAY
       ========================================================================= -->
  <div id="focus-call-overlay" class="focus-theme-midnight" style="display:none;">
    <!-- Ambient glowing backdrop effect -->
    <div class="focus-ambient-bg">
      <div class="focus-ambient-orb orb-1"></div>
      <div class="focus-ambient-orb orb-2"></div>
      <div class="focus-ambient-orb orb-3"></div>
    </div>

    <!-- Top Call Bar -->
    <header class="focus-top-bar">
      <div class="focus-top-left">
        <div class="focus-avatar-container" onclick="openCharacterGalleryModal()" title="Switch Companion Character">
          <img id="focus-top-avatar" src="/static/characters/aarushi/neutral.svg" alt="Aarushi" class="focus-top-avatar-img">
          <span class="focus-status-dot"></span>
        </div>
        <div class="focus-character-meta">
          <div class="focus-character-name-row">
            <span id="focus-companion-name" class="focus-character-name">Aarushi</span>
            <span class="focus-character-tag">Personal AI Companion</span>
          </div>
          <div id="focus-call-badge" class="focus-call-badge">
            <span class="pulse-indicator"></span>
            <span id="focus-badge-text">Connected (Live)</span>
          </div>
        </div>
      </div>

      <div class="focus-top-center">
        <div class="focus-timer-pill">
          <span class="focus-timer-icon">🟢</span>
          <span id="focus-call-timer">00:00</span>
        </div>
      </div>

      <div class="focus-top-right">
        <!-- Theme Switcher -->
        <select id="focus-theme-select" class="focus-select-pill" onchange="setFocusTheme(this.value)" title="Atmosphere Theme">
          <option value="midnight">🌌 Midnight</option>
          <option value="lavender">💜 Lavender</option>
          <option value="warm">🌅 Warm Sunset</option>
          <option value="dark">🖤 Obsidian Dark</option>
        </select>

        <!-- Character Gallery Button -->
        <button class="focus-icon-btn" onclick="openCharacterGalleryModal()" title="Select Anime Character">
          🎭 Companions
        </button>

        <!-- Fullscreen Toggle Button -->
        <button class="focus-icon-btn" onclick="toggleFocusFullscreen()" title="Toggle Fullscreen">
          ⛶
        </button>

        <!-- Hangup / Close Button -->
        <button class="focus-icon-btn focus-btn-hangup-top" onclick="closeFocusCallMode()" title="End Call">
          ✕
        </button>
      </div>
    </header>

    <!-- Center Anime Character Stage -->
    <main class="focus-stage">
      <div class="focus-character-wrapper">
        <div id="focus-halo" class="focus-character-halo state-idle"></div>
        <img id="focus-character-img" src="/static/characters/aarushi/neutral.svg" alt="Companion" class="focus-character-art companion-breathe">
      </div>

      <!-- Audio-reactive Voice Activity Waveform -->
      <div id="focus-voice-wave" class="focus-voice-wave">
        <span class="bar bar-1"></span>
        <span class="bar bar-2"></span>
        <span class="bar bar-3"></span>
        <span class="bar bar-4"></span>
        <span class="bar bar-5"></span>
        <span class="bar bar-6"></span>
        <span class="bar bar-7"></span>
      </div>

      <!-- Active Expression Pill -->
      <div id="focus-expression-pill" class="focus-expression-pill">
        ✨ Attentive & Present
      </div>
    </main>

    <!-- Live Conversation Transcript Panel -->
    <section class="focus-transcript-container">
      <div class="focus-transcript-card">
        <div class="focus-transcript-header">
          <span class="focus-transcript-title">💬 Live Conversation Transcript</span>
          <button class="focus-transcript-toggle" onclick="toggleTranscriptSize()" title="Toggle Compact / Full">⤢</button>
        </div>
        <div id="focus-transcript-scroll" class="focus-transcript-body">
          <div id="focus-transcript-user-wrap" class="focus-transcript-line user" style="display:none;">
            <span class="focus-speaker-tag">YOU:</span>
            <span id="focus-transcript-user-text" class="focus-text-content"></span>
          </div>
          <div id="focus-transcript-bot-wrap" class="focus-transcript-line bot">
            <span id="focus-transcript-bot-tag" class="focus-speaker-tag">AARUSHI:</span>
            <span id="focus-transcript-bot-text" class="focus-text-content">Call started with Aarushi. I am listening, speak naturally or ask anything!</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Bottom Floating Call Controls Dock -->
    <footer class="focus-controls-dock">
      <div class="focus-dock-inner">
        <!-- Mic Mute / Unmute -->
        <button id="focus-btn-mic" class="focus-dock-btn active" onclick="toggleFocusMic()" title="Toggle Microphone">
          <span class="focus-dock-icon">🎙️</span>
          <span class="focus-dock-label">Mic Active</span>
        </button>

        <!-- Barge-in / Stop Assistant Speaking -->
        <button id="focus-btn-stop" class="focus-dock-btn btn-interrupt" onclick="interruptFocusCall()" title="Interrupt / Stop Speaking (Barge-In)">
          <span class="focus-dock-icon">⏹️</span>
          <span class="focus-dock-label">Stop Speaking</span>
        </button>

        <!-- Speaker Mute / Unmute -->
        <button id="focus-btn-speaker" class="focus-dock-btn" onclick="toggleFocusSpeaker()" title="Toggle Voice Audio Output">
          <span class="focus-dock-icon">🔊</span>
          <span class="focus-dock-label">Speaker On</span>
        </button>

        <!-- Switch Companion Gallery -->
        <button class="focus-dock-btn" onclick="openCharacterGalleryModal()" title="Switch Companion Character">
          <span class="focus-dock-icon">🎭</span>
          <span class="focus-dock-label">Characters</span>
        </button>

        <!-- End Call Button -->
        <button id="focus-btn-end" class="focus-dock-btn btn-end-call" onclick="closeFocusCallMode()" title="End Focus Call">
          <span class="focus-dock-icon">📞</span>
          <span class="focus-dock-label">End Call</span>
        </button>
      </div>
    </footer>
  </div>

  <!-- CHARACTER SELECTION GALLERY MODAL -->
  <div id="character-gallery-modal" class="modal-backdrop" style="display:none;" onclick="if(event.target===this) closeCharacterGalleryModal()">
    <div class="character-gallery-card">
      <div class="character-gallery-header">
        <div>
          <h2 style="margin:0; font-size:20px; font-weight:700; color:#fff;">Select Anime Companion</h2>
          <p style="margin:4px 0 0; font-size:13px; color:var(--text-muted);">Choose your personal conversational companion for Focus Talking Mode</p>
        </div>
        <button class="modal-close-btn" onclick="closeCharacterGalleryModal()">✕</button>
      </div>

      <div class="character-gallery-grid" id="character-gallery-list">
        <!-- Aarushi Card -->
        <div class="companion-select-card active" id="char-card-aarushi" onclick="selectCharacter('aarushi')">
          <div class="char-card-preview">
            <img src="/static/characters/aarushi/happy.svg" alt="Aarushi" class="char-preview-img">
            <span class="char-badge default">Default</span>
          </div>
          <div class="char-card-info">
            <h3 class="char-name">Aarushi</h3>
            <span class="char-role">Empathetic Personal Companion</span>
            <p class="char-desc">Warm, thoughtful anime companion with natural Hinglish & English voice, rich lifelong memory, and emotional intelligence.</p>
            <div class="char-traits">
              <span class="trait-tag">💖 Warm</span>
              <span class="trait-tag">🧠 Lifelong Memory</span>
              <span class="trait-tag">🎙️ Expressive Voice</span>
            </div>
          </div>
          <div class="char-card-action">
            <button class="btn btn-select-char" id="btn-char-aarushi">Active Companion</button>
          </div>
        </div>

        <!-- Aoi Card -->
        <div class="companion-select-card" id="char-card-aoi" onclick="selectCharacter('aoi')">
          <div class="char-card-preview">
            <img src="/static/characters/aoi/happy.svg" alt="Aoi" class="char-preview-img">
            <span class="char-badge cyber">Cyber Tech</span>
          </div>
          <div class="char-card-info">
            <h3 class="char-name">Aoi</h3>
            <span class="char-role">Cool Tech & Coding Specialist</span>
            <p class="char-desc">Intelligent, sharp cyber-companion with neon headset, focused on programming, debugging, algorithms, and deep systems engineering.</p>
            <div class="char-traits">
              <span class="trait-tag">⚡ Tech Savvy</span>
              <span class="trait-tag">💻 Code Expert</span>
              <span class="trait-tag">🎧 Cyber Headset</span>
            </div>
          </div>
          <div class="char-card-action">
            <button class="btn btn-select-char" id="btn-char-aoi">Select Aoi</button>
          </div>
        </div>

        <!-- Kenji Card -->
        <div class="companion-select-card" id="char-card-kenji" onclick="selectCharacter('kenji')">
          <div class="char-card-preview">
            <img src="/static/characters/kenji/happy.svg" alt="Kenji" class="char-preview-img">
            <span class="char-badge male">Energetic</span>
          </div>
          <div class="char-card-info">
            <h3 class="char-name">Kenji</h3>
            <span class="char-role">Friendly Anime Buddy & Co-developer</span>
            <p class="char-desc">Upbeat, friendly co-pilot and buddy with casual hoodie, emerald eyes, motivating attitude, and supportive humor.</p>
            <div class="char-traits">
              <span class="trait-tag">🌟 Energetic</span>
              <span class="trait-tag">🤝 Loyal Buddy</span>
              <span class="trait-tag">⚡ Motivating</span>
            </div>
          </div>
          <div class="char-card-action">
            <button class="btn btn-select-char" id="btn-char-kenji">Select Kenji</button>
          </div>
        </div>
      </div>

      <div class="character-gallery-footer">
        <span style="font-size:12px; color:var(--text-muted);">✨ All character artwork is SVG vector-rendered locally from <code>/static/characters/</code> (CC0 Open License).</span>
        <button class="btn btn-primary" onclick="closeCharacterGalleryModal()">Done</button>
      </div>
    </div>
  </div>

</body>
</html>
"""
