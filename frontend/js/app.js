'use strict';

const API_BASE = window.location.origin + '/api/v1';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  transcribe: { file: null, blob: null },
  understand: { file: null, blob: null },
  analyze:    { file: null, blob: null },
  recorder:   { mediaRecorder: null, chunks: [], activePanel: null, timerInterval: null, seconds: 0 },
};

// ── DOM helpers ─────────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

// ── Tab switching ────────────────────────────────────────────────────────────
$$('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    $$('.tab-btn').forEach(b => b.classList.remove('active'));
    $$('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`#panel-${target}`).classList.add('active');
  });
});

// ── API health check ─────────────────────────────────────────────────────────
async function checkHealth() {
  const dot  = $('#status-dot');
  const text = $('#status-text');
  try {
    const res  = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    if (data.status === 'ok') {
      dot.className  = 'status-dot online';
      text.textContent = `Model loaded · ${data.device.toUpperCase()} · ${data.model_name}`;
    } else {
      dot.className  = 'status-dot';
      text.textContent = 'Model loading…';
      setTimeout(checkHealth, 5000);
    }
  } catch {
    dot.className  = 'status-dot error';
    text.textContent = 'API unreachable';
  }
}
checkHealth();

// ── File upload handling ─────────────────────────────────────────────────────
function setupUpload(panel, stateKey) {
  const zone    = $(`#${panel}-zone`);
  const input   = $(`#${panel}-file`);
  const preview = $(`#${panel}-preview`);

  // Drag-over visual
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) handleFileSelect(f, stateKey, preview);
  });

  input.addEventListener('change', () => {
    if (input.files[0]) handleFileSelect(input.files[0], stateKey, preview);
  });

  $(`#${panel}-remove`, preview).addEventListener('click', () => {
    state[stateKey].file = null;
    state[stateKey].blob = null;
    input.value = '';
    preview.classList.remove('visible');
  });
}

function handleFileSelect(file, stateKey, previewEl) {
  state[stateKey].file = file;
  state[stateKey].blob = null;

  $('[data-name]', previewEl).textContent = file.name;
  $('[data-size]', previewEl).textContent = formatBytes(file.size);
  previewEl.classList.add('visible');

  // Reset result
  hideResult(stateKey);
}

setupUpload('transcribe', 'transcribe');
setupUpload('understand', 'understand');
setupUpload('analyze',    'analyze');

// ── Audio recorder ────────────────────────────────────────────────────────────
function setupRecorder(panelId) {
  const btn      = $(`#${panelId}-record-btn`);
  const status   = $(`#${panelId}-recorder-status`);
  const timer    = $(`#${panelId}-recorder-timer`);
  const waveform = $(`#${panelId}-waveform`);
  const preview  = $(`#${panelId}-preview`);
  const r        = state.recorder;

  btn.addEventListener('click', async () => {
    if (r.mediaRecorder && r.mediaRecorder.state === 'recording') {
      // Stop
      r.mediaRecorder.stop();
      clearInterval(r.timerInterval);
      btn.classList.remove('recording');
      btn.innerHTML = '🎤';
      status.textContent = 'Processing…';
      waveform.classList.remove('active');
    } else {
      // Start
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        r.chunks = [];
        r.seconds = 0;
        r.activePanel = panelId;

        r.mediaRecorder = new MediaRecorder(stream);
        r.mediaRecorder.ondataavailable = e => r.chunks.push(e.data);
        r.mediaRecorder.onstop = () => {
          const blob = new Blob(r.chunks, { type: 'audio/webm' });
          state[panelId].blob = blob;
          state[panelId].file = null;

          const name = `recording_${Date.now()}.webm`;
          $('[data-name]', preview).textContent = name;
          $('[data-size]', preview).textContent = formatBytes(blob.size);
          preview.classList.add('visible');
          status.textContent = 'Recording ready';
          timer.textContent = '';
          stream.getTracks().forEach(t => t.stop());
        };

        r.mediaRecorder.start();
        btn.classList.add('recording');
        btn.innerHTML = '⏹';
        status.textContent = 'Recording…';
        waveform.classList.add('active');

        r.timerInterval = setInterval(() => {
          r.seconds++;
          timer.textContent = formatTime(r.seconds);
        }, 1000);

      } catch (err) {
        showAlert(panelId, `Microphone access denied: ${err.message}`, 'error');
      }
    }
  });
}

