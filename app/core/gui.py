"""
GUI Dashboard for the Agentic Honeypot.
Serves a self-contained HTML page at the root endpoint.
Features: Chat demo, feature flag toggles, prompt strategy selection, live session logs.
"""

GUI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍯 Agentic Honeypot — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-tertiary: #21262d;
  --border: #30363d;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --accent-blue: #58a6ff;
  --accent-green: #3fb950;
  --accent-red: #f85149;
  --accent-yellow: #d29922;
  --accent-purple: #bc8cff;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Inter',sans-serif; background:var(--bg-primary); color:var(--text-primary); min-height:100vh; }

/* Header */
.header {
  background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  display: flex; align-items: center; justify-content: space-between;
}
.header h1 { font-size:1.4rem; font-weight:700; }
.header h1 span { color:var(--accent-blue); }
.header .badge {
  background:var(--accent-green); color:#fff; font-size:0.7rem; font-weight:600;
  padding:3px 8px; border-radius:12px; margin-left:8px;
}
.header-right { display:flex; gap:12px; align-items:center; }
.api-key-input {
  background:var(--bg-tertiary); border:1px solid var(--border); color:var(--text-primary);
  padding:6px 12px; border-radius:6px; font-size:0.8rem; width:220px;
  font-family:monospace;
}
.api-key-input:focus { outline:none; border-color:var(--accent-blue); }
.unlock-btn {
  background:var(--accent-blue); color:#fff; border:none; padding:6px 14px;
  border-radius:6px; font-size:0.8rem; cursor:pointer; font-weight:600;
}
.unlock-btn:hover { opacity:0.9; }
.lock-status { font-size:0.75rem; color:var(--accent-red); }
.lock-status.unlocked { color:var(--accent-green); }

/* Layout */
.main-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  grid-template-rows: 1fr auto;
  height: calc(100vh - 60px);
}

/* Chat Panel */
.chat-panel {
  display:flex; flex-direction:column;
  border-right:1px solid var(--border);
}
.chat-header {
  padding:12px 16px; background:var(--bg-secondary);
  border-bottom:1px solid var(--border);
  font-size:0.85rem; font-weight:600; color:var(--accent-blue);
}
.chat-messages {
  flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px;
}
.msg {
  max-width:75%; padding:10px 14px; border-radius: 12px;
  font-size:0.85rem; line-height:1.5; position:relative;
}
.msg-scammer {
  background:#2d333b; align-self:flex-end; border-bottom-right-radius:4px;
}
.msg-honeypot {
  background:var(--bg-secondary); border:1px solid var(--border);
  align-self:flex-start; border-bottom-left-radius:4px;
}
.msg-meta {
  font-size:0.65rem; color:var(--text-secondary); margin-top:4px;
}
.msg-honeypot .msg-label { color:var(--accent-green); font-weight:600; font-size:0.7rem; margin-bottom:4px; }
.msg-scammer .msg-label { color:var(--accent-red); font-weight:600; font-size:0.7rem; margin-bottom:4px; }
.typing-indicator { color:var(--text-secondary); font-style:italic; font-size:0.8rem; padding:8px 0; }

.chat-input-area {
  padding:12px 16px; background:var(--bg-secondary); border-top:1px solid var(--border);
  display:flex; gap:8px;
}
.chat-input {
  flex:1; background:var(--bg-tertiary); border:1px solid var(--border);
  color:var(--text-primary); padding:10px 14px; border-radius:8px; font-size:0.85rem;
  font-family:'Inter',sans-serif;
}
.chat-input:focus { outline:none; border-color:var(--accent-blue); }
.send-btn {
  background:var(--accent-blue); color:#fff; border:none; padding:10px 20px;
  border-radius:8px; font-size:0.85rem; cursor:pointer; font-weight:600;
  transition: all 0.15s;
}
.send-btn:hover { opacity:0.9; transform:translateY(-1px); }
.send-btn:disabled { opacity:0.4; cursor:not-allowed; transform:none; }
.reset-btn {
  background:var(--bg-tertiary); color:var(--text-secondary); border:1px solid var(--border);
  padding:10px 14px; border-radius:8px; font-size:0.8rem; cursor:pointer;
}
.reset-btn:hover { border-color:var(--accent-red); color:var(--accent-red); }

