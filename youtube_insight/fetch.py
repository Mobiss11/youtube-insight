"""Скачивание аудио из YouTube видео через yt-dlp."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(os.getenv("YT_INSIGHT_DIR", Path(__file__).parent.parent / "output"))


def _yt_dlp(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run yt-dlp as a Python module (more reliable than CLI)."""
    cmd = [sys.executable, "-m", "yt_dlp"] + args
    return subprocess.run(cmd, **kwargs)


def check_yt_dlp() -> bool:
    """Проверить что yt-dlp установлен."""
    try:
        _yt_dlp(["--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def fetch_channel_videos(channel_url: str, max_videos: int = 0) -> list[dict]:
    """Получить список всех видео с канала.

    Args:
        channel_url: URL канала (например https://www.youtube.com/@pro_money_tg)
        max_videos: Макс. количество видео (0 = все)

    Returns:
        Список dict с ключами: id, title, url, duration, upload_date
    """
    cmd = [
        "--flat-playlist", "--dump-json", "--no-warnings",
    ]
    if max_videos > 0:
        cmd += ["--playlist-end", str(max_videos)]
    cmd.append(channel_url + "/videos")

    result = _yt_dlp(cmd, capture_output=True, text=True)
    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            videos.append({
                "id": data.get("id", ""),
                "title": data.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                "duration": data.get("duration", 0),
                "upload_date": data.get("upload_date", ""),
            })
        except json.JSONDecodeError:
            continue

    return videos


def fetch_video_info(url: str) -> dict:
    """Получить метаданные одного видео."""
    cmd = ["--dump-json", "--no-warnings", url]
    result = _yt_dlp(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")
    data = json.loads(result.stdout)
    return {
        "id": data.get("id", ""),
        "title": data.get("title", ""),
        "url": url,
        "duration": data.get("duration", 0),
        "upload_date": data.get("upload_date", ""),
        "description": data.get("description", ""),
        "channel": data.get("channel", ""),
    }


def download_audio(url: str, output_name: Optional[str] = None) -> Path:
    """Скачать аудиодорожку видео в WAV.

    Args:
        url: URL видео
        output_name: Имя выходного файла (без расширения). Если None — video_id.

    Returns:
        Путь к скачанному WAV-файлу.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_name is None:
        # Extract video ID from URL
        if "watch?v=" in url:
            output_name = url.split("watch?v=")[1].split("&")[0]
        else:
            output_name = "video"

    output_path = OUTPUT_DIR / output_name

    cmd = [
        "-f", "bestaudio[ext=m4a]/bestaudio/best",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", f"{output_path}.%(ext)s",
        "--no-warnings",
        "--no-playlist",
        url,
    ]

    _yt_dlp(cmd, check=True, capture_output=True)
    wav_path = Path(f"{output_path}.wav")
    if not wav_path.exists():
        raise FileNotFoundError(f"Audio not created: {wav_path}")
    return wav_path
