import os
import io
import logging
import tempfile
import numpy as np
import torch
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2-Audio-7B-Instruct")
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

_processor = None
_model = None
_device = "cpu"
_model_loaded = False


def get_model_status() -> Dict[str, Any]:
    return {
        "model_loaded": _model_loaded,
        "model_name": MODEL_NAME,
        "device": _device,
        "mock_mode": USE_MOCK,
    }


def load_model() -> None:
    global _processor, _model, _device, _model_loaded

    if USE_MOCK:
        logger.info("MOCK mode enabled — skipping model download")
        _model_loaded = True
        return

    logger.info("Loading Qwen2-Audio-7B-Instruct …")

    from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if _device == "cuda" else torch.float32

    _processor = AutoProcessor.from_pretrained(MODEL_NAME)

    load_kwargs: Dict[str, Any] = {"torch_dtype": dtype}
    if _device == "cuda":
        load_kwargs["device_map"] = "auto"

    _model = Qwen2AudioForConditionalGeneration.from_pretrained(MODEL_NAME, **load_kwargs)

    if _device == "cpu":
        _model = _model.to(_device)

    _model.eval()
    _model_loaded = True
    logger.info(f"Model loaded on {_device}")


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _load_audio_bytes(audio_bytes: bytes, filename: str) -> Tuple[np.ndarray, int]:
    """Return (mono float32 array, sample_rate) from raw audio bytes."""
    import soundfile as sf
    import librosa

    try:
        audio_io = io.BytesIO(audio_bytes)
        data, sr = sf.read(audio_io)
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data.astype(np.float32), sr
    except Exception:
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            data, sr = librosa.load(tmp_path, sr=None, mono=True)
            return data.astype(np.float32), sr
        finally:
            os.unlink(tmp_path)


def _preprocess_audio(audio_bytes: bytes, filename: str) -> Tuple[np.ndarray, float]:
    """Load, resample to model SR, return (array, duration_seconds)."""
    import librosa

    target_sr: int = (
        _processor.feature_extractor.sampling_rate if _processor else 16000
    )
    data, sr = _load_audio_bytes(audio_bytes, filename)
    duration = len(data) / sr

    if sr != target_sr:
        data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)

    return data.astype(np.float32), duration


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def _run_inference(
    audio_array: np.ndarray,
    conversation: List[Dict[str, Any]],
    max_new_tokens: int = 512,
) -> str:
    if USE_MOCK:
        return (
            "Mock response: The audio contains spoken content. "
            "Enable the real model by setting USE_MOCK=false and providing GPU resources."
        )

    if _model is None or _processor is None:
        raise RuntimeError("Model is not loaded yet.")

    text: str = _processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=False,
    )

    inputs = _processor(
        text=text,
        audios=[audio_array],
        return_tensors="pt",
        padding=True,
        sampling_rate=_processor.feature_extractor.sampling_rate,
    )

    # Move tensors to model device
    device = next(_model.parameters()).device
    inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

    with torch.no_grad():
        generated_ids = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )

    # Strip the prompt tokens
    generated_ids = generated_ids[:, inputs["input_ids"].size(1):]
    response: str = _processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]

    return response.strip()


def _build_conversation(prompt: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": "You are a helpful audio understanding assistant.",
        },
        {
            "role": "user",
            "content": [
                # audio_url is a placeholder; actual audio is passed via `audios=`
                {"type": "audio", "audio_url": "audio_input"},
                {"type": "text", "text": prompt},
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe(audio_bytes: bytes, filename: str) -> Dict[str, Any]:
    audio_array, duration = _preprocess_audio(audio_bytes, filename)
    conversation = _build_conversation(
        "Please transcribe this audio accurately and completely."
    )
    result = _run_inference(audio_array, conversation)
    return {"transcription": result, "duration_seconds": round(duration, 2)}


def understand(audio_bytes: bytes, filename: str, question: str) -> str:
    audio_array, _ = _preprocess_audio(audio_bytes, filename)
    conversation = _build_conversation(question)
    return _run_inference(audio_array, conversation)


def analyze(audio_bytes: bytes, filename: str) -> Dict[str, Any]:
    audio_array, duration = _preprocess_audio(audio_bytes, filename)

    transcription = _run_inference(
        audio_array,
        _build_conversation("Transcribe this audio accurately and completely."),
    )
    summary = _run_inference(
        audio_array,
        _build_conversation(
            "Provide a concise summary of the main content and key points of this audio."
        ),
        max_new_tokens=256,
    )
    sentiment = _run_inference(
        audio_array,
        _build_conversation(
            "Analyze the tone, emotion, and overall sentiment expressed in this audio. "
            "Be specific about the emotional cues you detect."
        ),
        max_new_tokens=256,
    )

    return {
        "transcription": transcription,
        "summary": summary,
        "sentiment": sentiment,
        "duration_seconds": round(duration, 2),
    }