/* Control Panel */
.control-panel {
  background:var(--bg-secondary); overflow-y:auto; padding:0;
}
.panel-section {
  padding:14px 16px; border-bottom:1px solid var(--border);
}
.panel-section h3 {
  font-size:0.75rem; font-weight:600; color:var(--text-secondary);
  text-transform:uppercase; letter-spacing:0.05em; margin-bottom:10px;
}
.panel-section.locked { opacity:0.4; pointer-events:none; }

/* Toggle Switch */
.toggle-row {
  display:flex; justify-content:space-between; align-items:center;
  padding:6px 0;
}
.toggle-label { font-size:0.82rem; }
.toggle {
  position:relative; width:36px; height:20px;
}
.toggle input { opacity:0; width:0; height:0; }
.toggle-slider {
  position:absolute; cursor:pointer; inset:0;
  background:var(--bg-tertiary); border:1px solid var(--border);
  border-radius:20px; transition:0.2s;
}
.toggle-slider:before {
  content:""; position:absolute; height:14px; width:14px;
  left:2px; bottom:2px; background:var(--text-secondary);
  border-radius:50%; transition:0.2s;
}
.toggle input:checked + .toggle-slider { background:var(--accent-green); border-color:var(--accent-green); }
.toggle input:checked + .toggle-slider:before { transform:translateX(16px); background:#fff; }

/* Strategy Radio */
.strategy-options { display:flex; flex-direction:column; gap:6px; }
.strategy-option {
  display:flex; align-items:center; gap:8px;
  padding:6px 10px; border-radius:6px; cursor:pointer;
  font-size:0.82rem; transition:0.15s;
}
.strategy-option:hover { background:var(--bg-tertiary); }
.strategy-option input[type="radio"] { accent-color:var(--accent-blue); }
.strategy-option.active { background:var(--bg-tertiary); }
.strategy-badge {
  font-size:0.65rem; padding:2px 6px; border-radius:4px; font-weight:600;
}
.strat-default { background:#1f6feb33; color:var(--accent-blue); }
.strat-aggressive { background:#f8514933; color:var(--accent-red); }
.strat-defensive { background:#3fb95033; color:var(--accent-green); }

/* Model Selector */
.model-select {
  width:100%; background:var(--bg-tertiary); border:1px solid var(--border);
  color:var(--text-primary); padding:8px 10px; border-radius:6px;
  font-size:0.8rem; font-family:monospace;
}
.model-select:focus { outline:none; border-color:var(--accent-blue); }

/* Logs Table */
.logs-panel {
  grid-column:1/-1; border-top:1px solid var(--border);
  max-height:250px; overflow-y:auto; background:var(--bg-secondary);
}
.logs-panel.locked { opacity:0.4; pointer-events:none; }
.logs-header {
  padding:10px 16px; display:flex; justify-content:space-between; align-items:center;
  background:var(--bg-tertiary); position:sticky; top:0; z-index:1;
}
.logs-header h3 {
  font-size:0.75rem; font-weight:600; color:var(--text-secondary);
  text-transform:uppercase; letter-spacing:0.05em;
}
.logs-header .refresh-info { font-size:0.65rem; color:var(--text-secondary); }
table { width:100%; border-collapse:collapse; }
th {
  text-align:left; padding:8px 12px; font-size:0.72rem; font-weight:600;
  color:var(--text-secondary); background:var(--bg-tertiary);
  position:sticky; top:36px;
}
td { padding:7px 12px; font-size:0.78rem; border-top:1px solid var(--border); }
tr:hover { background:var(--bg-primary); }
.fast { color:var(--accent-green); }
.medium { color:var(--accent-yellow); }
.slow { color:var(--accent-red); }

/* Welcome message */
.welcome {
  text-align:center; padding:40px 20px; color:var(--text-secondary);
}
.welcome h2 { color:var(--text-primary); font-size:1.1rem; margin-bottom:8px; }
.welcome p { font-size:0.85rem; max-width:400px; margin:0 auto; line-height:1.6; }
.welcome .hint { margin-top:16px; font-size:0.75rem; color:var(--accent-blue); }

/* Status toast */
.toast {
  position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
  background:var(--accent-green); color:#fff; padding:8px 20px;
  border-radius:8px; font-size:0.8rem; font-weight:600;
  opacity:0; transition:opacity 0.3s; pointer-events:none; z-index:100;
}
.toast.show { opacity:1; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>🍯 <span>Agentic Honeypot</span> Dashboard<span class="badge">LIVE</span></h1>
  <div class="header-right">
    <span class="lock-status" id="lockStatus">🔒 Admin Locked</span>
    <input type="password" class="api-key-input" id="apiKeyInput" placeholder="Enter Admin API Key...">
    <button class="unlock-btn" id="unlockBtn" onclick="unlockAdmin()">Unlock</button>
  </div>
</div>

<!-- Main Layout -->
<div class="main-layout">

  <!-- Chat Panel -->
  <div class="chat-panel">
    <div class="chat-header">💬 Chat Simulator — Pretend to be a scammer</div>
    <div class="chat-messages" id="chatMessages">
      <div class="welcome">
        <h2>Welcome to the Honeypot Demo</h2>
        <p>Type a message as if you were a scammer trying to steal bank details. Watch how the AI agent responds in character.</p>
        <p class="hint">Try: "Hello sir, your bank account has been compromised"</p>
      </div>
    </div>
    <div class="chat-input-area">
      <input type="text" class="chat-input" id="chatInput" placeholder="Type a scam message..." onkeydown="if(event.key==='Enter')sendMessage()">
      <button class="send-btn" id="sendBtn" onclick="sendMessage()">Send ➤</button>
      <button class="reset-btn" onclick="resetChat()">Reset</button>
    </div>
  </div>

  <!-- Control Panel -->
  <div class="control-panel">
    <!-- Feature Flags -->
    <div class="panel-section" id="flagsSection">
      <h3>⚙️ Feature Flags</h3>
      <div class="toggle-row">
        <span class="toggle-label">LLM Extraction</span>
        <label class="toggle"><input type="checkbox" id="flagLlm" checked onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Stalling</span>
        <label class="toggle"><input type="checkbox" id="flagStall" checked onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Verbose Logging</span>
        <label class="toggle"><input type="checkbox" id="flagVerbose" onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
    </div>

    <!-- Prompt Strategy -->
    <div class="panel-section" id="strategySection">
      <h3>🎯 Prompt Strategy</h3>
      <div class="strategy-options">
        <label class="strategy-option active">
          <input type="radio" name="strategy" value="default" checked onchange="updateConfig()">
          Default <span class="strategy-badge strat-default">Balanced</span>
        </label>
        <label class="strategy-option">
          <input type="radio" name="strategy" value="aggressive" onchange="updateConfig()">
          Aggressive <span class="strategy-badge strat-aggressive">Fast Leak</span>
        </label>
        <label class="strategy-option">
          <input type="radio" name="strategy" value="defensive" onchange="updateConfig()">
          Defensive <span class="strategy-badge strat-defensive">Cautious</span>
        </label>
      </div>
    </div>

    <!-- Model Config -->
    <div class="panel-section" id="modelSection">
      <h3>🤖 Model Config</h3>
      <select class="model-select" id="modelSelect" onchange="updateConfig()">
        <option value="accounts/fireworks/models/kimi-k2p5">Fireworks Kimi K2.5</option>
        <option value="mistralai/mistral-large-3-675b-instruct-2512">Mistral Large 3</option>
        <option value="moonshotai/kimi-k2.5">NVIDIA Kimi K2.5</option>
      </select>
      <div style="margin-top:8px;font-size:0.7rem;color:var(--text-secondary)">
        Primary model for persona & extraction
      </div>
    </div>

    <!-- Status -->
    <div class="panel-section">
      <h3>📊 Status</h3>
      <div style="font-size:0.8rem;line-height:1.8">
        <div>Sessions: <strong id="statSessions">0</strong></div>
        <div>Avg Latency: <strong id="statAvg">—</strong></div>
        <div>Strategy: <strong id="statStrategy">default</strong></div>
      </div>
    </div>
  </div>

  <!-- Session Logs -->
  <div class="logs-panel" id="logsPanel">
    <div class="logs-header">
      <h3>📋 Session Timing Logs</h3>
      <span class="refresh-info" id="logsRefresh">Refreshes every 5s</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>Session</th><th>Turn</th><th>Total</th>
          <th>Detector</th><th>Extractor</th><th>Persona</th><th>Output</th>
          <th>Model</th><th>Time</th>
        </tr>
      </thead>
      <tbody id="logsBody">
        <tr><td colspan="9" style="text-align:center;color:var(--text-secondary)">No data yet — send a message to populate</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// State
let adminKey = '';
let isAdminUnlocked = false;
let sessionId = 'demo-' + Date.now().toString(36);
let chatHistory = [];

// Toast
function showToast(msg, color) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = color || 'var(--accent-green)';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}

// Admin Unlock
function unlockAdmin() {
  adminKey = document.getElementById('apiKeyInput').value.trim();
  if (!adminKey) return;
  // Verify key by calling /admin/config
  fetch('/admin/config', { headers: { 'X-API-KEY': adminKey } })
    .then(r => {
      if (r.ok) {
        isAdminUnlocked = true;
        document.getElementById('lockStatus').textContent = '🔓 Admin Unlocked';
        document.getElementById('lockStatus').className = 'lock-status unlocked';
        document.getElementById('flagsSection').classList.remove('locked');
        document.getElementById('strategySection').classList.remove('locked');
        document.getElementById('modelSection').classList.remove('locked');
        document.getElementById('logsPanel').classList.remove('locked');
        r.json().then(loadConfigState);
        showToast('Admin unlocked!');
        refreshLogs();
      } else {
        showToast('Invalid API Key', 'var(--accent-red)');
      }
    })
    .catch(() => showToast('Connection error', 'var(--accent-red)'));
}

// Load current config into UI
function loadConfigState(cfg) {
  document.getElementById('flagLlm').checked = cfg.FLAG_LLM_EXTRACTION;
  document.getElementById('flagStall').checked = cfg.FLAG_STALLING;
  document.getElementById('flagVerbose').checked = cfg.FLAG_VERBOSE_LOGGING;
  document.querySelector(`input[name="strategy"][value="${cfg.PROMPT_STRATEGY}"]`).checked = true;
  document.getElementById('modelSelect').value = cfg.MODEL_PRIMARY;
  document.getElementById('statStrategy').textContent = cfg.PROMPT_STRATEGY;
  highlightStrategy();
}

function highlightStrategy() {
  document.querySelectorAll('.strategy-option').forEach(el => {
    el.classList.toggle('active', el.querySelector('input').checked);
  });
}

// Update config on admin panel change
function updateConfig() {
  highlightStrategy();
  if (!isAdminUnlocked) return;
  const strategy = document.querySelector('input[name="strategy"]:checked').value;
  const payload = {
    flag_llm_extraction: document.getElementById('flagLlm').checked,
    flag_stalling: document.getElementById('flagStall').checked,
    flag_verbose_logging: document.getElementById('flagVerbose').checked,
    prompt_strategy: strategy,
    model_primary: document.getElementById('modelSelect').value,
  };
  fetch('/admin/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-KEY': adminKey },
    body: JSON.stringify(payload),
  }).then(r => {
    if (r.ok) {
      showToast('Config updated!');
      document.getElementById('statStrategy').textContent = strategy;
    }
  });
}

// Chat
function addMessage(text, type, meta) {
  const container = document.getElementById('chatMessages');
  // Remove welcome message if present
  const welcome = container.querySelector('.welcome');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `msg msg-${type}`;
  const label = type === 'scammer' ? '🔴 Scammer (You)' : '🟢 Honeypot Agent';
  div.innerHTML = `<div class="msg-label">${label}</div>${text}${meta ? '<div class="msg-meta">'+meta+'</div>' : ''}`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addTyping() {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'typing-indicator';
  div.id = 'typingIndicator';
  div.textContent = '🟢 Agent is typing...';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  addMessage(text, 'scammer');
  document.getElementById('sendBtn').disabled = true;
  addTyping();

  const t0 = performance.now();
  try {
    const resp = await fetch('/api/chat/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: sessionId,
        message: { sender: 'demo-user', text: text, timestamp: new Date().toISOString() }
      }),
    });
    const elapsed = Math.round(performance.now() - t0);
    const data = await resp.json();
    removeTyping();
    if (data.reply) {
      addMessage(data.reply, 'honeypot', `⏱ ${elapsed}ms`);
    } else {
      addMessage('(no response)', 'honeypot', `⏱ ${elapsed}ms`);
    }
    // Refresh logs after a short delay
    setTimeout(refreshLogs, 500);
  } catch(e) {
    removeTyping();
    addMessage('Error: ' + e.message, 'honeypot');
  }
  document.getElementById('sendBtn').disabled = false;
  input.focus();
}

