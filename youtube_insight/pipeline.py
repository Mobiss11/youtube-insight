"""Оркестратор: полный пайплайн YouTube → Транскрибация → Инсайты.

Usage:
    python -m youtube_insight.pipeline "https://youtube.com/watch?v=VIDEO_ID"
    python -m youtube_insight.pipeline --channel "@pro_money_tg"
    python -m youtube_insight.pipeline --channel "@pro_money_tg" --max 5
    python -m youtube_insight.pipeline --channel "@pro_money_tg" --until "VIDEO_ID"
    python -m youtube_insight.pipeline --urls "url1,url2,url3"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from youtube_insight import __version__
from youtube_insight.fetch import (
    fetch_channel_videos,
    fetch_video_info,
    download_audio,
    check_yt_dlp,
    OUTPUT_DIR as FETCH_DIR,
)
from youtube_insight.transcribe import transcribe, detect_whisper_backend
from youtube_insight.densify import summarize


def process_video(url: str, output_dir: Optional[Path] = None) -> dict:
    """Полный пайплайн для одного видео.

    Returns:
        dict с транскриптом, инсайтами, метаданными.
    """
    if output_dir is None:
        output_dir = FETCH_DIR

    # 1. Info
    print(f"\n📹 {url}")
    info = fetch_video_info(url)
    print(f"   {info['title'][:80]}")
    print(f"   Длительность: {info['duration']}с | Канал: {info.get('channel', '?')}")

    # 2. Download audio
    print(f"   ⬇️  Скачиваю аудио...")
    audio_path = download_audio(url, info["id"])
    print(f"   📁 {audio_path}")

    # 3. Transcribe
    transcript = transcribe(audio_path)

    # 4. Summarize
    print(f"   🧠 Выжимаю суть через DeepSeek...")
    insights = summarize(
        transcript["text"],
        video_title=info["title"],
        video_description=info.get("description", ""),
    )

    # 5. Save results
    result = {
        "video": info,
        "transcript": transcript,
        "insights": insights,
        "processed_at": datetime.now().isoformat(),
        "pipeline_version": __version__,
    }

    result_path = output_dir / f"{info['id']}_insight.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Also save markdown summary
    md_path = output_dir / f"{info['id']}_summary.md"
    md = format_markdown(result)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    # Clean up audio
    audio_path.unlink(missing_ok=True)

    # Print summary
    print(f"\n   {'='*50}")
    print(f"   📊 {insights.get('title', info['title'])}")
    print(f"   {'='*50}")
    print(f"   {insights.get('summary', '')[:200]}")
    if insights.get("key_insights"):
        print(f"\n   💡 Ключевые тезисы:")
        for i, ins in enumerate(insights["key_insights"], 1):
            print(f"      {i}. {ins}")
    if insights.get("actionable_items"):
        print(f"\n   🎯 Что делать:")
        for i, act in enumerate(insights["actionable_items"], 1):
            print(f"      {i}. {act}")
    fluff = insights.get("fluff_score", 1.0)
    print(f"\n   💧 Воды: {fluff*100:.0f}%")
    print(f"   📁 Результат: {result_path}")

    return result


def format_markdown(result: dict) -> str:
    """Форматировать результат как Markdown."""
    info = result["video"]
    ins = result["insights"]

    md = f"# {ins.get('title', info['title'])}\n\n"
    md += f"**Источник:** {info['url']}\n"
    md += f"**Канал:** {info.get('channel', '')}\n"
    md += f"**Дата:** {info.get('upload_date', '')}\n"
    md += f"**Длительность:** {info['duration'] // 60} мин\n\n"
    md += f"---\n\n"
    md += f"## Суть\n\n{ins.get('summary', '')}\n\n"

    if ins.get("key_insights"):
        md += f"## Ключевые тезисы\n\n"
        for i, ki in enumerate(ins["key_insights"], 1):
            md += f"{i}. {ki}\n"
        md += "\n"

    if ins.get("actionable_items"):
        md += f"## Что делать\n\n"
        for i, ai in enumerate(ins["actionable_items"], 1):
            md += f"- [ ] {ai}\n"
        md += "\n"

    if ins.get("key_numbers"):
        md += f"## Цифры и статистика\n\n"
        for kn in ins["key_numbers"]:
            md += f"- {kn}\n"
        md += "\n"

    if ins.get("timestamps"):
        md += f"## Ключевые моменты\n\n"
        for ts in ins["timestamps"]:
            md += f"- **[{ts['time']}]** {ts['topic']}\n"
        md += "\n"

    md += f"---\n*Воды: {ins.get('fluff_score', 1.0)*100:.0f}% | Обработано: {result.get('processed_at', '')}*\n"
    return md


def process_channel(
    channel_url: str,
    max_videos: int = 0,
    until_video_id: Optional[str] = None,
) -> list[dict]:
    """Обработать все видео канала."""
    print(f"\n🔍 Сканирую канал: {channel_url}")
    videos = fetch_channel_videos(channel_url, max_videos)

    if until_video_id:
        # Найти индекс видео и обрезать список до него (включая его)
        ids = [v["id"] for v in videos]
        if until_video_id in ids:
            idx = ids.index(until_video_id)
            videos = videos[: idx + 1]
            print(f"   Обрабатываю {len(videos)} видео (до {until_video_id})")
        else:
            print(f"   ⚠️  Видео {until_video_id} не найдено в канале")

    print(f"   Всего видео: {len(videos)}")
    total_duration = sum(v["duration"] for v in videos) / 60
    print(f"   Общая длительность: {total_duration:.0f} мин")
    print(f"   Примерное время обработки: {total_duration * 0.15:.0f} мин (на M4 с mlx-whisper)")

    results = []
    for i, video in enumerate(videos, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(videos)}] {video['title'][:80]}")
        print(f"{'='*60}")
        try:
            result = process_video(video["url"])
            results.append(result)
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            continue

        # Пауза между видео чтобы не триггерить rate limiting
        if i < len(videos):
            time.sleep(3)

    # Save channel summary
    summary_path = FETCH_DIR / "channel_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "channel": channel_url,
            "processed_at": datetime.now().isoformat(),
            "total_videos": len(videos),
            "successful": len(results),
            "videos": [r["video"] for r in results],
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Готово! Обработано {len(results)}/{len(videos)} видео")
    print(f"📁 Результаты: {FETCH_DIR}")
    print(f"{'='*60}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Insight — транскрибация и выжимка сути из YouTube видео",
    )
    parser.add_argument("url", nargs="?", help="URL одного видео")
    parser.add_argument("--channel", "-c", help="URL канала для пакетной обработки")
    parser.add_argument("--max", "-m", type=int, default=0, help="Макс. количество видео с канала")
    parser.add_argument("--until", "-u", help="ID видео — обработать все видео до этого (включая его)")
    parser.add_argument("--urls", help="Список URL через запятую")
    parser.add_argument("--output", "-o", help="Директория для результатов")
    parser.add_argument("--version", action="version", version=f"youtube-insight {__version__}")

    args = parser.parse_args()

    # Проверки
    if not check_yt_dlp():
        print("❌ yt-dlp не установлен. Выполни: pip install yt-dlp")
        sys.exit(1)

    backend = detect_whisper_backend()
    if backend == "none":
        print("❌ Whisper не установлен. Выполни:")
        print("   pip install mlx-whisper   (Mac M1-M4, рекомендуется)")
        sys.exit(1)
    print(f"🎤 Whisper backend: {backend}")

    output_dir = Path(args.output) if args.output else None

    # Single video
    if args.url:
        process_video(args.url, output_dir)

    # Channel
    elif args.channel:
        process_channel(args.channel, args.max, args.until)

    # Multiple URLs
    elif args.urls:
        urls = [u.strip() for u in args.urls.split(",")]
        for url in urls:
            process_video(url, output_dir)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
