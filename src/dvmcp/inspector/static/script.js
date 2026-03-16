// ============================================================
// DVMCP Inspector — Client Logic
// ============================================================

// ── State ──
let tools = [];
let selectedTool = null;
let isConnected = false;

// ── Department display config ──
const DEPT_MAP = {
  hr:     { label: 'HR',          cls: 'hr' },
  eng:    { label: 'Engineering', cls: 'eng' },
  fin:    { label: 'Finance',     cls: 'fin' },
  it:     { label: 'IT Admin',    cls: 'it' },
  support:{ label: 'Support',     cls: 'support' },
  mktg:   { label: 'Marketing',   cls: 'mktg' },
};

// ── Toast Notifications ──
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toastContainer');
  const icons = {
    success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastOut 0.2s ease forwards';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

// ── Connection ──
async function toggleConnection() {
  const btn = document.getElementById('connectBtn');
  if (isConnected) {
    btn.disabled = true;
    btn.querySelector('span').textContent = 'Disconnecting...';
    await fetch('/api/disconnect', { method: 'POST' });
    isConnected = false;
    tools = [];
    selectedTool = null;
    updateUI();
    showToast('Disconnected from server', 'info');
    btn.disabled = false;
  } else {
    btn.disabled = true;
    btn.querySelector('span').textContent = 'Connecting...';
    try {
      const res = await fetch('/api/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          difficulty: document.getElementById('difficultySelect').value,
          department: document.getElementById('departmentSelect').value || null,
        }),
      });
      const data = await res.json();
      if (data.ok) {
        isConnected = true;
        await loadTools();
        refreshHistory();
        showToast(`Connected — ${tools.length} tools loaded`, 'success');
      }
    } catch (e) {
      showToast('Connection failed: ' + e.message, 'error');
    }
    updateUI();
    btn.disabled = false;
  }
}

async function reconnectWithSettings() {
  if (!isConnected) return;

  const difficulty = document.getElementById('difficultySelect').value;
  const department = document.getElementById('departmentSelect').value || null;

  showToast(`Reconnecting — ${difficulty}${department ? ', ' + department : ''}...`, 'info');

  try {
    const res = await fetch('/api/reconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ difficulty, department }),
    });
    const data = await res.json();
    if (data.ok) {
      await loadTools();
      refreshHistory();
      loadServerInfo();
      showToast(`Reconnected — ${difficulty}, ${tools.length} tools loaded`, 'success');
    }
  } catch (e) {
    showToast('Reconnect failed: ' + e.message, 'error');
  }
}

function onSettingsChange() {
  if (isConnected) {
    reconnectWithSettings();
  }
}

async function loadTools() {
  try {
    const res = await fetch('/api/tools');
    const data = await res.json();
    if (data.result) {
      tools = data.result.tools || [];
    } else if (data.tools) {
      tools = data.tools;
    } else {
      tools = [];
    }
  } catch (e) {
    tools = [];
  }
  renderToolList();
  refreshHistory();
}

// ── UI Updates ──
function updateUI() {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  const btn = document.getElementById('connectBtn');
  const btnSpan = btn.querySelector('span');
  const btnIcon = btn.querySelector('.btn-icon');

  if (isConnected) {
    dot.className = 'status-indicator on';
    text.textContent = 'Connected';
    btnSpan.textContent = 'Disconnect';
    btn.className = 'btn-connect connected';
    btnIcon.innerHTML = '<path d="M18 6L6 18"/><path d="M6 6l12 12"/>';
  } else {
    dot.className = 'status-indicator off';
    text.textContent = 'Disconnected';
    btnSpan.textContent = 'Connect';
    btn.className = 'btn-connect';
    btnIcon.innerHTML = '<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>';
    document.getElementById('toolList').innerHTML = `
      <div class="empty-state sidebar-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" opacity="0.3">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
        <p class="empty-title">No tools loaded</p>
        <p class="empty-sub">Connect to the server to browse available tools</p>
      </div>`;
    document.getElementById('toolCount').textContent = '0';
    document.getElementById('toolDetail').innerHTML = `
      <div class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round" opacity="0.15">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
        <p class="empty-title">No tool selected</p>
        <p class="empty-sub">Choose a tool from the sidebar to inspect and invoke it</p>
      </div>`;
    document.getElementById('serverInfo').innerHTML = `
      <div class="empty-state" style="height:auto;padding:60px 0">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round" opacity="0.15">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>
        </svg>
        <p class="empty-title">No server connected</p>
        <p class="empty-sub">Connect to view server details</p>
      </div>`;
  }

  loadServerInfo();
}

