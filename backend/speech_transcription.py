"""Local speech-to-text using a multilingual, CPU-friendly Whisper model."""

from io import BytesIO
from threading import Lock


MODEL_NAME = "base"
LANGUAGE_CODES = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Kannada": "kn",
    "Bengali": "bn",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Punjabi": "pa",
    "Urdu": "ur",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Portuguese": "pt",
    "Arabic": "ar",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Simplified)": "zh",
}

_model = None
_model_lock = Lock()


def _get_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel

                _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio: bytes, language: str) -> str:
    """Transcribe browser-recorded audio locally and return the selected language's text."""
    language_code = LANGUAGE_CODES.get(language)
    if language_code is None:
        raise ValueError("The selected language is not supported for voice input.")
    if not audio:
        raise ValueError("The recording is empty. Please record your voice and try again.")

    model = _get_model()
    segments, _ = model.transcribe(
        BytesIO(audio),
        language=language_code,
        beam_size=3,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
