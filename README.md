# Audio Understanding — Qwen2-Audio-7B-Instruct

**Projet de Fin du Module · Architecture Modernes de Réseaux de Neurones**  
Université Euromed de Fès · EIDIA · 2025/2026  
Étudiantes : Tassnim & Zineb

---

## Overview

An operational REST API and web interface for **Audio Understanding** using the open-source multimodal model **[Qwen2-Audio-7B-Instruct](https://huggingface.co/Qwen/Qwen2-Audio-7B-Instruct)**.

The platform exposes three capabilities:

| Endpoint | Description |
|---|---|
| `POST /api/v1/audio/transcribe` | Convert speech/audio to accurate text |
| `POST /api/v1/audio/understand` | Answer any question about an audio file |
| `POST /api/v1/audio/analyze` | Full report: transcription + summary + sentiment |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     Browser (SPA)                    │
│   Upload / Record → Tabs: Transcrire, Comprendre,    │
│                     Analyser → Display results       │
└──────────────────────────┬───────────────────────────┘
                           │ HTTP POST (multipart/form-data)
┌──────────────────────────▼───────────────────────────┐
│                  FastAPI  (port 8000)                 │
│  /api/v1/audio/transcribe                            │
│  /api/v1/audio/understand                            │
│  /api/v1/audio/analyze                               │
│  /api/v1/health                                      │
│  /api/docs   (Swagger UI)                            │
└──────────────────────────┬───────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────┐
│          Qwen2-Audio-7B-Instruct (HuggingFace)       │
│  AutoProcessor  →  Qwen2AudioForConditionalGeneration│
│  Runs on CUDA (float16) or CPU (float32)             │
└──────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- NVIDIA GPU with ≥ 16 GB VRAM (recommended) **or** CPU (slower)
- `ffmpeg` system package (for MP3/M4A/WebM decoding)

### Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** for the web UI.  
Open **http://localhost:8000/api/docs** for the interactive Swagger UI.

### Run on Google Colab (recommended — free A100 GPU)

Open `Qwen2_Audio_Colab.ipynb` in Colab and run the cells in order.  
A public `*.trycloudflare.com` URL is printed at the end.

---

## API Reference

### `POST /api/v1/audio/transcribe`

| Field | Type | Description |
|---|---|---|
| `audio` | file | Audio file (WAV, MP3, OGG, FLAC, WebM, M4A) |

**Response:**
```json
{
  "transcription": "Hello, this is a test recording...",
  "filename": "test.wav",
  "duration_seconds": 4.2
}
```

---

### `POST /api/v1/audio/understand`

| Field | Type | Description |
|---|---|---|
| `audio` | file | Audio file |
| `question` | string | Question to ask about the audio |

**Response:**
```json
{
  "question": "What language is spoken?",
  "answer": "The audio is in English. The speaker has a clear American accent.",
  "filename": "test.wav"
}
```

---

### `POST /api/v1/audio/analyze`

| Field | Type | Description |
|---|---|---|
| `audio` | file | Audio file |

**Response:**
```json
{
  "filename": "test.wav",
  "transcription": "Good morning everyone...",
  "summary": "A morning greeting addressing a group...",
  "sentiment": "The tone is warm and positive, with an energetic and welcoming sentiment.",
  "duration_seconds": 6.1
}
```

---

### `GET /api/v1/health`

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_name": "Qwen/Qwen2-Audio-7B-Instruct",
  "device": "cuda"
}
```

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, lifespan, health endpoint, static serving
│   │   ├── model.py         # Model loading & inference (Qwen2-Audio)
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── routers/
│   │       └── audio.py     # POST /transcribe, /understand, /analyze
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Single-page application (3 tabs)
│   ├── css/style.css        # Custom animations & typography
│   └── js/app.js            # Tab switching, upload, recorder, API calls
├── presentation/
│   ├── presentation.pptx    # 11-slide oral presentation
│   └── build_pptx.py        # Script that generated the PPTX (python-pptx)
├── rapport/
│   ├── rapport.tex          # LaTeX source (13 pages)
│   ├── rapport.pdf          # Compiled PDF
│   └── references.bib       # BibLaTeX bibliography (7 entries)
├── Qwen2_Audio_Colab.ipynb  # One-click Colab deployment (A100 + cloudflared)
└── .env.example
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_NAME` | `Qwen/Qwen2-Audio-7B-Instruct` | HuggingFace model ID |
| `USE_MOCK` | `false` | Skip model loading; return placeholder responses |
| `LOAD_IN_4BIT` | `false` | 4-bit quantization (nf4) for GPUs with < 16 GB VRAM |
| `LOAD_IN_8BIT` | `false` | 8-bit quantization for GPUs with < 16 GB VRAM |
| `HF_TOKEN` | *(none)* | HuggingFace token for gated models |

---

## Supported Audio Formats

WAV · MP3 · OGG · FLAC · WebM · M4A · AAC — up to **50 MB** per file.

---

## About the Model

