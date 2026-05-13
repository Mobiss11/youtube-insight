#!/usr/bin/env python3
"""
Интерактивный мастер установки YouTube Insight + Whisper-Skill.

Проводит за руку от нуля до работающего пайплайна:
1. Проверяет/ставит Whisper-Skill (https://github.com/Mobiss11/Whisper-Skill)
2. Проверяет/ставит зависимости (yt-dlp, ffmpeg, certifi)
3. Настраивает DeepSeek API ключ
4. Запускает тестовый прогон

Использование:
    python wizard.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# ── Colors ──────────────────────────────────────────────
BOLD = "\033[1m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
BLUE = "\033[34m"; RED = "\033[31m"; CYAN = "\033[36m"; NC = "\033[0m"


def heading(text: str):
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  {text}{NC}")
    print(f"{BOLD}{'='*60}{NC}")


def step(n: int, text: str):
    print(f"\n  {CYAN}[{n}]{NC} {text}")


def ok(text: str):     print(f"  {GREEN}✅{NC} {text}")
def fail(text: str):   print(f"  {RED}❌{NC} {text}")
def warn(text: str):   print(f"  {YELLOW}⚠️{NC}  {text}")
def info(text: str):   print(f"     {text}")


def run(cmd: list[str], **kw) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, **kw)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", "command not found"


def find_whisper_skill() -> Path | None:
    """Найти установленный Whisper-Skill."""
    candidates = [
        Path.home() / ".config/opencode/skills/whisper-skill",
        Path.home() / ".config/opencode/skills/Whisper-Skill",
        Path.home() / "Whisper-Skill",
        Path("/tmp/Whisper-Skill"),
    ]
    for p in candidates:
        if p.exists() and (p / "wizard.py").exists():
            return p
    return None


def detect_whisper_backend() -> tuple[str, str]:
    """Проверить какой Whisper установлен. Возвращает (backend, model_name)."""
    # 1. mlx-whisper (Apple Silicon)
    try:
        import mlx_whisper
        return "mlx", "mlx-community/whisper-large-v3-turbo"
    except ImportError:
        pass

    # 2. faster-whisper
    try:
        import faster_whisper
        return "faster", "large-v3"
    except ImportError:
        pass

    # 3. openai-whisper
    try:
        import whisper
        return "openai", "large-v2"
    except ImportError:
        pass

    return "none", ""


def check_python() -> bool:
    v = sys.version_info
    if v >= (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    fail(f"Python {v.major}.{v.minor} — нужен 3.11+")
    info("brew install python@3.11")
    return False


def check_ffmpeg() -> bool:
    code, out, _ = run(["ffmpeg", "-version"])
    if code == 0:
        ok("ffmpeg")
        return True
    fail("ffmpeg не установлен")
    info("brew install ffmpeg")
    return False


def check_yt_dlp() -> bool:
    try:
        import yt_dlp
        ok("yt-dlp")
        return True
    except ImportError:
        fail("yt-dlp не установлен")
        info("pip install yt-dlp")
        return False


def check_deepseek() -> bool:
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key and len(key) > 10:
        ok("DeepSeek API ключ")
        return True
    warn("DEEPSEEK_API_KEY не задан")
    info("Без ключа — только транскрибация, без выжимки сути")
    info("Ключ: https://platform.deepseek.com/api_keys")
    info("export DEEPSEEK_API_KEY=sk-...")
    return False


def is_apple_silicon() -> bool:
    return sys.platform == "darwin" and "arm" in os.uname().machine


def install_whisper_skill():
    """Клонировать и настроить Whisper-Skill."""
    heading("📦 Установка Whisper-Skill")

    ws_path = Path.home() / ".config/opencode/skills/Whisper-Skill"
    if ws_path.exists():
        ok(f"Whisper-Skill уже установлен: {ws_path}")
        return ws_path

    print(f"\n  Whisper-Skill — это фундамент для транскрибации.")
    print(f"  Он сам определит твоё железо и поставит правильный Whisper.")
    print(f"  https://github.com/Mobiss11/Whisper-Skill\n")

    choice = input(f"  Установить Whisper-Skill в {ws_path}? [Y/n]: ").strip().lower()
    if choice == "n":
        warn("Пропускаю установку Whisper-Skill")
        return None

    step(1, "Клонирую Whisper-Skill...")
    code, out, err = run([
        "git", "clone", "https://github.com/Mobiss11/Whisper-Skill.git",
        str(ws_path),
    ])
    if code != 0:
        fail(f"Не удалось клонировать: {err[:200]}")
        info("Попробуй вручную: git clone https://github.com/Mobiss11/Whisper-Skill.git")
        return None

    ok("Whisper-Skill склонирован")

    step(2, "Запускаю детектор окружения Whisper-Skill...")
    detect_script = ws_path / "scripts" / "detect_env.py"
    if detect_script.exists():
        code, out, err = run([sys.executable, str(detect_script)])
        print(f"     {out[:500]}")
    else:
        warn("Скрипт detect_env.py не найден — пропускаю")

    step(3, "Устанавливаю Whisper под твоё железо...")
    if is_apple_silicon():
        info("🍎 Apple Silicon → mlx-whisper (нативный Metal, 8x быстрее)")
        run([sys.executable, "-m", "pip", "install", "mlx-whisper", "-q"])
    else:
        info("💻 Стандартный → faster-whisper")
        run([sys.executable, "-m", "pip", "install", "faster-whisper", "-q"])

    ok("Whisper установлен")
    return ws_path


def install_deps(need_ytdlp: bool):
    """Установить Python-зависимости."""
    heading("📦 Зависимости")

    deps = ["certifi"]
    if need_ytdlp:
        deps.append("yt-dlp")

    for dep in deps:
        info(f"pip install {dep}...")
        run([sys.executable, "-m", "pip", "install", dep, "-q"])

    ok("Зависимости установлены")


def test_pipeline():
    """Запустить тестовый прогон."""
    heading("🧪 Тестовый прогон")

    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        print("\n  ⏭️  Пропускаю — нужен DEEPSEEK_API_KEY для полного теста")
        print("     export DEEPSEEK_API_KEY=sk-...")
        print("     python wizard.py")
        return

    backend, _ = detect_whisper_backend()
    if backend == "none":
        print("\n  ⏭️  Пропускаю — Whisper не установлен")
        return

    print("\n  🎬 Тестовое видео: Me at the zoo (19 секунд)")
    print("  Это быстро — просто проверим что всё летает...\n")

    code, out, err = run([
        sys.executable, "-m", "youtube_insight.pipeline",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    ], timeout=180)

    if code == 0:
        ok("🎉 Тест пройден! Всё работает.")
        print("\n  📁 Результат: output/jNQXAC9IVRw_insight.json")
        print("  📁 Конспект:  output/jNQXAC9IVRw_summary.md")
    else:
        fail("Тест не пройден")
        if err:
            print(f"     {err[:300]}")
        if out:
            # Maybe pipeline printed progress to stdout
            lines = out.strip().split("\n")
            for line in lines[-5:]:
                print(f"     {line}")


def print_usage():
    heading("🚀 Готово! Команды для работы")

    print(f"""
  {BOLD}YouTube видео:{NC}
    youtube-insight "https://www.youtube.com/watch?v=VIDEO_ID"

  {BOLD}Весь YouTube канал:{NC}
    youtube-insight --channel "@channel_name"
    youtube-insight --channel "@channel" --max 5
    youtube-insight --channel "@channel" --until "VIDEO_ID"

  {BOLD}Несколько видео:{NC}
    youtube-insight --urls "url1,url2,url3"

  {BOLD}Локальные файлы:{NC}
    youtube-insight --file "/path/to/video.mp4"
    youtube-insight --file "audio.wav" --title "Мой подкаст"

  {BOLD}Папка с файлами:{NC}
    youtube-insight --dir "/path/to/folder"

  {BOLD}Программный API:{NC}
    from youtube_insight.pipeline import process_video
    result = process_video("https://youtube.com/watch?v=...")
    print(result["insights"]["key_insights"])

  {BOLD}GitHub:{NC}
    https://github.com/Mobiss11/youtube-insight
    https://github.com/Mobiss11/Whisper-Skill
