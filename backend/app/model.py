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
# Optional quantization for limited-VRAM GPUs (e.g. Colab T4 ~15 GB).
LOAD_IN_4BIT = os.getenv("LOAD_IN_4BIT", "false").lower() == "true"
LOAD_IN_8BIT = os.getenv("LOAD_IN_8BIT", "false").lower() == "true"

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

def _build_inputs(text: str, audio_array: np.ndarray, sampling_rate: int):
    """Feed the audio to the processor.

    ``transformers`` renamed the audio argument across versions
    (``audios`` -> ``audio``). Passing the wrong name is silently ignored
    (it lands in ``**kwargs``), which strips the audio from the model inputs.
    We try both and keep the call that actually yields ``input_features``.
    """
    last_inputs = None
    for key in ("audios", "audio"):
        try:
            inputs = _processor(
                text=text,
                return_tensors="pt",
                padding=True,
                sampling_rate=sampling_rate,
                **{key: [audio_array]},
            )
        except (TypeError, ValueError):
            continue
        last_inputs = inputs
        if "input_features" in inputs:
            logger.info(
                "Audio passed via '%s' (input_features shape=%s)",
                key, tuple(inputs["input_features"].shape),
            )
            return inputs
        logger.warning("Processor ignored audio argument '%s' (no input_features)", key)

    return last_inputs


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

    if audio_array is None or len(audio_array) < 10:
        raise RuntimeError("Audio is empty or too short to process.")

    text: str = _processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=False,
    )

    inputs = _build_inputs(
        text, audio_array, _processor.feature_extractor.sampling_rate
    )

    # If the audio never made it into the inputs, the model would silently
    # answer as a text-only LLM ("I can't access the audio"). Fail loudly.
    if inputs is None or "input_features" not in inputs:
        raise RuntimeError(
            "Audio features missing from model inputs — the audio did not reach "
            "the model. Check the installed transformers version and audio decoding."
        )

    # Move tensors to the model device; match the model dtype for audio features
    # (the encoder is fp16 on GPU and would reject fp32 features).
    device = next(_model.parameters()).device
    model_dtype = next(_model.parameters()).dtype
    prepared: Dict[str, Any] = {}
    for k, v in inputs.items():
        if isinstance(v, torch.Tensor):
            v = v.to(device)
            if k == "input_features" and v.is_floating_point():
                v = v.to(model_dtype)
        prepared[k] = v
    inputs = prepared

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
