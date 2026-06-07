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
│   Upload / Record → Tabs: Transcribe, Understand,    │
│                     Analyze → Display results        │
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

### 1. Prerequisites

- Python 3.10+
- NVIDIA GPU with ≥ 16 GB VRAM (recommended) **or** CPU (slower)
- `ffmpeg` system package (for MP3/M4A decoding)

### 2. Run with Docker (recommended)

```bash
# GPU
docker compose up --build

# CPU / development (no model download)
USE_MOCK=true docker compose up --build
```

### 3. Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** for the web UI.  
Open **http://localhost:8000/api/docs** for the interactive Swagger UI.

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
│   │   ├── main.py          # FastAPI application & lifespan
│   │   ├── model.py         # Model loading & inference logic
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── routers/
│   │       └── audio.py     # /transcribe, /understand, /analyze endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html           # Single-page application
│   ├── css/style.css
│   └── js/app.js
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_NAME` | `Qwen/Qwen2-Audio-7B-Instruct` | HuggingFace model ID |
| `USE_MOCK` | `false` | Skip model loading; return mock responses |
| `HF_TOKEN` | *(none)* | HuggingFace token for gated models |

---

## Supported Audio Formats

WAV · MP3 · OGG · FLAC · WebM · M4A · AAC — up to **50 MB** per file.

---

## About the Model

**Qwen2-Audio-7B-Instruct** is an open-source multimodal language model developed by Alibaba Cloud. It natively processes raw audio waveforms alongside text, enabling:

- Automatic Speech Recognition (ASR) in multiple languages
- Audio Q&A — answering free-form questions about audio content
- Sound event detection and description
- Emotional and tonal analysis
- Multi-turn audio-grounded conversations

The model uses a dedicated **Whisper-style audio encoder** combined with a **7B-parameter Qwen2 language model decoder**, trained with instruction tuning for interactive use.
