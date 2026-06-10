import time
from pathlib import Path

import numpy as np
import torch

_RETRY_ATTEMPTS = 2
_RETRY_DELAY = 3.0

_SAMPLE_RATE = 24000  # XTTS v2 output sample rate
_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
_VOICES_DIR = Path("voices")

_tts = None  # loaded once, stays in memory for the full pipeline run


def _get_tts():
    global _tts
    if _tts is None:
        # PyTorch 2.6+ defaults weights_only=True in torch.load, which breaks Coqui's
        # checkpoint loading (it uses custom classes in the pickle). XTTS v2 weights
        # are from a trusted public release, so weights_only=False is safe here.
        _original_load = torch.load
        torch.load = lambda *a, **kw: _original_load(*a, **{**kw, "weights_only": False})

        from TTS.api import TTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading XTTS v2 on {device}...")
        _tts = TTS(_MODEL_NAME).to(device)

        torch.load = _original_load  # restore after model is loaded
        print("XTTS v2 ready.")
    return _tts


def synthesize_segment(text: str, lang: str) -> np.ndarray:
    """
    Synthesize one text segment using the language-appropriate reference clip.
    lang must be "en" or "es".
    Retries up to _RETRY_ATTEMPTS times on failure before raising.
    Returns float32 audio array at 24000 Hz.
    """
    ref_map = {"en": _VOICES_DIR / "english_reference.wav",
               "es": _VOICES_DIR / "spanish_reference.wav"}
    reference_wav = str(ref_map[lang])

    last_exc = None
    for attempt in range(_RETRY_ATTEMPTS + 1):
        try:
            tts = _get_tts()
            wav = tts.tts(text=text, speaker_wav=reference_wav, language=lang)
            return np.array(wav, dtype=np.float32)
        except Exception as exc:
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS:
                print(f"  [TTS] attempt {attempt + 1} failed — retrying in {_RETRY_DELAY}s: {exc}")
                time.sleep(_RETRY_DELAY)
    raise last_exc


def generate_silence(duration_seconds: float) -> np.ndarray:
    """Return a silence buffer of the given duration at 24000 Hz."""
    n_samples = int(_SAMPLE_RATE * duration_seconds)
    return np.zeros(n_samples, dtype=np.float32)


def combine_and_save(audio_segments: list[np.ndarray], output_path: str) -> None:
    """Concatenate all audio segments and write to a WAV file."""
    import soundfile as sf
    combined = np.concatenate(audio_segments)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, combined, _SAMPLE_RATE)


def generate_slide_audio(script_segments: list[dict], output_path: str) -> list[dict]:
    """
    Given the ordered segment list from script_builder.build_script(),
    synthesize each segment and save the combined audio to output_path.

    Returns a list of timing dicts — one per segment — each with keys:
      lang, type, text, start (seconds), end (seconds)

    Pause segments are included in the timing list so the player knows
    when the English block ends and the Spanish block begins.
    """
    audio_parts = []
    timings: list[dict] = []
    cursor = 0.0
    total = len(script_segments)

    for i, seg in enumerate(script_segments, 1):
        lang = seg["lang"]

        if lang == "pause":
            duration = seg["duration"]
            audio_parts.append(generate_silence(duration))
            timings.append({"lang": "pause", "type": "pause", "text": "",
                            "start": cursor, "end": cursor + duration})
            print(f"  [{i}/{total}] [pause {duration}s]")
            cursor += duration
        else:
            text = seg["text"]
            print(f"  [{i}/{total}] [{lang.upper()}] {text}")
            wav = synthesize_segment(text, lang)
            duration = len(wav) / _SAMPLE_RATE
            timings.append({"lang": lang, "type": seg.get("type", "sentence"),
                            "text": text, "start": cursor, "end": cursor + duration})
            audio_parts.append(wav)
            cursor += duration

    combine_and_save(audio_parts, output_path)
    print(f"  Saved → {output_path}")
    return timings
