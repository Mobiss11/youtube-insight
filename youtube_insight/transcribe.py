"""Транскрибация аудио через Whisper (mlx на Apple Silicon, стандартный на других)."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def detect_whisper_backend() -> str:
    """Определить доступный Whisper-бэкенд.

    Returns: 'mlx', 'faster', 'openai', или 'none'
    """
    # 1. mlx-whisper (нативный Metal, быстрее всего на M1-M4)
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import mlx_whisper; print('ok')"],
            capture_output=True, text=True
        )
        if "ok" in result.stdout:
            return "mlx"
    except Exception:
        pass

    # 2. faster-whisper (CTranslate2, хорош на CPU/GPU)
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from faster_whisper import WhisperModel; print('ok')"],
            capture_output=True, text=True
        )
        if "ok" in result.stdout:
            return "faster"
    except Exception:
        pass

    # 3. openai-whisper (оригинальный, медленный но надёжный)
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import whisper; print('ok')"],
            capture_output=True, text=True
        )
        if "ok" in result.stdout:
            return "openai"
    except Exception:
        pass

    return "none"


def transcribe_mlx(audio_path: Path, model_name: str = "mlx-community/whisper-large-v3-turbo") -> dict:
    """Транскрибация через mlx-whisper (Mac M1-M4, самый быстрый)."""
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=model_name,
        word_timestamps=True,
    )
    return {
        "text": result["text"],
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            }
            for seg in result.get("segments", [])
        ],
    }


def transcribe_faster(audio_path: Path, model_size: str = "large-v3") -> dict:
    """Транскрибация через faster-whisper (CTranslate2)."""
    from faster_whisper import WhisperModel

    # Определить device
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
    except ImportError:
        device = "cpu"
        compute_type = "int8"

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(audio_path), beam_size=5, word_timestamps=True)

    segs = []
    full_text = []
    for seg in segments:
        segs.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        full_text.append(seg.text)

    return {"text": " ".join(full_text), "segments": segs}


def transcribe_openai(audio_path: Path, model_size: str = "large-v2") -> dict:
    """Транскрибация через openai-whisper (медленный, но совместимый)."""
    import whisper

    model = whisper.load_model(model_size)
    result = model.transcribe(str(audio_path), word_timestamps=True)

    return {
        "text": result["text"],
        "segments": [
            {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
            for seg in result.get("segments", [])
        ],
    }


def extract_audio_from_video(video_path: Path, output_dir: Optional[Path] = None) -> Path:
    """Извлечь аудиодорожку из видеофайла через ffmpeg.

    Args:
        video_path: Путь к видеофайлу (.mp4, .mov, .mkv, etc.)
        output_dir: Директория для WAV (по умолчанию — рядом с видео)

    Returns:
        Путь к WAV-файлу.
    """
    import subprocess

    if output_dir is None:
        output_dir = video_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_path = output_dir / f"{video_path.stem}_audio.wav"

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    if not wav_path.exists():
        raise FileNotFoundError(f"Audio extraction failed: {wav_path}")
    return wav_path


SUPPORTED_AUDIO = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".opus"}
SUPPORTED_VIDEO = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".ts", ".mts"}

def is_media_file(path: Path) -> bool:
    """Проверить что файл — аудио или видео."""
    return path.suffix.lower() in (SUPPORTED_AUDIO | SUPPORTED_VIDEO)

def is_audio_file(path: Path) -> bool:
    """Проверить что файл — аудио (не требует ffmpeg)."""
    return path.suffix.lower() in SUPPORTED_AUDIO

def is_video_file(path: Path) -> bool:
    """Проверить что файл — видео (нужно извлечь аудио)."""
    return path.suffix.lower() in SUPPORTED_VIDEO


def transcribe(audio_path: Path, model_name: Optional[str] = None) -> dict:
    """Транскрибировать аудиофайл. Авто-выбор бэкенда.

    Args:
        audio_path: Путь к WAV-файлу.
        model_name: Модель Whisper (опционально, авто-выбор если None).

    Returns:
        dict с keys: text (полный текст), segments (список с start/end/text).
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    backend = detect_whisper_backend()
    if backend == "none":
        raise RuntimeError(
            "Whisper не установлен. Установи один из:\n"
            "  pip install mlx-whisper   (Mac M1-M4, recommended)\n"
            "  pip install faster-whisper (CPU/GPU)\n"
            "  pip install openai-whisper (fallback)"
        )

    print(f"  🎤 Транскрибация через {backend}...")
    start = time.time()

    if backend == "mlx":
        model = model_name or "mlx-community/whisper-large-v3-turbo"
        result = transcribe_mlx(audio_path, model)
    elif backend == "faster":
        model = model_name or "large-v3"
        result = transcribe_faster(audio_path, model)
    else:
        model = model_name or "large-v2"
        result = transcribe_openai(audio_path, model)

    elapsed = time.time() - start
    duration_mins = (audio_path.stat().st_size / (16000 * 2 * 60))  # rough estimate
    print(f"  ✅ Готово за {elapsed:.1f}с ({len(result['text'])} символов)")

    return result