function resetChat() {
  sessionId = 'demo-' + Date.now().toString(36);
  const container = document.getElementById('chatMessages');
  container.innerHTML = `<div class="welcome">
    <h2>Session Reset</h2>
    <p>New session started. Type a message to begin.</p>
    <p class="hint">Try: "Hello sir, your bank account has been compromised"</p>
  </div>`;
}

// Logs
function colorClass(ms) {
  if (ms === undefined || ms === '-') return '';
  const v = parseFloat(ms);
  if (v < 1000) return 'fast';
  if (v < 5000) return 'medium';
  return 'slow';
}
function nodeMs(nodes, name) {
  const n = (nodes||[]).find(e => e.node === name);
  if (!n) return '-';
  let t = n.duration_ms + 'ms';
  if (n.llm_ms) t += ` <span style="color:var(--text-secondary)">(LLM:${n.llm_ms}ms)</span>`;
  return t;
}

async function refreshLogs() {
  if (!isAdminUnlocked) return;
  try {
    const resp = await fetch('/admin/timing?limit=30', { headers: { 'X-API-KEY': adminKey } });
    const data = await resp.json();
    const timings = data.timings || [];
    const tbody = document.getElementById('logsBody');

    if (timings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-secondary)">No data yet</td></tr>';
      return;
    }

    // Update stats
    const totals = timings.map(t => t.total_ms);
    const avg = Math.round(totals.reduce((a,b) => a+b, 0) / totals.length);
    document.getElementById('statSessions').textContent = timings.length;
    document.getElementById('statAvg').textContent = avg + 'ms';
    document.getElementById('statAvg').className = colorClass(avg);

    tbody.innerHTML = timings.slice().reverse().map(t => {
      const nodes = t.nodes || [];
      const time = t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : '';
      return `<tr>
        <td>${(t.session_id||'?').substring(0,14)}</td>
        <td>${t.turn||'-'}</td>
        <td class="${colorClass(t.total_ms)}">${t.total_ms}ms</td>
        <td>${nodeMs(nodes,'detector')}</td>
        <td>${nodeMs(nodes,'extractor')}</td>
        <td>${nodeMs(nodes,'persona')}</td>
        <td>${nodeMs(nodes,'output')}</td>
        <td style="font-family:monospace;font-size:0.7rem">${(t.model_primary||'').split('/').pop()}</td>
        <td style="font-size:0.7rem;color:var(--text-secondary)">${time}</td>
      </tr>`;
    }).join('');

    document.getElementById('logsRefresh').textContent = 'Updated ' + new Date().toLocaleTimeString();
  } catch(e) { console.error('Log refresh error:', e); }
}

// Lock admin sections on load
document.getElementById('flagsSection').classList.add('locked');
document.getElementById('strategySection').classList.add('locked');
document.getElementById('modelSection').classList.add('locked');
document.getElementById('logsPanel').classList.add('locked');

// Auto-refresh logs every 5s if admin is unlocked
setInterval(refreshLogs, 5000);
</script>
</body>
</html>"""