function getDeptInfo(name) {
  const prefix = name.split('.')[0];
  return DEPT_MAP[prefix] || { label: prefix, cls: 'eng' };
}

function renderToolList() {
  const container = document.getElementById('toolList');
  const search = document.getElementById('toolSearch').value.toLowerCase();
  const filtered = tools.filter(t =>
    t.name.toLowerCase().includes(search) ||
    (t.description || '').toLowerCase().includes(search)
  );

  document.getElementById('toolCount').textContent = filtered.length;

  if (filtered.length === 0 && tools.length > 0) {
    container.innerHTML = `
      <div class="empty-state sidebar-empty">
        <p class="empty-sub">No tools match "${escapeHtml(document.getElementById('toolSearch').value)}"</p>
      </div>`;
    return;
  }

  if (filtered.length === 0) return;

  container.innerHTML = filtered.map(t => {
    const dept = getDeptInfo(t.name);
    const isActive = selectedTool && selectedTool.name === t.name;
    return `<div class="tool-item ${isActive ? 'active' : ''}" onclick="selectTool('${t.name}')">
      <div class="tool-name">
        <span>${t.name}</span>
        <span class="tool-dept-badge ${dept.cls}">${dept.label}</span>
      </div>
      <div class="tool-desc">${t.description || ''}</div>
    </div>`;
  }).join('');
}

function filterTools() {
  renderToolList();
}

// ── Tool Selection & Detail ──
function selectTool(name) {
  selectedTool = tools.find(t => t.name === name) || null;
  renderToolList();
  renderToolDetail();
  switchTab('tools');
}

function renderToolDetail() {
  const container = document.getElementById('toolDetail');
  if (!selectedTool) {
    container.innerHTML = `
      <div class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round" opacity="0.15">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
        <p class="empty-title">No tool selected</p>
        <p class="empty-sub">Choose a tool from the sidebar to inspect and invoke it</p>
      </div>`;
    return;
  }

  const t = selectedTool;
  const dept = getDeptInfo(t.name);
  const schema = t.inputSchema || {};
  const props = schema.properties || {};
  const required = schema.required || [];

  let formFields = '';
  for (const [key, prop] of Object.entries(props)) {
    const isReq = required.includes(key);
    const type = prop.type || 'string';
    const desc = prop.description || '';
    const enumVals = prop.enum;

    let input;
    if (enumVals) {
      const opts = enumVals.map(v => `<option value="${v}">${v}</option>`).join('');
      input = `<div class="select-wrapper"><select id="field-${key}" style="width:100%"><option value="">-- select --</option>${opts}</select><svg class="select-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>`;
    } else if (type === 'object' || type === 'array') {
      input = `<textarea id="field-${key}" rows="3" placeholder='${type === 'object' ? '{}' : '[]'}' spellcheck="false"></textarea>`;
    } else if (type === 'boolean') {
      input = `<div class="select-wrapper"><select id="field-${key}" style="width:100%"><option value="">-- select --</option><option value="true">true</option><option value="false">false</option></select><svg class="select-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>`;
    } else if (type === 'integer' || type === 'number') {
      input = `<input type="number" id="field-${key}" placeholder="${escapeHtml(desc)}" spellcheck="false">`;
    } else {
      input = `<input type="text" id="field-${key}" placeholder="${escapeHtml(desc)}" spellcheck="false">`;
    }

    formFields += `<div class="form-group">
      <label>${key} ${isReq ? '<span class="required">*</span>' : ''} <span class="type-hint">${type}</span></label>
      ${input}
      ${desc ? `<div class="field-desc">${escapeHtml(desc)}</div>` : ''}
    </div>`;
  }

  const paramsContent = Object.keys(props).length === 0
    ? '<p class="no-params">This tool takes no parameters</p>'
    : formFields;

  const gearIcon = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';

  container.innerHTML = `
    <div class="tool-header">
      <div class="tool-name-display">
        ${t.name}
        <span class="dept-tag tool-dept-badge ${dept.cls}">${dept.label}</span>
      </div>
      <div class="tool-description">${t.description || 'No description available'}</div>
    </div>

    <div class="tool-split">
      <div class="tool-split-request">
        <div class="param-section">
          <div class="param-section-header">
            ${gearIcon}
            Parameters
          </div>
          <div class="param-section-body">
            ${paramsContent}
          </div>
        </div>

        <div class="tool-actions">
          <button class="btn btn-primary btn-send" id="callBtn" onclick="callSelectedTool()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Execute
          </button>
          <button class="btn" onclick="copyAsJSON()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            Copy JSON-RPC
          </button>
          <button class="btn" onclick="showSchema()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            View Schema
          </button>
        </div>
      </div>

      <div class="tool-split-response">
        <div class="param-section" style="height:100%;display:flex;flex-direction:column">
          <div class="param-section-header">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
            Response
          </div>
          <div class="param-section-body" style="flex:1;overflow-y:auto" id="toolResult">
            <div class="empty-state" style="height:100%;min-height:200px">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round" opacity="0.15">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
              <p class="empty-sub">Execute the tool to see the response</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function gatherArguments() {
  if (!selectedTool) return {};
  const schema = selectedTool.inputSchema || {};
  const props = schema.properties || {};
  const args = {};

  for (const [key, prop] of Object.entries(props)) {
    const el = document.getElementById('field-' + key);
    if (!el) continue;
    let val = el.value;
    if (val === '') continue;

    const type = prop.type || 'string';
    if (type === 'integer') {
      args[key] = parseInt(val, 10);
    } else if (type === 'number') {
      args[key] = parseFloat(val);
    } else if (type === 'boolean') {
      args[key] = val === 'true';
    } else if (type === 'object' || type === 'array') {
      try { args[key] = JSON.parse(val); } catch { args[key] = val; }
    } else {
      args[key] = val;
    }
  }
  return args;
}

async function callSelectedTool() {
  if (!selectedTool || !isConnected) return;

  const btn = document.getElementById('callBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Executing...';

  const args = gatherArguments();
  const start = performance.now();

  try {
    const res = await fetch('/api/tools/call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: selectedTool.name, arguments: args }),
    });
    const data = await res.json();
    const duration = Math.round(performance.now() - start);
    renderResult('toolResult', data, duration);
    refreshHistory();
  } catch (e) {
    renderResult('toolResult', { error: { message: e.message } });
    showToast('Tool call failed: ' + e.message, 'error');
  }

  btn.disabled = false;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="5 3 19 12 5 21 5 3"/></svg> Execute`;
}