setupRecorder('transcribe');
setupRecorder('understand');
setupRecorder('analyze');

// ── Submit handlers ───────────────────────────────────────────────────────────
$('#transcribe-form').addEventListener('submit', async e => {
  e.preventDefault();
  const { file, blob } = state.transcribe;
  if (!file && !blob) return showAlert('transcribe', 'Please select or record audio first.', 'error');

  const fd = new FormData();
  fd.append('audio', blob || file, blob ? `recording_${Date.now()}.webm` : file.name);

  const result = await callAPI(`${API_BASE}/audio/transcribe`, fd, 'transcribe-submit');
  if (!result) return;

  showTranscribeResult(result);
});

$('#understand-form').addEventListener('submit', async e => {
  e.preventDefault();
  const { file, blob } = state.understand;
  if (!file && !blob) return showAlert('understand', 'Please select or record audio first.', 'error');

  const question = $('#understand-question').value.trim() || 'What is this audio about?';
  const fd = new FormData();
  fd.append('audio', blob || file, blob ? `recording_${Date.now()}.webm` : file.name);
  fd.append('question', question);

  const result = await callAPI(`${API_BASE}/audio/understand`, fd, 'understand-submit');
  if (!result) return;

  showUnderstandResult(result);
});

$('#analyze-form').addEventListener('submit', async e => {
  e.preventDefault();
  const { file, blob } = state.analyze;
  if (!file && !blob) return showAlert('analyze', 'Please select or record audio first.', 'error');

  const fd = new FormData();
  fd.append('audio', blob || file, blob ? `recording_${Date.now()}.webm` : file.name);

  const result = await callAPI(`${API_BASE}/audio/analyze`, fd, 'analyze-submit');
  if (!result) return;

  showAnalyzeResult(result);
});

// ── Generic API call ──────────────────────────────────────────────────────────
async function callAPI(url, formData, btnId) {
  const btn = $(`#${btnId}`);
  setLoading(btn, true);
  clearAlerts();

  try {
    const res  = await fetch(url, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  } catch (err) {
    const panel = btnId.split('-')[0];
    showAlert(panel, err.message, 'error');
    return null;
  } finally {
    setLoading(btn, false);
  }
}

// ── Result renderers ──────────────────────────────────────────────────────────
function showTranscribeResult(data) {
  const panel = $('#transcribe-result');
  $('#transcribe-text').textContent = data.transcription;
  if (data.duration_seconds) {
    $('#transcribe-duration').textContent = `${data.duration_seconds}s`;
    $('#transcribe-meta').style.display = 'flex';
  }
  panel.classList.add('visible');
}

function showUnderstandResult(data) {
  const panel = $('#understand-result');
  $('#understand-question-display').textContent = data.question;
  $('#understand-answer').textContent = data.answer;
  panel.classList.add('visible');
}

function showAnalyzeResult(data) {
  const panel = $('#analyze-result');
  $('#analyze-transcription').textContent = data.transcription;
  $('#analyze-summary').textContent       = data.summary;
  $('#analyze-sentiment').textContent     = data.sentiment;
  if (data.duration_seconds) {
    $('#analyze-duration').textContent = `${data.duration_seconds}s`;
    $('#analyze-meta').style.display = 'flex';
  }
  panel.classList.add('visible');
}

function hideResult(key) {
  const panel = $(`#${key}-result`);
  if (panel) panel.classList.remove('visible');
}

// ── Copy buttons ──────────────────────────────────────────────────────────────
$$('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.copy;
    const text = $(targetId)?.textContent || '';
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });
  });
});

// ── Alert helpers ─────────────────────────────────────────────────────────────
function showAlert(panel, message, type = 'error') {
  const el = $(`#${panel}-alert`);
  if (!el) return;
  el.className = `alert alert-${type}`;
  $('[data-msg]', el).textContent = message;
  el.style.display = 'flex';
}

function clearAlerts() {
  $$('.alert').forEach(el => { el.style.display = 'none'; });
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function setLoading(btn, loading) {
  btn.classList.toggle('loading', loading);
  btn.disabled = loading;
}

function formatBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b/1024).toFixed(1)} KB`;
  return `${(b/1048576).toFixed(1)} MB`;
}

function formatTime(secs) {
  const m = String(Math.floor(secs / 60)).padStart(2, '0');
  const s = String(secs % 60).padStart(2, '0');
  return `${m}:${s}`;
}
