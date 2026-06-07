'use strict';

const API_BASE = window.location.origin + '/api/v1';

// ── État ───────────────────────────────────────────────────────────────────
const state = {
  transcrire: { file: null, blob: null },
  comprendre: { file: null, blob: null },
  analyser: { file: null, blob: null },
  recorder: {
    mediaRecorder: null, chunks: [],
    activePanel: null, timerInterval: null, seconds: 0,
  },
};

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

// Icônes (jeu de traits, cohérent avec le HTML)
const ICON_MIC = `<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>`;
const ICON_STOP = `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>`;

// ── Onglets ────────────────────────────────────────────────────────────────
$$('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;

    $$('.tab-btn').forEach(b => {
      b.classList.remove('bg-white', 'text-indigo-600', 'shadow-sm');
      b.classList.add('text-slate-500', 'hover:text-slate-800');
    });

    btn.classList.add('bg-white', 'text-indigo-600', 'shadow-sm');
    btn.classList.remove('text-slate-500', 'hover:text-slate-800');

    $$('.tab-panel').forEach(p => p.classList.add('hidden'));
    $(`#panel-${target}`).classList.remove('hidden');
  });
});

// ── Vérification santé de l'API ────────────────────────────────────────────
async function verifierSante() {
  const dot = $('#status-dot');
  const text = $('#status-text');
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    if (data.status === 'ok') {
      dot.className = 'dot-online w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0';
      text.textContent = `Modèle chargé · ${data.device.toUpperCase()} · ${data.model_name}`;
    } else {
      dot.className = 'w-2 h-2 rounded-full bg-amber-500 flex-shrink-0';
      text.textContent = 'Chargement du modèle…';
      setTimeout(verifierSante, 5000);
    }
  } catch {
    dot.className = 'w-2 h-2 rounded-full bg-red-500 flex-shrink-0';
    text.textContent = 'API inaccessible';
  }
}
verifierSante();

// ── Gestion de l'import de fichier ────────────────────────────────────────
function configurerUpload(panelId) {
  const zone = $(`#${panelId}-zone`);
  const input = $(`#${panelId}-file`);
  const preview = $(`#${panelId}-preview`);

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('border-indigo-400', 'bg-indigo-50/50');
  });
  zone.addEventListener('dragleave', () => {
    zone.classList.remove('border-indigo-400', 'bg-indigo-50/50');
  });
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('border-indigo-400', 'bg-indigo-50/50');
    const f = e.dataTransfer.files[0];
    if (f) selectionnerFichier(f, panelId, preview);
  });

  input.addEventListener('change', () => {
    if (input.files[0]) selectionnerFichier(input.files[0], panelId, preview);
  });

  $(`#${panelId}-remove`).addEventListener('click', () => {
    state[panelId].file = null;
    state[panelId].blob = null;
    input.value = '';
    preview.classList.add('hidden');
    cacherResultat(panelId);
  });
}

function selectionnerFichier(file, panelId, previewEl) {
  state[panelId].file = file;
  state[panelId].blob = null;
  $('[data-name]', previewEl).textContent = file.name;
  $('[data-size]', previewEl).textContent = formaterOctets(file.size);
  previewEl.classList.remove('hidden');
  cacherResultat(panelId);
}

['transcrire', 'comprendre', 'analyser'].forEach(configurerUpload);

// ── Enregistrement micro ───────────────────────────────────────────────────
function configurerRecorder(panelId) {
  const btn = $(`#${panelId}-record-btn`);
  const status = $(`#${panelId}-recorder-status`);
  const timer = $(`#${panelId}-recorder-timer`);
  const waveform = $(`#${panelId}-waveform`);
  const preview = $(`#${panelId}-preview`);
  const r = state.recorder;

  btn.addEventListener('click', async () => {
    if (r.mediaRecorder && r.mediaRecorder.state === 'recording') {
      r.mediaRecorder.stop();
      clearInterval(r.timerInterval);
      btn.classList.remove('recording');
      btn.innerHTML = ICON_MIC;
      status.textContent = 'Traitement…';
      waveform.classList.add('hidden');
      waveform.classList.remove('flex');
    } else {
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
          const name = `enregistrement_${Date.now()}.webm`;
          $('[data-name]', preview).textContent = name;
          $('[data-size]', preview).textContent = formaterOctets(blob.size);
          preview.classList.remove('hidden');
          status.textContent = 'Enregistrement prêt';
          timer.textContent = '';
          stream.getTracks().forEach(t => t.stop());
        };

        r.mediaRecorder.start();
        btn.classList.add('recording');
        btn.innerHTML = ICON_STOP;
        status.textContent = 'Enregistrement en cours…';
        waveform.classList.remove('hidden');
        waveform.classList.add('flex');

        r.timerInterval = setInterval(() => {
          r.seconds++;
          timer.textContent = formaterTemps(r.seconds);
        }, 1000);

      } catch (err) {
        afficherAlerte(panelId, `Accès microphone refusé : ${err.message}`, 'error');
      }
    }
  });
}

