/* ── State ─────────────────────────────────────────────────────────── */
const API = '';
let cases      = [];
let workflows  = [];
let activeWfId  = null;
let activeRunId = null;   // run_id of the specific execution being viewed
let activeIsLive = false; // true only when the viewed execution is RUNNING
let sseSource  = null;

// Two-phase terminate: track which button is in "confirming" state
const terminateConfirming = {};

/* ── Init ──────────────────────────────────────────────────────────── */
function stripPaths(str) {
  if (!str) return '';
  return str.replace(/(?:\/[^\s\/:]+)*\/cases\//g, '/cases/');
}

async function init() {
  await checkTemporalStatus();
  await loadDashboard();
  setInterval(loadWorkflows, 6000);
  setInterval(checkTemporalStatus, 12000);
}

/* ── Temporal health ───────────────────────────────────────────────── */
async function checkTemporalStatus() {
  const dot  = document.getElementById('temporal-dot');
  const text = document.getElementById('temporal-status-text');
  try {
    const r = await fetch(`${API}/api/workflows`);
    dot.className   = r.ok ? 'status-dot online'  : 'status-dot offline';
    text.textContent = r.ok ? 'Temporal connected' : 'Temporal error';
  } catch {
    dot.className   = 'status-dot offline';
    text.textContent = 'Temporal offline';
  }
}

/* ── Navigation ────────────────────────────────────────────────────── */
document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    const view = btn.dataset.view;
    if (!view) return;
    switchView(view);
  });
});

function switchView(viewId) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const btn = document.getElementById(`nav-${viewId}`);
  const el  = document.getElementById(`view-${viewId}`);
  if (btn) btn.classList.add('active');
  if (el)  el.classList.add('active');
}

function goToDashboard() {
  switchView('dashboard');
  closeSse();
}

/* ── Dashboard ─────────────────────────────────────────────────────── */
async function loadDashboard() {
  await Promise.all([loadCases(), loadWorkflows()]);
}

/* ── Cases ─────────────────────────────────────────────────────────── */
async function loadCases() {
  try {
    const res = await fetch(`${API}/api/cases`);
    if (!res.ok) return;
    cases = await res.json();
    renderCasesGrid(cases);
  } catch (e) { console.warn('loadCases:', e); }
}

function renderCasesGrid(list) {
  const grid = document.getElementById('cases-grid');
  if (!list.length) {
    grid.innerHTML = '<div class="empty-state">No cases found in ./cases/</div>';
    return;
  }
  grid.innerHTML = list.map(c => {
    const files = [...(c.rtl_files || []), ...(c.tb_files || [])];
    return `
      <div class="case-card">
        <div class="case-card-header">
          <span class="case-id">${c.case_id}</span>
        </div>
        <div class="case-desc">${escHtml(c.description || 'No description available.')}</div>
        <div class="case-files">${files.map(f => `<span class="file-pill">${f}</span>`).join('')}</div>
        <button class="btn-primary" style="font-size:12px;padding:6px 14px;margin-top:2px;align-self:flex-start"
          onclick="launchCase('${c.case_id}')">
          <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/></svg>
          Run Debug
        </button>
      </div>
    `;
  }).join('');
}

/* ── Workflows table ───────────────────────────────────────────────── */
async function loadWorkflows() {
  try {
    const res = await fetch(`${API}/api/workflows`);
    if (!res.ok) return;
    workflows = await res.json();
    renderRunsTable(workflows);
  } catch (e) { console.warn('loadWorkflows:', e); }
}