""")


def main():
    print(f"""
{BOLD}{BLUE}╔══════════════════════════════════════════════════════╗
║  🎬 YouTube Insight — Мастер Установки              ║
║  Транскрибация + Выжимка сути через DeepSeek V4    ║
╚══════════════════════════════════════════════════════╝{NC}
    """)
    print("  Этот мастер проведёт за руку: проверит железо,")
    print("  поставит Whisper, настроит ключи, и запустит тест.")
    print("  После этого ты сможешь обрабатывать видео одной командой.\n")

    # ── Step 0: What do you need? ──
    heading("🎯 Что будем обрабатывать?")
    print(f"""
  {CYAN}1{NC}. YouTube видео (нужен yt-dlp)
  {CYAN}2{NC}. Только локальные файлы (yt-dlp не нужен)
  {CYAN}3{NC}. Всё вместе
    """)
    choice = input("  Выбор [1/2/3, Enter=3]: ").strip() or "3"
    need_ytdlp = choice in ("1", "3")

    # ── Step 1: Whisper-Skill ──
    heading("🔧 Проверка Whisper")

    backend, model = detect_whisper_backend()
    ws_path = find_whisper_skill()

    if backend != "none":
        ok(f"Whisper уже установлен (бэкенд: {backend})")
        if ws_path:
            ok(f"Whisper-Skill найден: {ws_path}")
    else:
        fail("Whisper не установлен")
        print(f"\n  {BOLD}YouTube Insight использует Whisper-Skill для транскрибации.{NC}")
        print(f"  Это мой же скилл: https://github.com/Mobiss11/Whisper-Skill")
        print(f"  Он сам определит твоё железо и поставит лучший Whisper.\n")
        ws_path = install_whisper_skill()

    # ── Step 2: Environment ──
    heading("🔧 Проверка окружения")
    check_python()
    if choice in ("2", "3"):
        check_ffmpeg()
    if need_ytdlp:
        check_yt_dlp()
    has_ds = check_deepseek()

    # ── Step 3: Install missing ──
    need_install = need_ytdlp and not _check_ytdlp_import()
    if need_install:
        install_deps(need_ytdlp)

    # ── Step 4: Status ──
    heading("📊 Статус системы")

    backend, model = detect_whisper_backend()
    print(f"  Whisper:     {'✅ ' + backend if backend != 'none' else '❌ не установлен'}")
    if is_apple_silicon():
        print(f"  Процессор:   🍎 Apple Silicon → mlx-whisper (8x быстрее)")
    print(f"  ffmpeg:      {'✅' if check_ffmpeg() else '❌ brew install ffmpeg'}")
    if need_ytdlp:
        print(f"  yt-dlp:      {'✅' if _check_ytdlp_import() else '❌'}")
    print(f"  DeepSeek:    {'✅ V4 Flash' if has_ds else '⚠️  только транскрибация'}")

    # ── Step 5: Test ──
    print(f"\n  {BOLD}Запустить тестовый прогон?{NC} (19-сек видео, быстро)")
    if input("  [Y/n]: ").strip().lower() != "n":
        test_pipeline()

    # ── Done ──
    print_usage()


def _check_ytdlp_import() -> bool:
    try:
        import yt_dlp
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