['transcrire', 'comprendre', 'analyser'].forEach(configurerRecorder);

// ── Soumission des formulaires ─────────────────────────────────────────────
$('#transcrire-form').addEventListener('submit', async e => {
  e.preventDefault();
  const { file, blob } = state.transcrire;
  if (!file && !blob)
    return afficherAlerte('transcrire', 'Veuillez sélectionner ou enregistrer un audio.', 'error');

  const fd = new FormData();
  fd.append('audio', blob || file, blob ? `enregistrement_${Date.now()}.webm` : file.name);

  const data = await appelAPI(`${API_BASE}/audio/transcribe`, fd, 'transcrire-submit');
  if (!data) return;

  $('#transcrire-text').textContent = data.transcription;
  if (data.duration_seconds) {
    $('#transcrire-duration').textContent = `${data.duration_seconds}s`;
    $('#transcrire-meta').classList.remove('hidden');
  }
  afficherResultat('transcrire');
});

$('#comprendre-form').addEventListener('submit', async e => {
  e.preventDefault();
  const { file, blob } = state.comprendre;
  if (!file && !blob)
    return afficherAlerte('comprendre', 'Veuillez sélectionner ou enregistrer un audio.', 'error');

  const question = $('#comprendre-question').value.trim() || 'De quoi parle cet audio ?';
  const fd = new FormData();
  fd.append('audio', blob || file, blob ? `enregistrement_${Date.now()}.webm` : file.name);
  fd.append('question', question);

  const data = await appelAPI(`${API_BASE}/audio/understand`, fd, 'comprendre-submit');
  if (!data) return;

  $('#comprendre-question-display').textContent = data.question;
  $('#comprendre-answer').textContent = data.answer;
  afficherResultat('comprendre');
});

$('#analyser-form').addEventListener('submit', async e => {
  e.preventDefault();
  const { file, blob } = state.analyser;
  if (!file && !blob)
    return afficherAlerte('analyser', 'Veuillez sélectionner ou enregistrer un audio.', 'error');

  const fd = new FormData();
  fd.append('audio', blob || file, blob ? `enregistrement_${Date.now()}.webm` : file.name);

  const data = await appelAPI(`${API_BASE}/audio/analyze`, fd, 'analyser-submit');
  if (!data) return;

  $('#analyser-transcription').textContent = data.transcription;
  $('#analyser-resume').textContent = data.summary;
  $('#analyser-sentiment').textContent = data.sentiment;
  if (data.duration_seconds) {
    $('#analyser-duration').textContent = `${data.duration_seconds}s`;
    $('#analyser-meta').classList.remove('hidden');
  }
  afficherResultat('analyser');
});

// ── Appel API générique ────────────────────────────────────────────────────
async function appelAPI(url, formData, btnId) {
  const btn = $(`#${btnId}`);
  activerChargement(btn, true);
  effacerAlertes();

  try {
    const res = await fetch(url, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  } catch (err) {
    const panel = btnId.replace('-submit', '');
    afficherAlerte(panel, err.message, 'error');
    return null;
  } finally {
    activerChargement(btn, false);
  }
}

// ── Résultats ──────────────────────────────────────────────────────────────
function afficherResultat(panelId) {
  const el = $(`#${panelId}-result`);
  el.classList.remove('hidden');
  el.classList.add('fade-up');
}

function cacherResultat(panelId) {
  $(`#${panelId}-result`)?.classList.add('hidden');
}

// ── Boutons copier ─────────────────────────────────────────────────────────
$$('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = $(btn.dataset.copy)?.textContent || '';
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'Copié !';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });
  });
});

// ── Alertes ────────────────────────────────────────────────────────────────
function afficherAlerte(panelId, message) {
  const el = $(`#${panelId}-alert`);
  if (!el) return;
  $('[data-msg]', el).textContent = message;
  el.classList.remove('hidden');
  el.classList.add('flex');
}

function effacerAlertes() {
  $$('[id$="-alert"]').forEach(el => {
    el.classList.add('hidden');
    el.classList.remove('flex');
  });
}

// ── Chargement bouton ──────────────────────────────────────────────────────
function activerChargement(btn, loading) {
  btn.disabled = loading;
  $('.spinner', btn).classList.toggle('hidden', !loading);
  $('.btn-label', btn).classList.toggle('hidden', loading);
}

// ── Utilitaires ────────────────────────────────────────────────────────────
function formaterOctets(b) {
  if (b < 1024) return `${b} o`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} Ko`;
  return `${(b / 1048576).toFixed(1)} Mo`;
}

function formaterTemps(secs) {
  const m = String(Math.floor(secs / 60)).padStart(2, '0');
  const s = String(secs % 60).padStart(2, '0');
  return `${m}:${s}`;
}