**Qwen2-Audio-7B-Instruct** is an open-source multimodal language model by Alibaba Cloud. It natively processes raw audio waveforms alongside text, enabling:

- Automatic Speech Recognition (ASR) in multiple languages
- Audio Q&A — answering free-form questions about audio content
- Emotional and tonal analysis
- Multi-turn audio-grounded conversations

The model pairs a **Whisper-style audio encoder** with a **7B-parameter Qwen2 language model decoder**, instruction-tuned for interactive use.

---

## Grading Criteria — Where It Is in the Code

Quick navigation guide for each evaluated criterion.

### 2.1 Montage d'API Opérationnelle — 6 pts

| Criterion | File | Lines |
|---|---|---|
| `POST /transcribe` — audio → transcription | `backend/app/routers/audio.py` | 40–76 |
| `POST /understand` — audio + question → réponse | `backend/app/routers/audio.py` | 79–128 |
| `POST /analyze` — transcription + résumé + sentiment | `backend/app/routers/audio.py` | 131–172 |
| `GET /health` — état du serveur et du modèle | `backend/app/main.py` | 51–59 |
| Serveur FastAPI + routage | `backend/app/main.py` | 26–48 |
| Réception `multipart/form-data` | `backend/app/routers/audio.py` | 47, 89–93, 141 |
| Validation (type, taille ≤ 50 Mo, fichier non vide) | `backend/app/routers/audio.py` | 30–37, 52–61 |
| Appel au modèle IA | `backend/app/routers/audio.py` | 64, 116, 158 |
| Réponses JSON typées (Pydantic) | `backend/app/schemas.py` | 5–29 |
| Swagger UI interactif | `backend/app/main.py` | 34 (`/api/docs`) |

### 2.4 Mise en application — 10 pts

| Criterion | File | Lines / Section |
|---|---|---|
| Onglet **Transcrire** (UI) | `frontend/index.html` | `#panel-transcrire` |
| Onglet **Comprendre** — Q&R libre (UI) | `frontend/index.html` | `#panel-comprendre` |
| Onglet **Analyser** — rapport complet (UI) | `frontend/index.html` | `#panel-analyser` |
| Import fichier par glisser-déposer | `frontend/js/app.js` | 64–94 (`configurerUpload`) |
| Enregistrement microphone (MediaRecorder) | `frontend/js/app.js` | 108–164 (`configurerRecorder`) |
| Appels `fetch` vers l'API | `frontend/js/app.js` | 169–228 |
| Affichage des résultats avec animation | `frontend/js/app.js` | 251–258 (`afficherResultat`) |
| Interface servie par le backend (même origine) | `backend/app/main.py` | 63–70 |
| Chargement du modèle Qwen2-Audio | `backend/app/model.py` | 29–77 (`load_model`) |
| Inférence audio complète | `backend/app/model.py` | 159–217 (`_run_inference`) |
| Décodage + rééchantillonnage à 16 kHz | `backend/app/model.py` | 84–120 |
| Injection robuste de l'audio (gestion versions `transformers`) | `backend/app/model.py` | 127–156 (`_build_inputs`) |
| Déploiement GPU Colab A100 + tunnel public | `Qwen2_Audio_Colab.ipynb` | cellules 2–7 |

### 2.5 Rapport — 2 pts

| Criterion | File | Section |
|---|---|---|
| Introduction | `rapport/rapport.tex` | `\chapter{Introduction}` |
| Méthodologie (architecture, pipeline, API) | `rapport/rapport.tex` | `\chapter{Méthodologie}` |
| Résultats (difficultés, déploiement Colab) | `rapport/rapport.tex` | `\chapter{Résultats}` |
| Conclusion + pistes d'amélioration | `rapport/rapport.tex` | `\chapter{Conclusion}` |
| Références bibliographiques (7 entrées) | `rapport/references.bib` | fichier complet |
| PDF compilé — 13 pages | `rapport/rapport.pdf` | — |

### 2.6 Présentation orale — 2 pts

| Criterion | File | Diapositive |
|---|---|---|
| Couverture (titre, étudiantes, encadrant) | `presentation/presentation.pptx` | 1 |
| Plan de la présentation | `presentation/presentation.pptx` | 2 |
| Contexte & objectifs | `presentation/presentation.pptx` | 3 |
| Architecture Qwen2-Audio | `presentation/presentation.pptx` | 4 |
| API — les 3 endpoints POST | `presentation/presentation.pptx` | 5 |
| Interface web — 3 fonctionnalités | `presentation/presentation.pptx` | 6 |
| Pipeline technique d'inférence | `presentation/presentation.pptx` | 7 |
| Déploiement Google Colab | `presentation/presentation.pptx` | 8 |
| Difficultés & solutions | `presentation/presentation.pptx` | 9 |
| Pistes d'amélioration | `presentation/presentation.pptx` | 10 |
| Conclusion | `presentation/presentation.pptx` | 11 |
| Script source de la présentation | `presentation/build_pptx.py` | — |
