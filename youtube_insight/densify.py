"""Выжимка сути из транскрипта через DeepSeek V4."""

import json
import os
import sys
from typing import Optional

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1"

SYSTEM_PROMPT = """Ты — профессиональный аналитик контента. Твоя задача — извлечь из транскрипта YouTube-видео только САМУЮ СУТЬ, без воды.

Правила:
1. Убери всё что не несёт смысловой нагрузки: приветствия, прощания, self-promo, «подписывайтесь на канал», «всем привет», разговоры не по теме.
2. Выдели 3-5 КЛЮЧЕВЫХ ТЕЗИСОВ — то ради чего видео было снято.
3. Найди actionable items — что конкретно можно сделать/применить после просмотра.
4. Если есть цифры, даты, проценты, конкретные названия — сохрани их.
5. Формат ответа — СТРОГО JSON без markdown-обёртки:

{
  "title": "Оригинальное название видео",
  "summary": "2-3 предложения — суть видео",
  "key_insights": [
    "Тезис 1",
    "Тезис 2",
    "Тезис 3"
  ],
  "actionable_items": [
    "Что сделать 1",
    "Что сделать 2"
  ],
  "key_numbers": ["цифра/статистика 1"],
  "timestamps": [
    {"time": "MM:SS", "topic": "О чём речь в этом моменте"}
  ],
  "fluff_score": 0.0
}

fluff_score: насколько много воды в видео (0.0 = чистые инсайты, 1.0 = 100% воды).
Отвечай ТОЛЬКО JSON, без объяснений."""


def summarize(transcript_text: str, video_title: str = "", video_description: str = "") -> dict:
    """Прогнать транскрипт через DeepSeek для извлечения сути.

    Args:
        transcript_text: Полный текст транскрипта.
        video_title: Название видео.
        video_description: Описание видео.

    Returns:
        dict с ключами: title, summary, key_insights, actionable_items, etc.
    """
    if not DEEPSEEK_KEY:
        print("  ⚠️  DEEPSEEK_API_KEY не задан — возвращаю сырой транскрипт")
        return {
            "title": video_title or "Без названия",
            "summary": transcript_text[:500] + "...",
            "key_insights": [],
            "actionable_items": [],
            "key_numbers": [],
            "timestamps": [],
            "fluff_score": 1.0,
        }

    # Обрежем транскрипт до ~50K символов (входит в контекст)
    max_chars = 50000
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars] + "\n... (транскрипт обрезан)"

    user_message = f"""Название видео: {video_title}
Описание: {video_description}

ТРАНСКРИПТ:
{transcript_text}

Извлеки суть по JSON-схеме."""

    try:
        import urllib.request
        import ssl
        import certifi

        body = json.dumps({
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }).encode()

        req = urllib.request.Request(
            f"{DEEPSEEK_ENDPOINT}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
            },
        )

        # Use certifi's CA bundle for SSL (fixes macOS Python SSL issues)
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = json.loads(resp.read())

        content = data["choices"][0]["message"]["content"]

        # Убрать markdown-обёртку если есть
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]

        result = json.loads(content)
        return result

    except Exception as e:
        print(f"  ⚠️  Ошибка DeepSeek: {e}")
        return {
            "title": video_title or "Без названия",
            "summary": transcript_text[:500] + "...",
            "key_insights": [],
            "actionable_items": [],
            "key_numbers": [],
            "timestamps": [],
            "fluff_score": 1.0,
        }
