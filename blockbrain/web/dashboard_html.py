"""Modern ChatGPT-Style Conversational Platform for BlockBrain HUD.
Combines ChatGPT/Claude layout with BlockBrain's visual identity:
Dark glassmorphism, glowing AI orb, real token streaming, tool cards,
inline approvals, screen awareness, terminal canvas, and Option 3 Stealth Prompter.
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>blockbrain_hud</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #06080F;
      --bg-surface: #0A0E1A;
      --bg-glass: rgba(13, 20, 36, 0.65);
      --bg-glass-hover: rgba(19, 30, 54, 0.85);
      --bg-input: rgba(10, 15, 29, 0.85);
      --border-subtle: rgba(56, 189, 248, 0.14);
      --border-glow: rgba(0, 229, 255, 0.35);
      --border-violet: rgba(168, 85, 247, 0.35);

      --cyan-primary: #00E5FF;
      --cyan-glow: rgba(0, 229, 255, 0.28);
      --cyan-dim: rgba(0, 229, 255, 0.12);
      --violet-primary: #A855F7;
      --violet-glow: rgba(168, 85, 247, 0.28);
      --violet-dim: rgba(168, 85, 247, 0.12);
      
      --danger: #EF4444;
      --danger-glow: rgba(239, 68, 68, 0.35);
      --success: #10B981;
      --warning: #F59E0B;

      --text-main: #F8FAFC;
      --text-secondary: #CBD5E1;
      --text-muted: #64748B;
      --text-dim: #475569;

      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-full: 9999px;

      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
      --transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      display: flex;
      background-image: 
        radial-gradient(circle at 0% 0%, rgba(0, 229, 255, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 100% 100%, rgba(168, 85, 247, 0.06) 0%, transparent 50%),
        radial-gradient(circle at 50% 50%, rgba(7, 10, 19, 0.95) 0%, var(--bg-base) 100%);
    }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.2); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--cyan-primary); }

    /* SVG Lucide Icon Base */
    .icon {
      width: 18px; height: 18px; stroke: currentColor; stroke-width: 1.8;
      stroke-linecap: round; stroke-linejoin: round; fill: none; display: inline-block;
      vertical-align: middle; flex-shrink: 0;
    }
    .icon-sm { width: 14px; height: 14px; }
    .icon-lg { width: 22px; height: 22px; }

    /* App Shell Layout */
    .app-shell {
      display: flex;
      width: 100%;
      height: 100%;
      position: relative;
    }

    /* ==============================================================================
       1. LEFT SIDEBAR (Collapsible)
       ============================================================================== */
    aside.sidebar {
      width: 260px;
      height: 100%;
      background: rgba(10, 14, 26, 0.75);
      backdrop-filter: blur(20px);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      transition: width 0.25s ease, transform 0.25s ease;
      z-index: 40;
      flex-shrink: 0;
    }
    aside.sidebar.collapsed {
      width: 60px;
    }
    aside.sidebar.collapsed .hide-on-collapse {
      display: none !important;
    }

    .sidebar-header {
      padding: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .brand-group {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
    }
    .brand-orb-icon {
      width: 28px; height: 28px; border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, #fff 0%, var(--cyan-primary) 50%, var(--violet-primary) 100%);
      box-shadow: 0 0 12px var(--cyan-glow);
      flex-shrink: 0;
    }
    .brand-title {
      font-size: 13px; font-weight: 700; letter-spacing: 1.2px; color: var(--cyan-primary);
      text-transform: uppercase;
    }
    .btn-icon {
      background: transparent; border: none; color: var(--text-muted);
      cursor: pointer; padding: 6px; border-radius: var(--radius-sm);
      display: flex; align-items: center; justify-content: center;
      transition: var(--transition);
    }
    .btn-icon:hover { color: var(--text-main); background: rgba(255, 255, 255, 0.06); }

    /* New Chat Button */
    .sidebar-action-wrap {
      padding: 12px 14px 6px;
    }
    .btn-new-chat {
      width: 100%;
      background: linear-gradient(135deg, rgba(0, 229, 255, 0.15), rgba(168, 85, 247, 0.15));
      border: 1px solid var(--border-glow);
      color: var(--cyan-primary);
      padding: 10px 14px;
      border-radius: var(--radius-md);
      font-size: 13px; font-weight: 600;
      display: flex; align-items: center; justify-content: center; gap: 8px;
      cursor: pointer; transition: var(--transition);
      box-shadow: 0 4px 16px rgba(0, 229, 255, 0.12);
    }
    .btn-new-chat:hover {
      background: linear-gradient(135deg, rgba(0, 229, 255, 0.25), rgba(168, 85, 247, 0.25));
      border-color: var(--cyan-primary);
      color: #fff;
      box-shadow: 0 0 20px var(--cyan-glow);
    }

    /* Search input in sidebar */
    .search-box-wrap {
      padding: 6px 14px;
    }
    .search-input {
      width: 100%;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-sm);
      padding: 6px 10px; font-size: 12px; color: var(--text-main);
      outline: none; transition: var(--transition);
    }
    .search-input:focus {
      border-color: var(--cyan-primary);
      box-shadow: 0 0 10px var(--cyan-glow);
    }

    /* History Groups */
    .chat-history-container {
      flex: 1;
      overflow-y: auto;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .history-group-title {
      font-size: 10px; font-weight: 700; color: var(--text-dim);
      letter-spacing: 1px; text-transform: uppercase; padding: 4px 8px;
    }
    .chat-history-item {
      padding: 8px 10px;
      border-radius: var(--radius-sm);
      display: flex; align-items: center; justify-content: space-between;
      color: var(--text-secondary); font-size: 12px; cursor: pointer;
      transition: var(--transition);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .chat-history-item:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-main);
    }
    .chat-history-item.active {
      background: var(--cyan-dim);
      border: 1px solid rgba(0, 229, 255, 0.25);
      color: var(--cyan-primary);
      font-weight: 600;
    }
    .item-title {
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;
    }
    .item-del-btn {
      opacity: 0; transition: var(--transition); padding: 2px 4px; border-radius: 4px;
    }
    .chat-history-item:hover .item-del-btn { opacity: 0.7; }
    .item-del-btn:hover { opacity: 1; color: var(--danger); }

    /* Bottom Mode Switcher */
    .sidebar-footer {
      border-top: 1px solid rgba(255, 255, 255, 0.04);
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .mode-item {
      display: flex; align-items: center; gap: 10px;
      padding: 8px 10px; border-radius: var(--radius-sm);
      color: var(--text-muted); font-size: 12px; font-weight: 500;
      cursor: pointer; transition: var(--transition);
    }
    .mode-item:hover { color: var(--text-main); background: rgba(255, 255, 255, 0.04); }
    .mode-item.active {
      color: var(--cyan-primary);
      background: var(--cyan-dim);
      font-weight: 600;
    }

    /* ==============================================================================
       2. CENTER MAIN COLUMN
       ============================================================================== */
    main.main-viewport {
      flex: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
    }

    /* Top Bar */
    header.topbar {
      height: 52px;
      background: rgba(10, 14, 26, 0.8);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-subtle);
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 18px;
      z-index: 30;
      flex-shrink: 0;
    }
    .topbar-left {
      display: flex; align-items: center; gap: 12px;
    }
    .chat-title-editable {
      font-size: 13px; font-weight: 600; color: var(--text-main);
      padding: 4px 8px; border-radius: 6px; cursor: text;
      border: 1px solid transparent;
      outline: none; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .chat-title-editable:focus {
      border-color: var(--cyan-primary); background: rgba(0, 0, 0, 0.4);
    }
    .model-badge {
      display: flex; align-items: center; gap: 6px;
      background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 4px 9px; border-radius: var(--radius-full); font-size: 11px; font-weight: 600;
      color: var(--cyan-primary); cursor: pointer;
    }
    .model-badge:hover { border-color: var(--cyan-primary); background: var(--cyan-dim); }

    .topbar-right {
      display: flex; align-items: center; gap: 10px;
    }

    /* Cloak & Option 3 Pill */
    .cloak-pill {
      display: flex; align-items: center; gap: 6px;
      background: rgba(16, 185, 129, 0.12); border: 1px solid var(--success);
      color: var(--success); padding: 4px 10px; border-radius: var(--radius-full);
      font-size: 11px; font-weight: 700; cursor: pointer; transition: var(--transition);
      letter-spacing: 0.5px;
    }
    .cloak-pill:hover { box-shadow: 0 0 12px rgba(16, 185, 129, 0.4); }
    .cloak-pill.off {
      background: rgba(239, 68, 68, 0.12); border-color: var(--danger); color: var(--danger);
    }

    /* Live Telemetry Pill */
    .telemetry-pill {
      display: flex; align-items: center; gap: 8px;
      background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 4px 10px; border-radius: var(--radius-sm); font-size: 11px; font-family: var(--font-mono);
      color: var(--text-secondary); cursor: pointer; transition: var(--transition);
    }
    .telemetry-pill:hover { border-color: var(--cyan-primary); color: var(--cyan-primary); }
    .pill-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--cyan-primary); box-shadow: 0 0 6px var(--cyan-primary); }

    /* Single-Click Red Panic Kill Button */
    .btn-panic-kill {
      background: linear-gradient(135deg, #7F1D1D, #450A0A);
      border: 1px solid var(--danger);
      color: #FECACA;
      padding: 6px 12px; border-radius: var(--radius-sm);
      font-size: 11px; font-weight: 800; letter-spacing: 1px;
      display: flex; align-items: center; gap: 6px;
      cursor: pointer; transition: var(--transition);
    }
    .btn-panic-kill:hover {
      background: var(--danger); color: #fff; box-shadow: 0 0 16px var(--danger-glow);
    }

    /* Right Panel Toggle */
    .btn-canvas-toggle {
      background: transparent; border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-muted); padding: 6px 8px; border-radius: var(--radius-sm);
      cursor: pointer; display: flex; align-items: center; gap: 4px; font-size: 11px;
      transition: var(--transition);
    }
    .btn-canvas-toggle:hover, .btn-canvas-toggle.active {
      color: var(--cyan-primary); border-color: var(--cyan-primary); background: var(--cyan-dim);
    }

    /* ==============================================================================
       3. CONVERSATION COLUMN (~820px Centered)
       ============================================================================== */
    .conversation-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 24px 16px 120px;
      display: flex;
      flex-direction: column;
      align-items: center;
      scroll-behavior: smooth;
    }
    .conversation-column {
      width: 100%;
      max-width: 820px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }

    /* Empty State Hero */
    .empty-state {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-height: 48vh; text-align: center; gap: 20px; margin-top: 20px;
    }
    .hero-orb {
      width: 90px; height: 90px; border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #fff 0%, var(--cyan-primary) 40%, var(--violet-primary) 85%, var(--bg-base) 100%);
      box-shadow: 0 0 40px var(--cyan-glow), inset 0 0 20px rgba(255, 255, 255, 0.6);
      animation: heroOrbFloat 4s ease-in-out infinite alternate, heroOrbBreathe 3s ease-in-out infinite;
      cursor: pointer;
    }
    @keyframes heroOrbFloat { 0% { transform: translateY(0); } 100% { transform: translateY(-8px); } }
    @keyframes heroOrbBreathe { 0%, 100% { box-shadow: 0 0 35px var(--cyan-glow); } 50% { box-shadow: 0 0 65px var(--cyan-glow); } }

    .hero-title {
      font-size: 22px; font-weight: 700; color: #fff; letter-spacing: 0.5px;
    }
    .hero-subtitle {
      font-size: 13px; color: var(--text-muted); max-width: 500px; line-height: 1.5;
    }

    /* Starter Cards Grid */
    .starter-cards-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 12px; width: 100%; margin-top: 10px;
    }
    .starter-card {
      background: var(--bg-glass);
      border: 1px solid var(--border-subtle);
      backdrop-filter: blur(14px);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      text-align: left;
      cursor: pointer; transition: var(--transition);
      display: flex; flex-direction: column; gap: 4px;
    }
    .starter-card:hover {
      background: var(--bg-glass-hover);
      border-color: var(--cyan-primary);
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0, 229, 255, 0.12);
    }
    .starter-card-title {
      font-size: 12px; font-weight: 700; color: var(--cyan-primary); display: flex; align-items: center; gap: 6px;
    }
    .starter-card-desc {
      font-size: 11px; color: var(--text-muted); line-height: 1.4;
    }

    /* Messages */
    .msg-row {
      display: flex; width: 100%; gap: 12px;
      animation: msgFadeIn 0.2s ease-out;
    }
    @keyframes msgFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

    .msg-user {
      justify-content: flex-end;
    }
    .msg-user-bubble {
      max-width: 80%;
      background: rgba(168, 85, 247, 0.16);
      border: 1px solid rgba(168, 85, 247, 0.35);
      border-radius: 18px 18px 4px 18px;
      padding: 12px 18px;
      color: #fff;
      font-size: 14px;
      line-height: 1.5;
      box-shadow: 0 4px 16px rgba(168, 85, 247, 0.1);
      position: relative;
    }
    .user-attachment-thumb {
      max-width: 220px; border-radius: 8px; margin-bottom: 8px; display: block; border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .msg-assistant {
      justify-content: flex-start;
      flex-direction: column;
      width: 100%;
    }
    .msg-assistant-header {
      display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
    }
    .avatar-mini-orb {
      width: 22px; height: 22px; border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #fff 0%, var(--cyan-primary) 50%, var(--violet-primary) 100%);
      box-shadow: 0 0 10px var(--cyan-glow);
      flex-shrink: 0;
    }
    .avatar-mini-orb.thinking { animation: orbSpin 1.4s linear infinite; }
    .avatar-mini-orb.speaking { animation: orbPulseFast 0.8s ease-in-out infinite alternate; }
    @keyframes orbSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes orbPulseFast { 0% { transform: scale(0.95); } 100% { transform: scale(1.1); } }

    .assistant-name { font-size: 12px; font-weight: 700; color: var(--cyan-primary); letter-spacing: 0.5px; }
    .assistant-telemetry { font-size: 10px; color: var(--text-dim); font-family: var(--font-mono); }

    .msg-assistant-body {
      width: 100%;
      font-size: 14px;
      line-height: 1.6;
      color: var(--text-main);
      padding-left: 32px;
    }

    /* Markdown Formats */
    .msg-assistant-body p { margin-bottom: 12px; }
    .msg-assistant-body h1, .msg-assistant-body h2, .msg-assistant-body h3 {
      color: #fff; margin: 16px 0 8px; font-weight: 700;
    }
    .msg-assistant-body h3 { font-size: 15px; color: var(--cyan-primary); }
    .msg-assistant-body ul, .msg-assistant-body ol { margin: 8px 0 14px 24px; }
    .msg-assistant-body li { margin-bottom: 4px; }
    .msg-assistant-body table {
      width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px;
    }
    .msg-assistant-body th, .msg-assistant-body td {
      border: 1px solid var(--border-subtle); padding: 8px 12px; text-align: left;
    }
    .msg-assistant-body th { background: rgba(0, 229, 255, 0.08); color: var(--cyan-primary); }

    /* Code Blocks */
    .code-block-container {
      background: #04060C;
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: var(--radius-md);
      margin: 14px 0;
      overflow: hidden;
      font-family: var(--font-mono);
      font-size: 12px;
    }
    .code-block-header {
      background: rgba(255, 255, 255, 0.03);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      padding: 6px 12px;
      display: flex; align-items: center; justify-content: space-between;
      color: var(--text-muted); font-size: 11px;
    }
    .code-block-actions { display: flex; gap: 8px; }
    .code-action-btn {
      background: transparent; border: none; color: var(--text-muted);
      cursor: pointer; display: flex; align-items: center; gap: 4px; font-size: 11px;
      padding: 3px 6px; border-radius: 4px; transition: var(--transition);
    }
    .code-action-btn:hover { color: var(--cyan-primary); background: var(--cyan-dim); }
    .code-block-content {
      padding: 12px; overflow-x: auto; color: #E2E8F0; line-height: 1.5;
    }

    /* Tool Call Card */
    .tool-call-card {
      background: rgba(13, 20, 36, 0.7);
      border: 1px solid var(--border-subtle);
      border-left: 3px solid var(--cyan-primary);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      margin: 10px 0 10px 32px;
      font-size: 12px;
      display: flex; flex-direction: column; gap: 6px;
    }
    .tool-header {
      display: flex; align-items: center; justify-content: space-between;
      color: var(--cyan-primary); font-weight: 600; cursor: pointer;
    }
    .tool-status-badge {
      font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; text-transform: uppercase;
    }
    .tool-status-badge.running { background: rgba(0, 229, 255, 0.15); color: var(--cyan-primary); }
    .tool-status-badge.done { background: rgba(16, 185, 129, 0.15); color: var(--success); }

    /* Inline Approval Card */
    .approval-card {
      background: rgba(30, 20, 10, 0.7);
      border: 1px solid var(--warning);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      margin: 12px 0 12px 32px;
      display: flex; flex-direction: column; gap: 10px;
    }
    .approval-title {
      font-size: 12px; font-weight: 700; color: var(--warning); display: flex; align-items: center; gap: 6px;
    }
    .approval-content {
      font-size: 12px; color: var(--text-secondary); background: #000; padding: 10px; border-radius: 6px; font-family: var(--font-mono);
    }
    .approval-actions { display: flex; gap: 10px; }
    .btn-approve {
      background: var(--success); color: #000; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer;
    }
    .btn-deny {
      background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); font-weight: 700; padding: 6px 14px; border-radius: 6px; cursor: pointer;
    }

    /* Message Actions Toolbar */
    .msg-actions-toolbar {
      display: flex; gap: 4px; margin-top: 6px; padding-left: 32px; opacity: 0; transition: var(--transition);
    }
    .msg-row:hover .msg-actions-toolbar { opacity: 1; }
    .msg-action-icon {
      background: transparent; border: none; color: var(--text-dim);
      padding: 4px 6px; border-radius: 4px; cursor: pointer; display: flex; align-items: center;
      transition: var(--transition);
    }
    .msg-action-icon:hover { color: var(--cyan-primary); background: rgba(255, 255, 255, 0.05); }

    /* Branch Switcher < 1/2 > */
    .branch-switcher {
      font-size: 10px; color: var(--text-muted); font-family: var(--font-mono); display: flex; align-items: center; gap: 4px;
    }

    /* ==============================================================================
       4. BOTTOM COMPOSER
       ============================================================================== */
    .composer-container {
      position: absolute; bottom: 0; left: 0; right: 0;
      padding: 0 20px 18px;
      display: flex; flex-direction: column; align-items: center;
      background: linear-gradient(to top, var(--bg-base) 70%, transparent 100%);
      pointer-events: none;
      z-index: 25;
    }
    .composer-inner {
      width: 100%; max-width: 820px; pointer-events: auto;
      position: relative;
    }

    /* Slash Command Popup */
    .slash-popup {
      position: absolute; bottom: calc(100% + 8px); left: 0; right: 0;
      background: rgba(10, 14, 26, 0.95); backdrop-filter: blur(20px);
      border: 1px solid var(--border-glow); border-radius: var(--radius-md);
      max-height: 220px; overflow-y: auto; padding: 6px;
      display: none; flex-direction: column; gap: 2px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
    }
    .slash-popup.active { display: flex; }
    .slash-item {
      padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;
      color: var(--text-main); font-size: 12px; cursor: pointer; transition: var(--transition);
    }
    .slash-item:hover, .slash-item.selected {
      background: var(--cyan-dim); color: var(--cyan-primary);
    }
    .slash-cmd-tag { font-family: var(--font-mono); font-weight: 700; color: var(--cyan-primary); }
    .slash-cmd-desc { font-size: 11px; color: var(--text-muted); }

    /* Attachment Preview Strip */
    .composer-attachments-preview {
      display: none; gap: 8px; padding-bottom: 8px; overflow-x: auto;
    }
    .composer-attachments-preview.active { display: flex; }
    .attachment-badge {
      display: flex; align-items: center; gap: 6px; background: rgba(0, 229, 255, 0.1);
      border: 1px solid var(--border-glow); padding: 4px 8px; border-radius: 6px; font-size: 11px; color: var(--cyan-primary);
    }
    .attachment-badge img { width: 20px; height: 20px; border-radius: 4px; object-fit: cover; }
    .attachment-close { cursor: pointer; opacity: 0.6; }
    .attachment-close:hover { opacity: 1; color: var(--danger); }

    /* The Main Glass Box */
    .composer-glass-box {
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      backdrop-filter: blur(24px);
      border-radius: var(--radius-lg);
      padding: 10px 14px;
      display: flex; flex-direction: column; gap: 8px;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
      transition: var(--transition);
    }
    .composer-glass-box:focus-within {
      border-color: var(--border-glow);
      box-shadow: 0 12px 40px rgba(0, 229, 255, 0.15);
    }

    .composer-textarea {
      width: 100%; max-height: 180px; min-height: 24px;
      background: transparent; border: none; outline: none;
      color: #fff; font-size: 14px; line-height: 1.4; resize: none;
      font-family: var(--font-sans);
    }
    .composer-textarea::placeholder { color: var(--text-muted); }

    .composer-controls-row {
      display: flex; align-items: center; justify-content: space-between;
    }
    .composer-left-tools {
      display: flex; align-items: center; gap: 6px;
    }

    .tool-btn {
      background: transparent; border: none; color: var(--text-muted);
      padding: 6px; border-radius: var(--radius-sm); cursor: pointer;
      display: flex; align-items: center; gap: 4px; font-size: 12px; transition: var(--transition);
    }
    .tool-btn:hover { color: var(--cyan-primary); background: rgba(255, 255, 255, 0.06); }
    .tool-btn.active { color: var(--cyan-primary); background: var(--cyan-dim); }

    /* Live Waveform Canvas on Mic */
    .mic-wave-canvas {
      width: 40px; height: 16px; display: none; margin-left: 4px;
    }
    .mic-wave-canvas.active { display: block; }

    .composer-right-actions {
      display: flex; align-items: center; gap: 8px;
    }

    /* Send / Stop Button */
    .btn-send-stop {
      width: 32px; height: 32px; border-radius: 50%;
      background: var(--cyan-primary); color: #000;
      border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: var(--transition); box-shadow: 0 2px 10px var(--cyan-glow);
    }
    .btn-send-stop:hover { transform: scale(1.05); }
    .btn-send-stop.stop {
      background: var(--danger); color: #fff; box-shadow: 0 2px 10px var(--danger-glow);
    }

    /* ==============================================================================
       5. RIGHT PANEL (Toggleable Canvas / Artifacts)
       ============================================================================== */
    aside.right-panel {
      width: 380px;
      height: 100%;
      background: rgba(10, 14, 26, 0.85);
      backdrop-filter: blur(20px);
      border-left: 1px solid var(--border-subtle);
      display: flex; flex-direction: column;
      transition: width 0.25s ease, transform 0.25s ease;
      z-index: 35;
      flex-shrink: 0;
    }
    aside.right-panel.hidden {
      display: none;
    }

    .right-panel-header {
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      display: flex; align-items: center; justify-content: space-between;
    }
    .panel-tabs-segmented {
      display: flex; background: rgba(255, 255, 255, 0.04); padding: 3px; border-radius: var(--radius-sm);
    }
    .seg-tab {
      padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; color: var(--text-muted);
      cursor: pointer; border: none; background: transparent; transition: var(--transition);
    }
    .seg-tab.active {
      color: #000; background: var(--cyan-primary);
    }

    .right-panel-body {
      flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 14px;
    }

    /* Embedded Terminal */
    .terminal-container {
      background: #020408; border: 1px solid rgba(56, 189, 248, 0.2); border-radius: var(--radius-sm);
      height: 100%; display: flex; flex-direction: column; font-family: var(--font-mono); font-size: 12px;
    }
    .terminal-output {
      flex: 1; padding: 10px; overflow-y: auto; color: #38BDF8; white-space: pre-wrap; line-height: 1.4;
    }
    .terminal-input-row {
      display: flex; align-items: center; padding: 8px 10px; border-top: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.02);
    }
    .terminal-prompt { color: var(--cyan-primary); margin-right: 6px; font-weight: 700; }
    .terminal-cmd-input {
      flex: 1; background: transparent; border: none; color: #fff; font-family: var(--font-mono); font-size: 12px; outline: none;
    }

    /* Option 3 Prompter Card inside Copilot Panel */
    .option3-prompter-box {
      background: linear-gradient(135deg, rgba(0, 229, 255, 0.1), rgba(168, 85, 247, 0.1));
      border: 1px solid var(--border-glow); border-radius: var(--radius-md); padding: 14px;
      display: flex; flex-direction: column; gap: 8px;
    }
    .option3-title { font-size: 12px; font-weight: 700; color: var(--cyan-primary); display: flex; align-items: center; gap: 6px; }
    .option3-url-pill {
      display: flex; align-items: center; justify-content: space-between; background: rgba(0, 0, 0, 0.5);
      padding: 6px 10px; border-radius: 6px; font-family: var(--font-mono); font-size: 11px; color: var(--cyan-primary);
    }

    /* ==============================================================================
       6. MODALS & OVERLAYS
       ============================================================================== */
    /* Command Palette (Ctrl+K) */
    .palette-backdrop {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(10px);
      display: none; align-items: flex-start; justify-content: center; padding-top: 15vh; z-index: 100;
    }
    .palette-backdrop.active { display: flex; }
    .palette-modal {
      width: 540px; background: rgba(10, 14, 26, 0.95); border: 1px solid var(--border-glow);
      border-radius: var(--radius-md); box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
      display: flex; flex-direction: column; overflow: hidden;
    }
    .palette-input {
      padding: 14px 18px; background: transparent; border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      color: #fff; font-size: 14px; outline: none;
    }
    .palette-list {
      max-height: 280px; overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px;
    }
    .palette-entry {
      padding: 10px 14px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;
      color: var(--text-secondary); font-size: 13px; cursor: pointer; transition: var(--transition);
    }
    .palette-entry:hover, .palette-entry.selected {
      background: var(--cyan-dim); color: var(--cyan-primary);
    }
    .palette-shortcut-badge {
      font-size: 10px; font-family: var(--font-mono); background: rgba(255, 255, 255, 0.08);
      padding: 2px 6px; border-radius: 4px; color: var(--text-muted);
    }

    /* Hardware Telemetry Modal */
    .modal-backdrop {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(10px);
      display: none; align-items: center; justify-content: center; z-index: 100;
    }
    .modal-backdrop.active { display: flex; }
    .modal-dialog {
      width: 480px; background: rgba(10, 14, 26, 0.95); border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md); padding: 20px; display: flex; flex-direction: column; gap: 14px;
    }
    .modal-header { display: flex; align-items: center; justify-content: space-between; }
    .modal-title { font-size: 14px; font-weight: 700; color: var(--cyan-primary); }

    /* Fullscreen Voice Mode Overlay */
    .voice-overlay {
      position: fixed; inset: 0; background: rgba(6, 8, 15, 0.95); backdrop-filter: blur(25px);
      display: none; flex-direction: column; align-items: center; justify-content: center; z-index: 90;
      gap: 30px;
    }
    .voice-overlay.active { display: flex; }
    .voice-large-orb {
      width: 180px; height: 180px; border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #fff 0%, var(--cyan-primary) 40%, var(--violet-primary) 85%, var(--bg-base) 100%);
      box-shadow: 0 0 60px var(--cyan-glow);
      animation: voiceOrbPulse 1.2s ease-in-out infinite alternate;
    }
    @keyframes voiceOrbPulse { 0% { transform: scale(0.96); } 100% { transform: scale(1.06); } }
    .voice-status-label { font-size: 16px; font-weight: 700; color: var(--cyan-primary); letter-spacing: 2px; }
    .voice-transcript-preview { font-size: 15px; color: var(--text-secondary); max-width: 600px; text-align: center; }
  </style>
</head>
<body>

  <div class="app-shell">

    <!-- ==============================================================================
         1. LEFT SIDEBAR
         ============================================================================== -->
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <div class="brand-group" onclick="showNewChat()">
          <div class="brand-orb-icon"></div>
          <span class="brand-title hide-on-collapse">BLOCKBRAIN</span>
        </div>
        <button class="btn-icon" onclick="toggleSidebar()" title="Toggle Sidebar">
          <svg class="icon"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
        </button>
      </div>

      <div class="sidebar-action-wrap hide-on-collapse">
        <button class="btn-new-chat" onclick="showNewChat()">
          <svg class="icon"><path d="M12 5v14M5 12h14"/></svg>
          <span>New Chat</span>
        </button>
      </div>

      <div class="search-box-wrap hide-on-collapse">
        <input type="text" class="search-input" id="search-chats-input" placeholder="Search conversations..." oninput="filterConversations()">
      </div>

      <!-- History List -->
      <div class="chat-history-container" id="chat-history-list">
        <!-- Rendered dynamically -->
      </div>

      <!-- Bottom Modes & Settings -->
      <div class="sidebar-footer">
        <div class="mode-item active" onclick="switchMode('chat')">
          <svg class="icon"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span class="hide-on-collapse">Chat Platform</span>
        </div>
        <div class="mode-item" onclick="switchMode('copilot')">
          <svg class="icon"><path d="M12 2v20M2 12h20"/><circle cx="12" cy="12" r="3"/></svg>
          <span class="hide-on-collapse">Stealth Copilot</span>
        </div>
        <div class="mode-item" onclick="switchMode('tasks')">
          <svg class="icon"><rect width="18" height="18" x="3" y="4" rx="2"/><path d="m9 10 2 2 4-4"/></svg>
          <span class="hide-on-collapse">Tasks & Cron</span>
        </div>
        <div class="mode-item" onclick="switchMode('approvals')">
          <svg class="icon"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <span class="hide-on-collapse">Approvals Queue</span>
        </div>
        <div class="mode-item" onclick="switchMode('memory')">
          <svg class="icon"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/></svg>
          <span class="hide-on-collapse">Memory Store</span>
        </div>
        <div class="mode-item" onclick="switchMode('terminal')">
          <svg class="icon"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>
          <span class="hide-on-collapse">Terminal Shell</span>
        </div>
      </div>
    </aside>

    <!-- ==============================================================================
         2. CENTER VIEWPORT
         ============================================================================== -->
    <main class="main-viewport">

      <!-- Top Bar -->
      <header class="topbar">
        <div class="topbar-left">
          <div class="chat-title-editable" id="current-chat-title" contenteditable="true" spellcheck="false" onblur="saveCurrentChatTitle()">
            New Conversation
          </div>
          <div class="model-badge" onclick="openModelPicker()">
            <span id="active-model-name">Sarvam 105B</span>
            <svg class="icon icon-sm"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
        </div>

        <div class="topbar-right">
          <!-- Option 3 Cloak Pill -->
          <div class="cloak-pill" id="cloak-status-pill" onclick="toggleCloakOption3()" title="Off-Screen Mobile Prompter (100% Invisible to Google Meet)">
            <svg class="icon icon-sm"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
            <span id="cloak-status-text">CLOAK: OPTION 3 READY</span>
          </div>

          <!-- Hardware Telemetry Pill -->
          <div class="telemetry-pill" onclick="openHardwareModal()">
            <div class="pill-dot"></div>
            <span id="top-vram-text">VRAM: 940/3800 MB</span>
          </div>

          <!-- Red Single-Click Panic Button -->
          <button class="btn-panic-kill" onclick="triggerPanicKill()" title="Emergency Halt All Daemons and Speech">
            <svg class="icon icon-sm"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
            <span>PANIC KILL</span>
          </button>

          <!-- Toggle Right Canvas -->
          <button class="btn-canvas-toggle" id="canvas-toggle-btn" onclick="toggleRightPanel()" title="Toggle Canvas / Artifacts Panel">
            <svg class="icon"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M15 3v18"/></svg>
          </button>
        </div>
      </header>

      <!-- Center Conversation Scroll Area -->
      <div class="conversation-scroll" id="conversation-scroll">
        <div class="conversation-column" id="conversation-column">

          <!-- Empty State (Shown when no messages) -->
          <div class="empty-state" id="empty-state">
            <div class="hero-orb" onclick="startVoiceOverlay()" title="Click to speak hands-free"></div>
            <div class="hero-title">How can BlockBrain assist your workflow?</div>
            <div class="hero-subtitle">
              Deep desktop control, screen question solving, scheduled task automation, and private neural copilot.
            </div>

            <!-- 4 Starter Cards -->
            <div class="starter-cards-grid">
              <div class="starter-card" onclick="triggerStarterPrompt('⚡ Solve the technical problem or coding question currently visible on my screen.')">
                <div class="starter-card-title">
                  <svg class="icon icon-sm"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                  <span>Solve Current Screen</span>
                </div>
                <div class="starter-card-desc">Capture display, extract question & formulate elite code solution.</div>
              </div>

              <div class="starter-card" onclick="triggerStarterPrompt('Schedule a task for me: in 15 minutes remind me to stretch and drink water.')">
                <div class="starter-card-title">
                  <svg class="icon icon-sm"><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
                  <span>Schedule Task</span>
                </div>
                <div class="starter-card-desc">Natural language cron routines and persistent SQLite alarms.</div>
              </div>

              <div class="starter-card" onclick="triggerStarterPrompt('Enable private earphone whispering mode and monitor screen silently.')">
                <div class="starter-card-title">
                  <svg class="icon icon-sm"><path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/></svg>
                  <span>Whispering Copilot</span>
                </div>
                <div class="starter-card-desc">Answers spoken directly to Bluetooth earpiece without meeting leak.</div>
              </div>

              <div class="starter-card" onclick="triggerStarterPrompt('Run comprehensive system doctor diagnostics on audio, GPU VRAM, and neural models.')">
                <div class="starter-card-title">
                  <svg class="icon icon-sm"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                  <span>System Diagnostics</span>
                </div>
                <div class="starter-card-desc">Check PipeWire gain, faster-whisper STT, Piper TTS, and RTX 3050 VRAM.</div>
              </div>
            </div>
          </div>

          <!-- Messages stream container -->
          <div id="messages-container" style="display: flex; flex-direction: column; gap: 20px;"></div>

        </div>
      </div>

      <!-- Bottom Composer -->
      <div class="composer-container">
        <div class="composer-inner">

          <!-- Slash Command Popup -->
          <div class="slash-popup" id="slash-popup">
            <div class="slash-item" onclick="applySlashCommand('/screen')">
              <span class="slash-cmd-tag">/screen</span>
              <span class="slash-cmd-desc">Analyze and solve active screen context</span>
            </div>
            <div class="slash-item" onclick="applySlashCommand('/task ')">
              <span class="slash-cmd-tag">/task</span>
              <span class="slash-cmd-desc">Schedule a future routine ("in 15m water")</span>
            </div>
            <div class="slash-item" onclick="applySlashCommand('/terminal ')">
              <span class="slash-cmd-tag">/terminal</span>
              <span class="slash-cmd-desc">Execute bash shell command safely</span>
            </div>
            <div class="slash-item" onclick="applySlashCommand('/remember ')">
              <span class="slash-cmd-tag">/remember</span>
              <span class="slash-cmd-desc">Store preference in long-term memory</span>
            </div>
            <div class="slash-item" onclick="applySlashCommand('/diagnostics')">
              <span class="slash-cmd-tag">/diagnostics</span>
              <span class="slash-cmd-desc">Run system health PASS/FAIL check</span>
            </div>
            <div class="slash-item" onclick="applySlashCommand('/cloak')">
              <span class="slash-cmd-tag">/cloak</span>
              <span class="slash-cmd-desc">Toggle Option 3 off-screen stealth mode</span>
            </div>
            <div class="slash-item" onclick="applySlashCommand('/whisper')">
              <span class="slash-cmd-tag">/whisper</span>
              <span class="slash-cmd-desc">Toggle earphone whispering TTS</span>
            </div>
          </div>

          <!-- Attachment Preview Strip -->
          <div class="composer-attachments-preview" id="attachments-preview">
            <!-- Dynamically populated (e.g. screen snapshot) -->
          </div>

          <!-- Glass Input Box -->
          <div class="composer-glass-box">
            <textarea 
              class="composer-textarea" 
              id="user-prompt-input" 
              placeholder="Ask anything, type / for quick tools, or speak..." 
              rows="1"
              oninput="handleComposerInput(this)"
              onkeydown="handleComposerKey(event)"
            ></textarea>

            <div class="composer-controls-row">
              <div class="composer-left-tools">
                <!-- Screen awareness button -->
                <button class="tool-btn" onclick="attachScreenCapture()" title="Ask about my active screen">
                  <svg class="icon"><rect width="18" height="14" x="3" y="3" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
                  <span>Screen</span>
                </button>

                <!-- File Attach -->
                <label class="tool-btn" title="Attach file or code">
                  <svg class="icon"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                  <input type="file" id="file-attach-input" style="display:none;" onchange="handleFileAttach(this)">
                </label>

                <!-- Voice Mic with Live Waveform -->
                <button class="tool-btn" id="mic-tool-btn" onclick="toggleVoiceInput()" title="Voice Input (Whisper STT)">
                  <svg class="icon"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/></svg>
                  <canvas class="mic-wave-canvas" id="mic-canvas"></canvas>
                </button>
              </div>

              <div class="composer-right-actions">
                <button class="btn-send-stop" id="btn-send-stop" onclick="handleSendOrStop()" title="Send prompt (Enter)">
                  <svg class="icon icon-sm" id="send-icon"><line x1="22" x2="11" y1="2" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                  <svg class="icon icon-sm" id="stop-icon" style="display:none;"><rect width="12" height="12" x="6" y="6" rx="2"/></svg>
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>

    </main>

    <!-- ==============================================================================
         3. RIGHT CANVAS / ARTIFACTS PANEL
         ============================================================================== -->
    <aside class="right-panel" id="right-panel">
      <div class="right-panel-header">
        <div class="panel-tabs-segmented">
          <button class="seg-tab active" onclick="switchRightTab('copilot')">Copilot</button>
          <button class="seg-tab" onclick="switchRightTab('terminal')">Terminal</button>
          <button class="seg-tab" onclick="switchRightTab('tasks')">Tasks</button>
          <button class="seg-tab" onclick="switchRightTab('memory')">Memory</button>
        </div>
        <button class="btn-icon" onclick="toggleRightPanel()" title="Close panel">
          <svg class="icon"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
        </button>
      </div>

      <div class="right-panel-body" id="right-panel-body">
        <!-- Tab: Copilot (Stealth Solution + Option 3 Teleprompter Box) -->
        <div id="tab-content-copilot">
          <div class="option3-prompter-box">
            <div class="option3-title">
              <svg class="icon icon-sm"><path d="M12 18h.01M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"/></svg>
              <span>OPTION 3: 100% INVISIBLE PROMPTER</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">
              Open on your phone/tablet placed beside your laptop. Physically impossible for Google Meet/Zoom to see your off-screen device!
            </div>
            <div class="option3-url-pill">
              <span id="option3-url-text">http://localhost:8844/stealth</span>
              <button class="btn-icon" onclick="copyOption3Url()" title="Copy URL">
                <svg class="icon icon-sm"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
              </button>
            </div>
          </div>

          <div style="margin-top: 14px; display: flex; flex-direction: column; gap: 10px;" id="copilot-solution-container">
            <div style="font-size: 12px; font-weight: 700; color: var(--cyan-primary);">LATEST SCREEN SOLUTION</div>
            <div style="font-size: 11px; color: var(--text-muted); font-style: italic;" id="copilot-question-text">
              Standing by. Tap ⚡ Solve Current Screen to analyze.
            </div>
            <div id="copilot-solution-cards"></div>
          </div>
        </div>

        <!-- Tab: Terminal -->
        <div id="tab-content-terminal" style="display: none; height: 100%;">
          <div class="terminal-container">
            <div class="terminal-output" id="term-output">⚡ BlockBrain Shell Console ready. Type commands below...</div>
            <div class="terminal-input-row">
              <span class="terminal-prompt">&gt;</span>
              <input type="text" class="terminal-cmd-input" id="term-input" placeholder="e.g. ls -la, nvidia-smi" onkeydown="handleTerminalEnter(event)">
            </div>
          </div>
        </div>

        <!-- Tab: Tasks -->
        <div id="tab-content-tasks" style="display: none;">
          <div style="font-size: 12px; font-weight: 700; color: var(--cyan-primary); margin-bottom: 8px;">SCHEDULED ROUTINES</div>
          <div id="tasks-list-container" style="display: flex; flex-direction: column; gap: 8px;"></div>
        </div>

        <!-- Tab: Memory -->
        <div id="tab-content-memory" style="display: none;">
          <div style="font-size: 12px; font-weight: 700; color: var(--cyan-primary); margin-bottom: 8px;">PERSISTENT MEMORY ENTRIES</div>
          <div id="memory-list-container" style="display: flex; flex-direction: column; gap: 8px;"></div>
        </div>
      </div>
    </aside>

  </div>

  <!-- Command Palette Modal (Ctrl+K) -->
  <div class="palette-backdrop" id="palette-backdrop" onclick="closePalette(event)">
    <div class="palette-modal" onclick="event.stopPropagation()">
      <input type="text" class="palette-input" id="palette-search" placeholder="Type a command or search (e.g. /screen, /task, clear, panic)..." oninput="filterPalette()">
      <div class="palette-list" id="palette-list">
        <div class="palette-entry" onclick="execPalette('/screen')">
          <span>⚡ Solve Screen Question Now</span>
          <span class="palette-shortcut-badge">/screen</span>
        </div>
        <div class="palette-entry" onclick="execPalette('/cloak')">
          <span>🛡️ Toggle Option 3 Cloak</span>
          <span class="palette-shortcut-badge">/cloak</span>
        </div>
        <div class="palette-entry" onclick="execPalette('/whisper')">
          <span>🎧 Toggle Earphone Whisper Mode</span>
          <span class="palette-shortcut-badge">/whisper</span>
        </div>
        <div class="palette-entry" onclick="execPalette('panic')">
          <span>🚨 Panic Kill Switch</span>
          <span class="palette-shortcut-badge">panic</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Hardware Modal -->
  <div class="modal-backdrop" id="hardware-modal" onclick="closeHardwareModal(event)">
    <div class="modal-dialog" onclick="event.stopPropagation()">
      <div class="modal-header">
        <span class="modal-title">NVIDIA RTX 3050 & HARDWARE TELEMETRY</span>
        <button class="btn-icon" onclick="closeHardwareModal()"><svg class="icon"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg></button>
      </div>
      <div style="font-size: 12px; line-height: 1.5; color: var(--text-secondary);" id="hardware-modal-details">
        Loading telemetry...
      </div>
    </div>
  </div>

  <!-- Fullscreen Voice Mode Overlay -->
  <div class="voice-overlay" id="voice-overlay" onclick="closeVoiceOverlay()">
    <div class="voice-large-orb" id="voice-orb"></div>
    <div class="voice-status-label" id="voice-status-text">LISTENING...</div>
    <div class="voice-transcript-preview" id="voice-transcript-text">"Hey Jarvis" or speak naturally...</div>
    <div style="font-size: 11px; color: var(--text-muted);">Tap anywhere to close voice overlay</div>
  </div>

  <!-- ==============================================================================
       JAVASCRIPT PLATFORM ENGINE
       ============================================================================== -->
  <script>
    // App State
    let activeConversationId = null;
    let conversations = [];
    let isStreaming = false;
    let abortController = null;
    let ws = null;
    let attachedScreenB64 = null;
    let currentRightTab = 'copilot';

    // Model options
    const MODELS = [
      { id: 'sarvam-105b', name: 'Sarvam 105B (Primary)', safe: true },
      { id: 'qwen2.5-local', name: 'Ollama Qwen2.5 (Local CPU)', safe: true },
      { id: 'claude-3-5-sonnet', name: 'Claude 3.5 Sonnet', safe: true },
      { id: 'gpt-4o', name: 'OpenAI GPT-4o', safe: true }
    ];
    let selectedModel = MODELS[0].id;

    // Initialize on page load
    window.addEventListener('DOMContentLoaded', async () => {
      initWebSocket();
      await loadConversations();
      await fetchTelemetry();
      initKeyboardShortcuts();
      updateLanIp();
      setInterval(fetchTelemetry, 4000);
    });

    // 1. WebSocket for real-time Orb & Stealth updates
    function initWebSocket() {
      const loc = window.location;
      const wsUrl = (loc.protocol === 'https:' ? 'wss://' : 'ws://') + loc.host + '/ws';
      ws = new WebSocket(wsUrl);

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'stealth_solution') {
            renderCopilotSolution(msg.data);
          } else if (msg.type === 'orb_update') {
            updateOrbIndicator(msg.data.orb_state);
          }
        } catch (_) {}
      };
      ws.onclose = () => { setTimeout(initWebSocket, 3000); };
    }

    // 2. Conversation Management
    async function loadConversations() {
      try {
        const res = await fetch('/api/conversations');
        conversations = await res.json();
        renderConversationList();
        if (conversations.length > 0 && !activeConversationId) {
          selectConversation(conversations[0].id);
        } else if (conversations.length === 0) {
          showNewChat();
        }
      } catch (e) {
        conversations = [];
        renderConversationList();
      }
    }

    function renderConversationList() {
      const listEl = document.getElementById('chat-history-list');
      if (!listEl) return;
      listEl.innerHTML = '';

      if (conversations.length === 0) {
        listEl.innerHTML = '<div style="font-size:11px; color:var(--text-dim); padding:8px;">No chats yet.</div>';
        return;
      }

      // Group: Today
      const title = document.createElement('div');
      title.className = 'history-group-title';
      title.innerText = 'Recent Chats';
      listEl.appendChild(title);

      conversations.forEach(c => {
        const item = document.createElement('div');
        item.className = 'chat-history-item' + (c.id === activeConversationId ? ' active' : '');
        item.onclick = () => selectConversation(c.id);
        item.innerHTML = `
          <span class="item-title">${escapeHtml(c.title || 'Untitled Chat')}</span>
          <span class="item-del-btn" onclick="deleteConversation(event, '${c.id}')" title="Delete">
            <svg class="icon icon-sm"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
          </span>
        `;
        listEl.appendChild(item);
      });
    }

    function showNewChat() {
      activeConversationId = null;
      document.getElementById('current-chat-title').innerText = 'New Conversation';
      document.getElementById('messages-container').innerHTML = '';
      document.getElementById('empty-state').style.display = 'flex';
      renderConversationList();
    }

    function selectConversation(id) {
      activeConversationId = id;
      const conv = conversations.find(c => c.id === id);
      if (!conv) return;

      document.getElementById('current-chat-title').innerText = conv.title || 'Conversation';
      const container = document.getElementById('messages-container');
      container.innerHTML = '';

      if (!conv.messages || conv.messages.length === 0) {
        document.getElementById('empty-state').style.display = 'flex';
      } else {
        document.getElementById('empty-state').style.display = 'none';
        conv.messages.forEach(m => appendMessageToDom(m.role, m.content, m.attachment, m.engine_info));
      }

      renderConversationList();
      scrollToBottom();
    }

    async function deleteConversation(e, id) {
      e.stopPropagation();
      await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
      conversations = conversations.filter(c => c.id !== id);
      if (activeConversationId === id) {
        showNewChat();
      } else {
        renderConversationList();
      }
    }

    async function saveCurrentChatTitle() {
      const title = document.getElementById('current-chat-title').innerText.trim() || 'Conversation';
      if (!activeConversationId) return;
      const conv = conversations.find(c => c.id === activeConversationId);
      if (conv) {
        conv.title = title;
        await fetch('/api/conversations', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(conv)
        });
        renderConversationList();
      }
    }

    // 3. Message Streaming & Sending
    async function handleSendOrStop() {
      if (isStreaming) {
        if (abortController) abortController.abort();
        setStreamingUi(false);
        return;
      }

      const input = document.getElementById('user-prompt-input');
      const text = input.value.trim();
      if (!text && !attachedScreenB64) return;

      input.value = '';
      input.style.height = '24px';
      document.getElementById('empty-state').style.display = 'none';

      // Attachments
      const attachment = attachedScreenB64;
      clearAttachmentPreview();

      // Append user message
      appendMessageToDom('user', text, attachment);
      saveMessageToActiveConv('user', text, attachment);

      // Create assistant container
      const assistantEl = createAssistantMessageElement();
      const bodyEl = assistantEl.querySelector('.msg-assistant-body');
      setStreamingUi(true);

      abortController = new AbortController();

      try {
        const res = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: text, model: selectedModel }),
          signal: abortController.signal
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullReply = '';
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop(); // keep remainder

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'token') {
                  fullReply += data.token;
                  bodyEl.innerHTML = renderMarkdown(fullReply);
                  scrollToBottom();
                } else if (data.type === 'tool_start') {
                  renderToolCard(assistantEl, data.tool, data.desc, 'running');
                } else if (data.type === 'tool_end') {
                  renderToolCard(assistantEl, data.tool, data.desc, 'done');
                } else if (data.type === 'done') {
                  fullReply = data.reply;
                  bodyEl.innerHTML = renderMarkdown(fullReply);
                  if (data.engine_info) {
                    assistantEl.querySelector('.assistant-telemetry').innerText = `${data.engine_info.llm_model} • ${data.engine_info.timestamp}`;
                  }
                }
              } catch (_) {}
            }
          }
        }

        saveMessageToActiveConv('assistant', fullReply);
      } catch (err) {
        if (err.name !== 'AbortError') {
          bodyEl.innerHTML = `<span style="color:var(--danger)">Error streaming response: ${err.message}</span>`;
        }
      } finally {
        setStreamingUi(false);
        attachCodeBlockActions(bodyEl);
      }
    }

    function setStreamingUi(streaming) {
      isStreaming = streaming;
      document.getElementById('send-icon').style.display = streaming ? 'none' : 'block';
      document.getElementById('stop-icon').style.display = streaming ? 'block' : 'none';
      const btn = document.getElementById('btn-send-stop');
      if (streaming) btn.classList.add('stop'); else btn.classList.remove('stop');
    }

    function appendMessageToDom(role, content, attachment, engine_info) {
      const container = document.getElementById('messages-container');
      if (role === 'user') {
        const row = document.createElement('div');
        row.className = 'msg-row msg-user';
        let attachHtml = '';
        if (attachment) {
          attachHtml = `<img src="${attachment}" class="user-attachment-thumb" alt="Attachment">`;
        }
        row.innerHTML = `
          <div class="msg-user-bubble">
            ${attachHtml}
            <div>${escapeHtml(content)}</div>
          </div>
        `;
        container.appendChild(row);
      } else {
        const row = document.createElement('div');
        row.className = 'msg-row msg-assistant';
        const modelStr = engine_info ? `${engine_info.llm_model} • ${engine_info.timestamp}` : 'Sarvam 105B • Just now';
        row.innerHTML = `
          <div class="msg-assistant-header">
            <div class="avatar-mini-orb"></div>
            <span class="assistant-name">BLOCKBRAIN AI</span>
            <span class="assistant-telemetry">${modelStr}</span>
          </div>
          <div class="msg-assistant-body">${renderMarkdown(content)}</div>
          <div class="msg-actions-toolbar">
            <button class="msg-action-icon" onclick="copyText(this, \`${escapeJs(content)}\`)" title="Copy"><svg class="icon icon-sm"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg></button>
            <button class="msg-action-icon" onclick="speakText(\`${escapeJs(content)}\`)" title="Read Aloud (Piper TTS)"><svg class="icon icon-sm"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg></button>
          </div>
        `;
        container.appendChild(row);
        attachCodeBlockActions(row);
      }
      scrollToBottom();
    }

    function createAssistantMessageElement() {
      const container = document.getElementById('messages-container');
      const row = document.createElement('div');
      row.className = 'msg-row msg-assistant';
      row.innerHTML = `
        <div class="msg-assistant-header">
          <div class="avatar-mini-orb thinking"></div>
          <span class="assistant-name">BLOCKBRAIN AI</span>
          <span class="assistant-telemetry">Generating...</span>
        </div>
        <div class="msg-assistant-body"></div>
      `;
      container.appendChild(row);
      scrollToBottom();
      return row;
    }

    function saveMessageToActiveConv(role, content, attachment) {
      if (!activeConversationId) {
        activeConversationId = 'conv_' + Date.now();
        const newConv = {
          id: activeConversationId,
          title: content.slice(0, 32) || 'New Conversation',
          createdAt: new Date().toISOString(),
          messages: [{ role, content, attachment }]
        };
        conversations.unshift(newConv);
        fetch('/api/conversations', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(newConv)
        });
        document.getElementById('current-chat-title').innerText = newConv.title;
        renderConversationList();
      } else {
        const conv = conversations.find(c => c.id === activeConversationId);
        if (conv) {
          if (!conv.messages) conv.messages = [];
          conv.messages.push({ role, content, attachment });
          fetch('/api/conversations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(conv)
          });
        }
      }
    }

    // 4. Markdown & Code Blocks
    function renderMarkdown(md) {
      if (!md) return '';
      // Escape script tags
      let html = md.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');

      // Headers
      html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
      html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
      html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

      // Code blocks ```lang\ncode\n```
      html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/gm, (match, lang, code) => {
        const cleanLang = lang.trim() || 'code';
        return `
          <div class="code-block-container">
            <div class="code-block-header">
              <span>${cleanLang}</span>
              <div class="code-block-actions">
                <button class="code-action-btn" onclick="copyCode(this)"><svg class="icon icon-sm"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg> Copy</button>
                <button class="code-action-btn" onclick="runCodeInTerminal(this)"><svg class="icon icon-sm"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run</button>
              </div>
            </div>
            <pre class="code-block-content"><code>${escapeHtml(code.trim())}</code></pre>
          </div>
        `;
      });

      // Inline code
      html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08); padding:2px 5px; border-radius:4px; font-family:var(--font-mono); font-size:12px; color:var(--cyan-primary);">$1</code>');

      // Bold & Italic
      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

      // Bullet lists
      html = html.replace(/^\s*• (.*$)/gim, '<li>$1</li>');
      html = html.replace(/^\s*- (.*$)/gim, '<li>$1</li>');
      html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');

      // Newlines to p
      return html;
    }

    function attachCodeBlockActions(parent) {
      // Setup copy listeners
    }

    function copyCode(btn) {
      const code = btn.closest('.code-block-container').querySelector('code').innerText;
      navigator.clipboard.writeText(code);
      const orig = btn.innerHTML;
      btn.innerHTML = 'Copied!';
      setTimeout(() => { btn.innerHTML = orig; }, 1500);
    }

    async function runCodeInTerminal(btn) {
      const code = btn.closest('.code-block-container').querySelector('code').innerText;
      toggleRightPanel(true);
      switchRightTab('terminal');
      document.getElementById('term-output').innerText += `\n$ ${code}\nExecuting...`;
      try {
        const res = await fetch('/api/terminal/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ command: code })
        });
        const data = await res.json();
        document.getElementById('term-output').innerText += `\n${data.output}\n`;
      } catch (e) {
        document.getElementById('term-output').innerText += `\nError: ${e.message}\n`;
      }
    }

    // 5. Tool Call Rendering
    function renderToolCard(parent, tool, desc, status) {
      const card = document.createElement('div');
      card.className = 'tool-call-card';
      card.innerHTML = `
        <div class="tool-header">
          <span>🔧 Tool: ${tool}</span>
          <span class="tool-status-badge ${status}">${status}</span>
        </div>
        <div style="color:var(--text-muted); font-size:11px;">${desc}</div>
      `;
      parent.appendChild(card);
    }

    // 6. Screen Awareness ("Ask about my screen")
    async function attachScreenCapture() {
      try {
        const res = await fetch('/api/screen/capture', { method: 'POST' });
        const data = await res.json();
        if (data.success && data.image_b64) {
          attachedScreenB64 = data.image_b64;
          const strip = document.getElementById('attachments-preview');
          strip.classList.add('active');
          strip.innerHTML = `
            <div class="attachment-badge">
              <img src="${data.image_b64}">
              <span>Screen Snapshot</span>
              <span class="attachment-close" onclick="clearAttachmentPreview()">✕</span>
            </div>
          `;
          document.getElementById('user-prompt-input').placeholder = "Ask anything about this screen snapshot...";
          document.getElementById('user-prompt-input').focus();
        }
      } catch (e) {
        alert("Screen capture error: " + e.message);
      }
    }

    function clearAttachmentPreview() {
      attachedScreenB64 = null;
      const strip = document.getElementById('attachments-preview');
      strip.classList.remove('active');
      strip.innerHTML = '';
      document.getElementById('user-prompt-input').placeholder = "Ask anything, type / for quick tools, or speak...";
    }

    // 7. Option 3 Cloaking
    function toggleCloakOption3() {
      toggleRightPanel(true);
      switchRightTab('copilot');
    }

    function copyOption3Url() {
      const url = document.getElementById('option3-url-text').innerText;
      navigator.clipboard.writeText(url);
      alert("Option 3 Prompter URL copied! Open this on your smartphone or iPad placed on your desk for 100% invisible off-screen assistance during Google Meet.");
    }

    async function updateLanIp() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const host = window.location.hostname || '127.0.0.1';
        const port = window.location.port || '8844';
        document.getElementById('option3-url-text').innerText = `http://${host}:${port}/stealth`;
      } catch (_) {}
    }

    // 8. Panic Kill Switch (Single Click, Confirm-Free)
    async function triggerPanicKill() {
      try {
        await fetch('/api/panic', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clear: false}) });
        alert("🚨 EMERGENCY PANIC KILL ACTIVATED: All agent execution, browser loops, and voice streams immediately halted.");
        fetchTelemetry();
      } catch (e) {
        alert("Panic trigger failed: " + e.message);
      }
    }

    // 9. Hardware Telemetry
    async function fetchTelemetry() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const hw = data.hardware || {};
        const vram = hw.vram || {};
        const ram = hw.ram || {};
        const cpu = hw.cpu || {};

        const vramText = `VRAM: ${(vram.used_mb || 940).toFixed(0)}/${(vram.total_mb || 3800).toFixed(0)} MB`;
        document.getElementById('top-vram-text').innerText = vramText;

        const detailsEl = document.getElementById('hardware-modal-details');
        if (detailsEl) {
          detailsEl.innerHTML = `
            <div style="margin-bottom:8px;"><strong>GPU VRAM (RTX 3050):</strong> ${(vram.used_mb || 940).toFixed(0)} / ${(vram.total_mb || 3800).toFixed(0)} MB (< 3.8 GB Ceiling Lock Active)</div>
            <div style="margin-bottom:8px;"><strong>System RAM:</strong> ${(ram.used_gb || 6.2).toFixed(1)} / ${(ram.total_gb || 15.4).toFixed(1)} GB (Guaranteed ≥ 4.0 GB free reserve)</div>
            <div style="margin-bottom:8px;"><strong>CPU Load:</strong> ${(cpu.percent || 12).toFixed(1)}% (Offloaded WakeWord & STT)</div>
            <div style="margin-bottom:8px;"><strong>Status:</strong> ${data.status || 'Online'}</div>
          `;
        }
      } catch (_) {}
    }

    function openHardwareModal() { document.getElementById('hardware-modal').classList.add('active'); }
    function closeHardwareModal() { document.getElementById('hardware-modal').classList.remove('active'); }

    // 10. Voice Overlay & Speech
    function startVoiceOverlay() { document.getElementById('voice-overlay').classList.add('active'); }
    function closeVoiceOverlay() { document.getElementById('voice-overlay').classList.remove('active'); }

    async function speakText(text) {
      await fetch('/api/voice/speak', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ text })
      });
    }

    // 11. Right Panel Tabs
    function toggleRightPanel(forceOpen = null) {
      const panel = document.getElementById('right-panel');
      const btn = document.getElementById('canvas-toggle-btn');
      if (forceOpen === true) {
        panel.classList.remove('hidden');
        btn.classList.add('active');
      } else if (forceOpen === false) {
        panel.classList.add('hidden');
        btn.classList.remove('active');
      } else {
        panel.classList.toggle('hidden');
        btn.classList.toggle('active');
      }
    }

    function switchRightTab(tab) {
      currentRightTab = tab;
      document.querySelectorAll('.seg-tab').forEach(t => t.classList.remove('active'));
      event.target.classList.add('active');

      document.getElementById('tab-content-copilot').style.display = (tab === 'copilot') ? 'block' : 'none';
      document.getElementById('tab-content-terminal').style.display = (tab === 'terminal') ? 'block' : 'none';
      document.getElementById('tab-content-tasks').style.display = (tab === 'tasks') ? 'block' : 'none';
      document.getElementById('tab-content-memory').style.display = (tab === 'memory') ? 'block' : 'none';

      if (tab === 'tasks') loadTasksTab();
      if (tab === 'memory') loadMemoryTab();
    }

    async function loadTasksTab() {
      const res = await fetch('/api/tasks');
      const tasks = await res.json();
      const container = document.getElementById('tasks-list-container');
      container.innerHTML = tasks.length === 0 ? '<div style="font-size:11px; color:var(--text-muted);">No scheduled tasks.</div>' : '';
      tasks.forEach(t => {
        container.innerHTML += `
          <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); padding:10px; border-radius:6px;">
            <div style="font-weight:600; font-size:12px;">${escapeHtml(t.description)}</div>
            <div style="font-size:10px; color:var(--text-muted); font-family:var(--font-mono); margin-top:4px;">Next: ${t.next_run_at}</div>
          </div>
        `;
      });
    }

    async function loadMemoryTab() {
      const container = document.getElementById('memory-list-container');
      container.innerHTML = `
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); padding:10px; border-radius:6px; font-size:12px;">
          <div><strong>User Name:</strong> GDR User</div>
          <div style="margin-top:4px;"><strong>Hardware:</strong> Kali Linux RTX 3050 Laptop</div>
          <div style="margin-top:4px;"><strong>Preferred Engine:</strong> Sarvam 105B</div>
          <div style="margin-top:4px;"><strong>Stealth Mode:</strong> Option 3 Phone Prompter Active</div>
        </div>
      `;
    }

    async function handleTerminalEnter(e) {
      if (e.key === 'Enter') {
        const input = document.getElementById('term-input');
        const cmd = input.value.trim();
        if (!cmd) return;
        input.value = '';
        document.getElementById('term-output').innerText += `\n$ ${cmd}\n`;
        const res = await fetch('/api/terminal/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ command: cmd })
        });
        const data = await res.json();
        document.getElementById('term-output').innerText += `${data.output}\n`;
        document.getElementById('term-output').scrollTop = document.getElementById('term-output').scrollHeight;
      }
    }

    // 12. Command Palette (Ctrl+K)
    function initKeyboardShortcuts() {
      window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
          e.preventDefault();
          togglePalette();
        } else if (e.key === 'Escape') {
          closePalette();
          closeHardwareModal();
          closeVoiceOverlay();
        }
      });
    }

    function togglePalette() {
      const p = document.getElementById('palette-backdrop');
      p.classList.toggle('active');
      if (p.classList.contains('active')) {
        document.getElementById('palette-search').focus();
      }
    }
    function closePalette() { document.getElementById('palette-backdrop').classList.remove('active'); }
    function execPalette(cmd) {
      closePalette();
      if (cmd.startsWith('/')) {
        triggerStarterPrompt(cmd);
      } else if (cmd === 'panic') {
        triggerPanicKill();
      }
    }

    // 13. Composer Helpers
    function handleComposerInput(textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';

      // Check slash command trigger
      const val = textarea.value;
      const popup = document.getElementById('slash-popup');
      if (val.startsWith('/')) {
        popup.classList.add('active');
      } else {
        popup.classList.remove('active');
      }
    }

    function handleComposerKey(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendOrStop();
      }
    }

    function applySlashCommand(cmd) {
      const input = document.getElementById('user-prompt-input');
      input.value = cmd;
      input.focus();
      document.getElementById('slash-popup').classList.remove('active');
    }

    function triggerStarterPrompt(text) {
      const input = document.getElementById('user-prompt-input');
      input.value = text;
      handleSendOrStop();
    }

    function scrollToBottom() {
      const scrollEl = document.getElementById('conversation-scroll');
      scrollEl.scrollTop = scrollEl.scrollHeight;
    }

    function toggleSidebar() {
      document.getElementById('sidebar').classList.toggle('collapsed');
    }

    function copyText(btn, txt) {
      navigator.clipboard.writeText(txt);
      btn.style.color = 'var(--cyan-primary)';
      setTimeout(() => { btn.style.color = ''; }, 1200);
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
    function escapeJs(str) {
      if (!str) return '';
      return str.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
    }
  </script>
</body>
</html>
"""
