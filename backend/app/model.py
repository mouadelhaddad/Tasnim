import os
import io
import logging
import tempfile
import numpy as np
import torch
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2-Audio-7B-Instruct")
LOAD_IN_4BIT = os.getenv("LOAD_IN_4BIT", "false").lower() == "true"
LOAD_IN_8BIT = os.getenv("LOAD_IN_8BIT", "false").lower() == "true"

_processor    = None
_model        = None
_device       = "cpu"
_model_loaded = False


def get_model_status() -> Dict[str, Any]:
    return {
        "model_loaded": _model_loaded,
        "model_name":   MODEL_NAME,
        "device":       _device,
    }


def load_model() -> None:
    global _processor, _model, _device, _model_loaded

    logger.info("Loading Qwen2-Audio-7B-Instruct …")

    from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype   = torch.float16 if _device == "cuda" else torch.float32

    _processor = AutoProcessor.from_pretrained(MODEL_NAME)

    load_kwargs: Dict[str, Any] = {"torch_dtype": dtype}
    quantized = False

    if _device == "cuda":
        load_kwargs["device_map"] = "auto"

        if LOAD_IN_4BIT or LOAD_IN_8BIT:
            from transformers import BitsAndBytesConfig

            if LOAD_IN_4BIT:
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                logger.info("Loading in 4-bit (nf4) quantization")
            else:
                load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                logger.info("Loading in 8-bit quantization")
            quantized = True

    _model = Qwen2AudioForConditionalGeneration.from_pretrained(MODEL_NAME, **load_kwargs)

    # device_map / bitsandbytes already place the weights; only move manually on CPU.
    if _device == "cpu" and not quantized:
        _model = _model.to(_device)

    _model.eval()
    _model_loaded = True
    logger.info(f"Model loaded on {_device}")


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _load_audio_bytes(audio_bytes: bytes, filename: str) -> tuple:
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


def _preprocess_audio(audio_bytes: bytes, filename: str) -> tuple:
    """Load, resample to model SR, return (array, duration_seconds)."""
    import librosa

    target_sr: int = _processor.feature_extractor.sampling_rate
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
    )

    device = next(_model.parameters()).device
    inputs["input_ids"] = inputs["input_ids"].to(device)
    if "attention_mask" in inputs:
        inputs["attention_mask"] = inputs["attention_mask"].to(device)

    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        generated_ids = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )

    generated_ids = generated_ids[:, input_len:]
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
                {"type": "audio", "audio_url": "audio_input"},
                {"type": "text",  "text": prompt},
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe(audio_bytes: bytes, filename: str) -> Dict[str, Any]:
    audio_array, duration = _preprocess_audio(audio_bytes, filename)
    result = _run_inference(
        audio_array,
        _build_conversation("Please transcribe this audio accurately and completely."),
    )
    return {"transcription": result, "duration_seconds": round(duration, 2)}


def understand(audio_bytes: bytes, filename: str, question: str) -> str:
    audio_array, _ = _preprocess_audio(audio_bytes, filename)
    return _run_inference(audio_array, _build_conversation(question))


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
        "summary":       summary,
        "sentiment":     sentiment,
        "duration_seconds": round(duration, 2),
    }