function copyAsJSON() {
  if (!selectedTool) return;
  const args = gatherArguments();
  const msg = {
    jsonrpc: "2.0",
    id: 1,
    method: "tools/call",
    params: { name: selectedTool.name, arguments: args },
  };
  navigator.clipboard.writeText(JSON.stringify(msg, null, 2));
  showToast('Copied JSON-RPC to clipboard', 'success');
}

function showSchema() {
  if (!selectedTool) return;
  const schema = selectedTool.inputSchema || {};
  const resultEl = document.getElementById('toolResult');
  resultEl.innerHTML = `
    <div class="tool-result-inline">
      <div class="tool-result-status">
        <span class="status-ok">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          Input Schema
        </span>
      </div>
      <pre class="tool-result-pre">${escapeHtml(JSON.stringify(schema, null, 2))}</pre>
    </div>`;
}

// ── Raw JSON-RPC ──
async function sendRaw() {
  if (!isConnected) return showToast('Not connected to server', 'error');

  const method = document.getElementById('rawMethod').value;
  let params;
  try {
    params = JSON.parse(document.getElementById('rawParams').value);
  } catch (e) {
    return showToast('Invalid JSON in params: ' + e.message, 'error');
  }

  const start = performance.now();
  try {
    const res = await fetch('/api/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, params }),
    });
    const data = await res.json();
    const duration = Math.round(performance.now() - start);
    renderResult('rawResult', data, duration);
    refreshHistory();
  } catch (e) {
    renderResult('rawResult', { error: { message: e.message } });
    showToast('Request failed: ' + e.message, 'error');
  }
}

// ── Results ──
function renderResult(containerId, data, durationMs) {
  const container = document.getElementById(containerId);
  const isError = data?.error || data?.result?.isError;

  let body;
  if (data?.result?.content) {
    body = data.result.content.map(c => c.text || JSON.stringify(c)).join('\n');
  } else {
    body = JSON.stringify(data, null, 2);
  }

  const statusIcon = isError
    ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';

  // Inside the tool split panel, render inline (no wrapping card)
  if (containerId === 'toolResult') {
    container.innerHTML = `
      <div class="tool-result-inline">
        <div class="tool-result-status">
          <span class="${isError ? 'status-err' : 'status-ok'}">
            ${statusIcon}
            ${isError ? 'Error' : 'Success'}
          </span>
          ${durationMs != null ? `<span class="duration">${durationMs}ms</span>` : ''}
        </div>
        <pre class="tool-result-pre">${escapeHtml(body)}</pre>
      </div>`;
    return;
  }

  // For raw result and others, use the card style
  container.innerHTML = `
    <div class="result-box">
      <div class="result-header">
        <span class="${isError ? 'status-err' : 'status-ok'}">
          ${statusIcon}
          ${isError ? 'Error' : 'Success'}
        </span>
        ${durationMs != null ? `<span class="duration">${durationMs}ms</span>` : ''}
      </div>
      <div class="result-body"><pre>${escapeHtml(body)}</pre></div>
    </div>`;
}

