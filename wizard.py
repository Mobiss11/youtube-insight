#!/usr/bin/env python3
"""Интерактивный мастер установки YouTube Insight.

Спрашивает что нужно, проверяет окружение, ставит недостающее,
и запускает первый тестовый прогон.

Использование:
    python wizard.py
"""

import os
import subprocess
import sys
from pathlib import Path


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def step(num: int, text: str):
    print(f"\n  [{num}] {text}")


def ok(text: str):
    print(f"  ✅ {text}")


def fail(text: str):
    print(f"  ❌ {text}")


def warn(text: str):
    print(f"  ⚠️  {text}")


def run(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", "command not found"


def check_python() -> bool:
    v = sys.version_info
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
    if v < (3, 11):
        fail("Нужен Python 3.11+. Обнови: brew install python")
        return False
    return True


def check_ffmpeg() -> bool:
    code, out, _ = run(["ffmpeg", "-version"])
    if code == 0:
        ok("ffmpeg (для локальных видео)")
        return True
    fail("ffmpeg не установлен")
    print("     brew install ffmpeg")
    return False


def check_yt_dlp() -> bool:
    try:
        import yt_dlp
        ok("yt-dlp (для YouTube)")
        return True
    except ImportError:
        fail("yt-dlp не установлен")
        print("     pip install yt-dlp")
        return False


def check_whisper() -> str:
    """Return backend name or empty string."""
    # mlx-whisper
    try:
        import mlx_whisper
        ok("mlx-whisper (Mac M1-M4, ~8x realtime)")
        return "mlx"
    except ImportError:
        pass

    # faster-whisper
    try:
        import faster_whisper
        ok("faster-whisper (CPU/GPU)")
        return "faster"
    except ImportError:
        pass

    # openai-whisper
    try:
        import whisper
        ok("openai-whisper (fallback, медленный)")
        return "openai"
    except ImportError:
        pass

    fail("Whisper не установлен")

    # Suggest best for platform
    if sys.platform == "darwin" and "arm" in os.uname().machine:
        print("     Рекомендую: pip install mlx-whisper")
    else:
        print("     Рекомендую: pip install faster-whisper")
    print("     Или:         pip install openai-whisper")
    return ""


def check_deepseek() -> bool:
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key and len(key) > 10:
        ok("DeepSeek API ключ (для выжимки сути)")
        return True
    warn("DEEPSEEK_API_KEY не задан")
    print("     Без него — только транскрибация, без суммаризации.")
    print("     Ключ: https://platform.deepseek.com/api_keys")
    print("     export DEEPSEEK_API_KEY=sk-...")
    return False


def install_missing(whisper_backend: str, has_ytdlp: bool):
    """Установить недостающие пакеты."""
    section("📦 Установка зависимостей")

    if not has_ytdlp:
        step(1, "Устанавливаю yt-dlp...")
        run([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"], check=False)

    if not whisper_backend:
        if sys.platform == "darwin" and "arm" in os.uname().machine:
            step(2, "Устанавливаю mlx-whisper (оптимально для Apple Silicon)...")
            run([sys.executable, "-m", "pip", "install", "mlx-whisper", "-q"], check=False)
        else:
            step(2, "Устанавливаю faster-whisper...")
            run([sys.executable, "-m", "pip", "install", "faster-whisper", "-q"], check=False)

    step(3, "Устанавливаю certifi (SSL)...")
    run([sys.executable, "-m", "pip", "install", "certifi", "-q"], check=False)


def test_run():
    """Запустить тестовый прогон на коротком видео."""
    section("🧪 Тестовый прогон")

    from youtube_insight.fetch import check_yt_dlp as _yt
    from youtube_insight.transcribe import detect_whisper_backend

    if not _yt() or detect_whisper_backend() == "none":
        warn("Пропускаю тест — не все зависимости установлены")
        return

    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        print("\n  Вставь DeepSeek API ключ для полного теста:")
        print("  export DEEPSEEK_API_KEY=sk-...")
        print("  python wizard.py")
        return

    print("\n  Запускаю тест на 19-секундном видео...")
    print("  (Это быстро — проверим что всё работает)\n")

    code, out, err = run([
        sys.executable, "-m", "youtube_insight.pipeline",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    ])

    if code == 0:
        ok("Тест пройден! Всё работает.")
        print("\n  📁 Результат в output/jNQXAC9IVRw_*")
    else:
        fail("Тест не пройден")
        if err:
            print(f"  Ошибка: {err[:300]}")


def main():
    print("=" * 60)
    print("  🎬 YouTube Insight — Мастер Установки")
    print("=" * 60)
    print()
    print("  Этот мастер проверит всё что нужно и установит недостающее.")
    print("  После этого ты сможешь обрабатывать видео одной командой.")
    print()

    # === Step 0: What do you want to do? ===
    section("🎯 Что будем делать?")
    print()
    print("  1. Обрабатывать YouTube видео (нужен yt-dlp)")
    print("  2. Только локальные файлы (yt-dlp не нужен)")
    print("  3. Всё вместе")
    print()

    choice = input("  Выбор [1/2/3, Enter = 3]: ").strip() or "3"

    # === Step 1: Check environment ===
    section("🔧 Проверка окружения")

    check_python()
    if choice in ("2", "3"):
        check_ffmpeg()
    has_ytdlp = check_yt_dlp() if choice in ("1", "3") else True
    whisper_backend = check_whisper()
    has_ds = check_deepseek()

    # === Step 2: Install missing ===
    if not whisper_backend or (choice in ("1", "3") and not has_ytdlp):
        install_missing(whisper_backend, choice in ("1", "3") and not has_ytdlp)

    # === Step 3: Summary ===
    section("✅ Статус")

    from youtube_insight.transcribe import detect_whisper_backend
    wb = detect_whisper_backend()

    print(f"  Python:     {'✅' if sys.version_info >= (3, 11) else '❌'}")
    print(f"  Whisper:    {'✅ ' + wb if wb != 'none' else '❌'}")
    if choice in ("1", "3"):
        from youtube_insight.fetch import check_yt_dlp as _yt
        print(f"  yt-dlp:     {'✅' if _yt() else '❌'}")
    print(f"  DeepSeek:   {'✅' if has_ds else '⚠️  только транскрибация'}")

    print(f"\n  {'='*60}")
    print(f"  🚀 Готово! Используй:")
    print(f"    youtube-insight \"https://youtube.com/watch?v=VIDEO_ID\"")
    print(f"    youtube-insight --file \"/path/to/video.mp4\"")
    print(f"    youtube-insight --channel \"@channel_name\"")
    print(f"  {'='*60}")

    # === Step 4: Test ===
    print("\n  Запустить тестовый прогон? (19-сек видео, быстро)")
    if input("  [y/N]: ").strip().lower() == "y":
        test_run()


if __name__ == "__main__":
    main()