function renderRunsTable(wfs) {
  const empty = document.getElementById('runs-empty');
  const table = document.getElementById('runs-table');
  const tbody = document.getElementById('runs-tbody');

  if (!wfs.length) {
    empty.style.display = 'block';
    table.style.display = 'none';
    return;
  }
  empty.style.display = 'none';
  table.style.display = 'table';

  tbody.innerHTML = wfs.map(w => {
    const caseId  = w.workflow_id.replace('rtl-debug-', '');
    const started = w.start_time ? new Date(w.start_time).toLocaleString() : '—';
    const appSt   = temporalToApp(w.status);
    const isRunning = w.status === 'RUNNING';
    // Encode run_id safely (may contain special chars)
    const runIdAttr = encodeURIComponent(w.run_id || '');

    return `
      <tr onclick="openWorkflow('${w.workflow_id}', '${runIdAttr}')">
        <td><span class="case-id">${caseId}</span></td>
        <td style="font-family:var(--mono);font-size:11.5px;color:var(--text-dim)">${w.workflow_id}</td>
        <td>${badgeHtml(appSt)}</td>
        <td style="color:var(--text-secondary)">${started}</td>
        <td onclick="event.stopPropagation()">
          ${isRunning ? `
            <button id="term-btn-${w.workflow_id.replace(/-/g,'_')}"
              class="btn-term"
              onclick="handleTerminateClick(this,'${w.workflow_id}')">
              ■ Terminate
            </button>
          ` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

/* ── Two-phase terminate ──────────────────────────────────────────── */
function handleTerminateClick(btn, wfId) {
  if (btn.classList.contains('terminating')) return;

  if (!btn.classList.contains('confirming')) {
    // Phase 1: first click → ask for confirmation via button state
    btn.classList.add('confirming');
    btn.textContent = '⚠ Click again to confirm';
    // Reset after 3 seconds if not confirmed
    setTimeout(() => {
      if (btn.classList.contains('confirming')) {
        btn.classList.remove('confirming');
        btn.textContent = '■ Terminate';
      }
    }, 3000);
  } else {
    // Phase 2: second click → execute
    btn.classList.remove('confirming');
    btn.classList.add('terminating');
    btn.textContent = 'Terminating…';
    executeTerminate(wfId);
  }
}

async function executeTerminate(wfId) {
  try {
    const res  = await fetch(`${API}/api/workflows/${wfId}/terminate`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      toast('✓ Workflow terminated', 'info');
    } else {
      toast(data.detail || 'Could not terminate workflow', 'error');
    }
  } catch {
    toast('Network error while terminating', 'error');
  }
  await loadWorkflows();
}

/* ── Launch a workflow ─────────────────────────────────────────────── */
async function launchCase(caseId) {
  try {
    const res  = await fetch(`${API}/api/workflows/${caseId}/start`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      toast(`▶ Started ${data.workflow_id}`, 'success');
      openWorkflow(data.workflow_id);
    } else {
      toast(data.detail || 'Failed to start workflow', 'error');
    }
  } catch {
    toast('Network error', 'error');
  }
}

/* ── Open live view ────────────────────────────────────────────────── */
async function openWorkflow(wfId, encodedRunId) {
  activeWfId  = wfId;
  activeRunId = encodedRunId ? decodeURIComponent(encodedRunId) : null;

  // Determine if this specific execution is RUNNING
  const wf = workflows.find(w => w.run_id === activeRunId || (!activeRunId && w.workflow_id === wfId));
  activeIsLive = wf ? wf.status === 'RUNNING' : false;

  const caseId = wfId.replace('rtl-debug-', '');

  // Show live nav item
  const navLive = document.getElementById('nav-live');
  navLive.style.display = 'flex';
  document.getElementById('nav-live-label').textContent = caseId;

  switchView('live');
  resetLiveView(wfId, caseId);

  await refreshLiveView(wfId);

  // Only start SSE for RUNNING workflows — closed ones don't need live updates
  if (activeIsLive) startSse(wfId);
}

function resetLiveView(wfId, caseId) {
  document.getElementById('live-wf-title').textContent   = wfId;
  document.getElementById('live-wf-subtitle').textContent = `case: ${caseId}`;
  document.getElementById('live-wf-badge').className     = 'badge badge-started';
  document.getElementById('live-wf-badge').textContent   = 'started';

  ['section-failure','section-rca','section-patch','section-rerun','section-terminated'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  document.getElementById('inline-approval').style.display = 'none';
  document.getElementById('live-nav-dot').style.display    = 'none';
  document.querySelectorAll('.pipe-step').forEach(el => el.classList.remove('done','active','failed'));

  // Reset elapsed timer and step-details panel
  _wfStartTime = Date.now();
  document.getElementById('step-spinner').className = 'step-spinner';
  document.getElementById('step-summary-label').textContent = 'Initializing…';
  document.getElementById('step-info-grid').innerHTML = '';
  document.getElementById('step-log-row').style.display = 'none';
  // Reset approval auto-scroll marker
  delete document.getElementById('inline-approval').dataset.scrolled;
}

/* ── SSE ───────────────────────────────────────────────────────────── */
function startSse(wfId) {
  closeSse();
  // Always attach run_id so we track the exact execution
  const qs = activeRunId ? `?run_id=${encodeURIComponent(activeRunId)}` : '';
  sseSource = new EventSource(`${API}/api/workflows/${wfId}/stream${qs}`);
  sseSource.onmessage = e => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.event === 'update') applyUpdate(msg.status, msg.report, msg.execution_status);
      if (msg.event === 'done')   { closeSse(); loadWorkflows(); }
    } catch {}
  };
  sseSource.onerror = () => closeSse();
}

function closeSse() {
  if (sseSource) { sseSource.close(); sseSource = null; }
}

async function refreshLiveView(wfId) {
  try {
    // Always pass run_id so we load the exact execution the user clicked on,
    // not the latest execution of that workflow_id.
    const qs  = activeRunId ? `?run_id=${encodeURIComponent(activeRunId)}` : '';
    const res = await fetch(`${API}/api/workflows/${wfId}/status${qs}`);
    if (!res.ok) return;
    const d = await res.json();
    
    // Set activeIsLive properly so startSse works for newly launched workflows
    activeIsLive = d.execution_status === 'running';
    
    applyUpdate(d.status, d.report, d.execution_status);
  } catch {}
}

/* ── Apply update ──────────────────────────────────────────────────── */
const STEPS = ['started','simulating','parsing','analyzing','proposing_patch',
               'awaiting_approval','applying_patch','rerunning','completed'];

/* Human-readable description for each pipeline step */
const STEP_META = {
  started:           { label: 'Loading case files',        desc: 'Reading RTL source, testbench and specification from the cases directory.' },
  simulating:        { label: 'Running simulation',        desc: 'Compiling with iverilog and executing the testbench to capture pass/fail output.' },
  parsing:           { label: 'Parsing failure log',       desc: 'Extracting suspected module names, line numbers and failure type from the simulation output.' },
  analyzing:         { label: 'LLM root cause analysis',  desc: 'Sending failure context to the LLM to identify the root cause and assign a confidence score.' },
  proposing_patch:   { label: 'LLM generating patch',     desc: 'Asking the LLM to propose a corrective RTL snippet that fixes the identified root cause.' },
  awaiting_approval: { label: 'Waiting for human review', desc: 'The workflow is paused. Review the proposed patch below and approve or reject it.' },
  applying_patch:    { label: 'Applying approved patch',  desc: 'Writing the patched snippet to the RTL source file on disk.' },
  rerunning:         { label: 'Re-running simulation',    desc: 'Re-compiling and re-executing the testbench against the patched RTL to verify correctness.' },
  completed:         { label: 'Workflow completed',       desc: 'The debug workflow has finished successfully.' },
  failed:            { label: 'Workflow failed',          desc: 'The debug workflow encountered an unrecoverable error.' },
  terminated:        { label: 'Workflow terminated',      desc: 'This workflow was manually stopped before it could complete.' },
};

/* Elapsed time helper */
let _wfStartTime = null;
function _elapsed() {
  if (!_wfStartTime) return '—';
  const s = Math.floor((Date.now() - _wfStartTime) / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s/60)}m ${s%60}s`;
}

function updateStepDetails(status, report, execStatus) {
  const meta   = STEP_META[status] || { label: status, desc: '' };
  
  // A step is busy if the workflow is running AND we are not in a waiting state
  const isBusy = execStatus === 'running' && status !== 'awaiting_approval';

  /* Spinner dot state */
  const dot = document.getElementById('step-spinner');
  if (execStatus === 'failed')        dot.className = 'step-spinner failed';
  else if (execStatus === 'terminated') dot.className = 'step-spinner terminated';
  else if (isBusy)                    dot.className = 'step-spinner active';
  else                                dot.className = 'step-spinner done';

  /* Summary label */
  document.getElementById('step-summary-label').textContent = meta.label;

  /* Build info grid */
  const items = [];

  // Always present
  items.push({ key: 'Current step', val: meta.label, cls: '' });
  items.push({ key: 'Description',  val: meta.desc,  cls: 'muted' });
  items.push({ key: 'Elapsed',      val: _elapsed(),  cls: 'muted' });

  if (report) {
    // Case / workflow ID
    if (report.case_id)     items.push({ key: 'Case',       val: report.case_id,       cls: '' });
    if (report.workflow_id) items.push({ key: 'Workflow ID', val: report.workflow_id,   cls: '' });

    // Failure info
    if (report.failure_summary) {
      const fs = report.failure_summary;
      items.push({ key: 'Failure type',    val: fs.failure_type     || '—', cls: fs.failure_type ? 'error' : 'muted' });
      items.push({ key: 'Suspect module',  val: fs.suspected_module || '—', cls: fs.suspected_module ? 'warn' : 'muted' });
      if (fs.suspected_lines?.length) {
        items.push({ key: 'Suspect lines', val: `L${fs.suspected_lines.join(', L')}`, cls: 'warn' });
      }
    }

    // Root cause confidence
    if (report.root_cause) {
      const rc  = report.root_cause;
      const pct = Math.round((rc.confidence || 0) * 100);
      items.push({ key: 'RCA confidence',  val: `${pct}%`, cls: pct >= 70 ? 'ok' : pct >= 40 ? 'warn' : 'error' });
      items.push({ key: 'Suspect module',  val: rc.suspected_module || '—', cls: 'warn' });
    }

    // Patch status
    if (report.proposed_patch) {
      items.push({ key: 'Patch status', val: report.approval_status?.replace(/_/g,' ') || 'pending', cls: '' });
    }
  }

  document.getElementById('step-info-grid').innerHTML = items.map(it => `
    <div class="step-info-item">
      <span class="step-info-key">${it.key}</span>
      <span class="step-info-val ${it.cls}">${escHtml(String(it.val))}</span>
    </div>
  `).join('');

  /* Inline log excerpt — show last few lines of the most recent log */
  let logText = '';
  let logLabel = '';
  if (report?.rerun_result?.simulation_log) {
    logText  = report.rerun_result.simulation_log;
    logLabel = 'Rerun simulation log';
  } else if (report?.failure_summary?.raw_failure) {
    logText  = report.failure_summary.raw_failure;
    logLabel = 'Simulation failure output';
  }

  const logRow = document.getElementById('step-log-row');
  if (logText.trim()) {
    logRow.style.display = 'flex';
    document.getElementById('step-log-label').textContent = logLabel;
    // Show last 20 lines to keep it compact
    const lines = logText.trim().split('\n');
    const displayLog = (lines.length > 20 ? `… (${lines.length - 20} lines hidden)\n` + lines.slice(-20).join('\n') : logText);
    document.getElementById('step-log-pre').textContent = stripPaths(displayLog);
  } else {
    logRow.style.display = 'none';
  }
}

function applyUpdate(status, report, execStatus) {
  execStatus = execStatus || 'running';
  
  updatePipeline(status, execStatus);
  updateLiveBadge(status, execStatus);
  updateStepDetails(status, report, execStatus);

  // Pulsing amber dot on nav when waiting for human (only if actually live)
  document.getElementById('live-nav-dot').style.display =
    (status === 'awaiting_approval' && execStatus === 'running') ? 'block' : 'none';

  updateLiveSections(status, report || {}, execStatus);
}

function updatePipeline(status, execStatus) {
  const curIdx      = STEPS.indexOf(status);
  const isBadEnd    = execStatus === 'failed' || execStatus === 'terminated';
  const isRunning   = execStatus === 'running';

  document.querySelectorAll('.pipe-step').forEach(el => {
    el.classList.remove('done','active','failed');
    const idx = STEPS.indexOf(el.dataset.step);
    
    if (isBadEnd && idx === curIdx) {
      el.classList.add('failed');
    } else if (idx < curIdx || (!isRunning && idx === curIdx)) {
      // If it's closed and this is the current step, mark as done
      el.classList.add('done');
    } else if (isRunning && idx === curIdx) {
      el.classList.add('active');
    }
  });
}

function updateLiveBadge(status, execStatus) {
  const el = document.getElementById('live-wf-badge');
  // If the workflow is closed, show its final execution status (completed, terminated, failed).
  // But if Temporal execution completed gracefully, yet the logical report status is failed, show failed.
  let displayStatus = execStatus !== 'running' ? execStatus : status;
  if (execStatus === 'completed' && status === 'failed') {
    displayStatus = 'failed';
  }
  
  el.className    = 'badge ' + badgeClass(displayStatus);
  el.textContent  = displayStatus.replace(/_/g,' ');
}

function updateLiveSections(status, report, execStatus) {
  /* 1. Simulation failure */
  if (report.failure_summary) {
    const fs = report.failure_summary;
    show('section-failure');
    
    const pills = [];
    if (fs.suspected_module) {
      pills.push(`<span class="meta-pill">📁 ${escHtml(fs.suspected_module)}</span>`);
    }
    if (fs.suspected_lines && fs.suspected_lines.length > 0) {
      pills.push(`<span class="meta-pill">📍 Lines ${fs.suspected_lines.join(', ')}</span>`);
    }
    if (fs.failure_type) {
      pills.push(`<span class="meta-pill">🏷 ${escHtml(fs.failure_type)}</span>`);
    }
    
    document.getElementById('failure-meta').innerHTML = pills.join('');
    document.getElementById('failure-log').textContent = stripPaths(fs.raw_failure || '');
  } else {
    hide('section-failure');
  }

  /* 2. Root cause */
  if (report.root_cause) {
    const rc  = report.root_cause;
    const pct = Math.round((rc.confidence || 0) * 100);
    show('section-rca');
    document.getElementById('rca-card').innerHTML = `
      <div class="rca-summary">${escHtml(rc.summary || '')}</div>
      <div class="rca-explanation">${escHtml(rc.explanation || '')}</div>
      <div class="rca-confidence">
        Confidence: ${pct}%
        <div class="conf-bar"><div class="conf-fill" style="width:${pct}%"></div></div>
      </div>
    `;
  } else {
    hide('section-rca');
  }

  /* 2.5 History */
  const histEl = document.getElementById('section-history');
  if (report.history && report.history.length > 0) {
    histEl.innerHTML = report.history.map((it, i) => {
      const rr = it.rerun_result;
      const rrHtml = rr ? `
        <div style="margin-top:12px; padding-top:12px; border-top:1px solid var(--border)">
          <div style="font-size:12px; color: var(--text-secondary); font-weight:600; margin-bottom:6px;">
            Rerun Log:
          </div>
          <pre class="code-block" style="max-height:100px;">${escHtml(stripPaths(rr.simulation_log || rr.compile_log || ''))}</pre>
        </div>
      ` : '';

      return `
        <div class="report-card" style="opacity: 0.85; border-left: 3px solid var(--border);">
          <div class="card-header">
            <span class="card-icon">🔄</span>
            <h3>Iteration ${i + 1} (Failed)</h3>
          </div>
          <p class="patch-explanation">${escHtml(it.patch.explanation || '')}</p>
          <details class="diff-details" style="margin-top:12px;">
            <summary>View unified diff</summary>
            <div id="hist-diff-${i}" class="code-block diff-block" style="margin-top:0;"></div>
          </details>
          ${rrHtml}
        </div>
      `;
    }).join('');

    // Render diffs safely
    report.history.forEach((it, i) => {
      if (it.patch && it.patch.diff) {
        document.getElementById(`hist-diff-${i}`).innerHTML = renderDiff(it.patch.diff);
      }
    });
  } else {
    histEl.innerHTML = '';
  }

  /* 3. Proposed patch */
  // Show patch section if there's a patch OR the live workflow is waiting for approval
  if (report.proposed_patch || (status === 'awaiting_approval' && execStatus === 'running')) {
    show('section-patch');

    if (report.proposed_patch) {
      const patch = report.proposed_patch;
      document.getElementById('patch-explanation').textContent = patch.explanation || '';

      // --- Snippet with fallback: extract from diff if field is empty ---
      const origRaw   = patch.original_snippet?.trim();
      const patchedRaw = patch.patched_snippet?.trim();

      document.getElementById('snippet-original').innerHTML = origRaw
        ? highlightVerilog(origRaw)
        : extractOriginalFromDiff(patch.diff || '');

      document.getElementById('snippet-patched').innerHTML = patchedRaw
        ? highlightVerilog(patchedRaw)
        : extractPatchedFromDiff(patch.diff || '');

      document.getElementById('patch-diff').innerHTML = renderDiff(patch.diff || '');

      // Auto-open the diff details if both snippets were empty (diff is more reliable)
      if (!origRaw && !patchedRaw && patch.diff) {
        document.querySelector('.diff-details')?.setAttribute('open', '');
      }
    }

    /* Approval row — ONLY when the exact execution being viewed is currently RUNNING
       and waiting for input. execStatus is 'running' for live executions. */
    const approvalEl = document.getElementById('inline-approval');
    if (status === 'awaiting_approval' && execStatus === 'running') {
      approvalEl.style.display = 'flex';
      // Auto-scroll to approval buttons on first appearance
      if (!approvalEl.dataset.scrolled) {
        approvalEl.dataset.scrolled = '1';
        setTimeout(() => approvalEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 150);
      }
    } else {
      approvalEl.style.display = 'none';
      delete approvalEl.dataset.scrolled;
    }
  } else {
    hide('section-patch');
    document.getElementById('inline-approval').style.display = 'none';
  }

  /* 4. Rerun result */
  if (report.rerun_result) {
    const rr = report.rerun_result;
    show('section-rerun');
    
    const log = rr.simulation_log || rr.compile_log || '';
    document.getElementById('rerun-log').textContent   = stripPaths(log);
  } else {
    hide('section-rerun');
  }

  /* 5. Terminated banner — show when workflow was killed mid-run */
  const terminatedEl = document.getElementById('section-terminated');
  if (status === 'terminated') {
    if (terminatedEl) terminatedEl.style.display = 'flex';
  } else {
    if (terminatedEl) terminatedEl.style.display = 'none';
  }
}

/* ── Approval ──────────────────────────────────────────────────────── */
document.getElementById('btn-approve').addEventListener('click', () => sendApproval('approved'));
document.getElementById('btn-reject').addEventListener('click',  () => sendApproval('rejected'));

async function sendApproval(decision) {
  if (!activeWfId) return;
  const comment = document.getElementById('approval-comment').value;
  try {
    const res  = await fetch(`${API}/api/workflows/${activeWfId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, comment }),
    });
    if (res.ok) {
      document.getElementById('inline-approval').style.display = 'none';
      document.getElementById('live-nav-dot').style.display    = 'none';
      toast(decision === 'approved' ? '✅ Patch approved!' : '❌ Patch rejected', decision === 'approved' ? 'success' : 'error');
    } else {
      const err = await res.json();
      toast(err.detail || 'Error sending signal', 'error');
    }
  } catch {
    toast('Network error', 'error');
  }
}

/* ── Verilog highlighter ───────────────────────────────────────────── */
const VL_KW = ['module','endmodule','input','output','inout','reg','wire','logic',
  'always','begin','end','if','else','assign','parameter','localparam',
  'posedge','negedge','initial','forever','case','endcase','default',
  'integer','genvar','generate','endgenerate','function','endfunction',
  'task','endtask','timescale','include','define'];

function highlightVerilog(code) {
  let s = escHtml(code);
  s = s.replace(/(\/\/[^\n]*)/g, '<span class="vl-comment">$1</span>');
  s = s.replace(/\b(\d+\'[bBhHoOdD][0-9a-fA-F_xzXZ?]+)/g, '<span class="vl-number">$1</span>');
  s = s.replace(/(?<!['\w])(\b\d+\b)(?!['\w])/g, '<span class="vl-number">$1</span>');
  const kwRe = new RegExp(`\\b(${VL_KW.join('|')})\\b`, 'g');
  s = s.replace(kwRe, '<span class="vl-keyword">$1</span>');
  return s;
}

/* ── Diff renderer ─────────────────────────────────────────────────── */
function renderDiff(raw) {
  return raw.split('\n').map(line => {
    if (line.startsWith('+'))  return `<span class="line-add">${escHtml(line)}</span>`;
    if (line.startsWith('-'))  return `<span class="line-del">${escHtml(line)}</span>`;
    if (line.startsWith('@@')) return `<span class="line-hdr">${escHtml(line)}</span>`;
    return escHtml(line);
  }).join('\n');
}

/* Extract original (pre-patch) code from a unified diff and return highlighted HTML. */
function extractOriginalFromDiff(diff) {
  if (!diff) return '';
  const code = diff.split('\n')
    .filter(l => (l.startsWith(' ') || l.startsWith('-')) && !l.startsWith('--- '))
    .map(l => l.slice(1))
    .join('\n');
  return highlightVerilog(code);
}

/* Extract patched (post-patch) code from a unified diff and return highlighted HTML. */
function extractPatchedFromDiff(diff) {
  if (!diff) return '';
  const code = diff.split('\n')
    .filter(l => (l.startsWith(' ') || l.startsWith('+')) && !l.startsWith('+++ '))
    .map(l => l.slice(1))
    .join('\n');
  return highlightVerilog(code);
}

/* ── Badge helpers ─────────────────────────────────────────────────── */
function badgeClass(s) {
  const m = {
    started:'badge-started', running:'badge-running', simulating:'badge-running',
    parsing:'badge-running', analyzing:'badge-running', proposing_patch:'badge-running',
    awaiting_approval:'badge-approval', applying_patch:'badge-running',
    rerunning:'badge-running', completed:'badge-completed',
    failed:'badge-failed', terminated:'badge-terminated',
  };
  return m[s] || 'badge-default';
}
function badgeHtml(s) {
  return `<span class="badge ${badgeClass(s)}">${s.replace(/_/g,' ')}</span>`;
}
function temporalToApp(ts) {
  const m = {
    RUNNING:'running', COMPLETED:'completed', FAILED:'failed',
    TERMINATED:'terminated', CANCELED:'terminated', TIMED_OUT:'failed',
  };
  return m[ts] || ts.toLowerCase();
}

/* ── DOM helpers ───────────────────────────────────────────────────── */
function show(id) { document.getElementById(id).style.display = 'flex'; }
function hide(id) { document.getElementById(id).style.display = 'none'; }
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ── Toast ─────────────────────────────────────────────────────────── */
function toast(msg, type = 'info') {
  const c  = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className   = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => { el.style.transition = 'opacity .35s'; el.style.opacity = '0'; }, 4500);
  setTimeout(() => el.remove(), 5000);
}

/* ── Boot ──────────────────────────────────────────────────────────── */
init();