// ── History ──
async function refreshHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    const items = data.history || [];
    document.getElementById('historyBadge').textContent = items.length;
    renderHistory(items);
  } catch {}
}

function renderHistory(items) {
  const container = document.getElementById('historyList');
  if (items.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="height:auto;padding:60px 0">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round" opacity="0.15">
          <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
        </svg>
        <p class="empty-title">No requests yet</p>
        <p class="empty-sub">Requests will appear here as you interact with the server</p>
      </div>`;
    return;
  }

  container.innerHTML = items.slice().reverse().map((item) => {
    const time = new Date(item.timestamp * 1000).toLocaleTimeString();
    const isNotification = item.id === null;
    const isError = item.response?.error || item.response?.result?.isError;

    const methodColor = isError ? 'var(--error)' : isNotification ? 'var(--text-disabled)' : 'var(--text-primary)';
    const dirType = isNotification ? 'notif' : 'req';
    const dirLabel = isNotification ? 'NOTIF' : 'REQ';

    return `<div class="history-item">
      <div class="history-header" onclick="this.nextElementSibling.classList.toggle('open')">
        <div class="history-method-group">
          <span class="history-direction ${dirType}">${dirLabel}</span>
          <span class="history-method" style="color:${methodColor}">${item.method}</span>
        </div>
        <span class="history-meta">
          ${item.duration_ms != null ? `<span class="duration-pill">${item.duration_ms}ms</span>` : ''}
          <span>${time}</span>
          <span>#${item.id ?? '-'}</span>
        </span>
      </div>
      <div class="history-body">
        <div class="history-section">
          <h4>Request</h4>
          <pre>${escapeHtml(JSON.stringify(item.request, null, 2))}</pre>
        </div>
        ${item.response ? `<div class="history-section">
          <h4>Response</h4>
          <pre>${escapeHtml(JSON.stringify(item.response, null, 2))}</pre>
        </div>` : ''}
      </div>
    </div>`;
  }).join('');
}

async function clearHistory() {
  await fetch('/api/history/clear', { method: 'POST' });
  refreshHistory();
  showToast('History cleared', 'info');
}

// ── Server Info ──
async function loadServerInfo() {
  if (!isConnected) return;
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const info = data.serverInfo || {};

    const serverName = info.serverInfo?.name || 'N/A';
    const serverVersion = info.serverInfo?.version || 'N/A';
    const protocol = info.protocolVersion || 'N/A';
    const difficulty = data.difficulty || 'N/A';
    const department = data.department || 'All';

    document.getElementById('serverInfo').innerHTML = `
      <div class="server-info-grid">
        <div class="info-card">
          <div class="info-card-label">Server Name</div>
          <div class="info-card-value">${serverName}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">Version</div>
          <div class="info-card-value accent">${serverVersion}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">Protocol</div>
          <div class="info-card-value">${protocol}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">Difficulty</div>
          <div class="info-card-value" style="text-transform:capitalize">${difficulty}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">Department</div>
          <div class="info-card-value" style="text-transform:capitalize">${department}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">Tools Loaded</div>
          <div class="info-card-value accent">${tools.length}</div>
        </div>
      </div>

      <div class="capabilities-section">
        <div class="capabilities-header">Capabilities</div>
        <div class="capabilities-body">
          <pre>${escapeHtml(JSON.stringify(info.capabilities || {}, null, 2))}</pre>
        </div>
      </div>

      <div class="capabilities-section" style="margin-top:12px">
        <div class="capabilities-header">Raw Initialize Response</div>
        <div class="capabilities-body">
          <pre>${escapeHtml(JSON.stringify(info, null, 2))}</pre>
        </div>
      </div>
    `;
  } catch {}
}

// ── Tabs ──
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + tab));
  if (tab === 'history') refreshHistory();
  if (tab === 'server') loadServerInfo();
}

// ── Sidebar Resize ──
(function initResize() {
  const handle = document.getElementById('resizeHandle');
  const sidebar = document.getElementById('sidebar');
  let isResizing = false;

  handle.addEventListener('mousedown', (e) => {
    isResizing = true;
    handle.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const newWidth = Math.max(240, Math.min(500, e.clientX));
    sidebar.style.width = newWidth + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!isResizing) return;
    isResizing = false;
    handle.classList.remove('active');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
})();

// ── Util ──
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ──
fetch('/api/status').then(r => r.json()).then(data => {
  if (data.connected) {
    isConnected = true;
    updateUI();
    loadTools();
  }
});
