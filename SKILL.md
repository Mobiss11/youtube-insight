---
name: youtube-insight
description: Используй когда пользователь хочет транскрибировать YouTube видео, извлечь ключевые инсайты из видео/канала, убрать воду из контента, сделать конспект видео, обработать весь YouTube-канал, или построить пайплайн «видео → транскрибация → выжимка сути». Активируй при запросах: "сделай конспект этого видео", "выжми суть из канала", "транскрибируй YouTube", "обработай видео @channel", "убери воду из видео", "extract insights from YouTube", "transcribe channel". Скилл автоматически определяет железо, выбирает оптимальный Whisper-бэкенд (mlx-whisper на M1-M4 в 5x быстрее), скачивает аудио через yt-dlp, транскрибирует, и прогоняет через DeepSeek V4 для извлечения только сути без воды.
---

# YouTube Insight — транскрибация и выжимка сути

Скачивает видео с YouTube, транскрибирует через Whisper (mlx на M1-M4, faster-whisper на других), и прогоняет через DeepSeek V4 для извлечения **только ключевых инсайтов** — без приветствий, self-promo, и разговоров не по теме.

> ⚡ **Скорость на Mac Mini M4**: 10-минутное видео → ~30 секунд транскрибация + ~3 секунды DeepSeek = **~35 секунд на видео**.

## Архитектура

```
YouTube URL / Channel
        │
        ▼
   yt-dlp (скачивает аудио WAV)
        │
        ▼
   Whisper (mlx-whisper / faster-whisper / openai-whisper)
   Авто-выбор бэкенда под железо
        │
        ▼
   DeepSeek V4 Flash (deepseek-chat)
   Промпт: "Убери воду, оставь только инсайты"
        │
        ▼
   output/
   ├── VIDEO_ID_insight.json   # Полный результат
   └── VIDEO_ID_summary.md     # Markdown-конспект
```

## Быстрый старт

```bash
git clone https://github.com/Mobiss11/youtube-insight.git
cd youtube-insight
bash setup.sh
export DEEPSEEK_API_KEY=sk-...
```

## Использование

### Одно видео

```bash
youtube-insight "https://www.youtube.com/watch?v=VIDEO_ID"
```

Или просто дай нейронке ссылку:
> «Сделай конспект этого видео: https://youtube.com/watch?v=...»

### Несколько видео

```bash
youtube-insight --urls "https://youtube.com/watch?v=ID1,https://youtube.com/watch?v=ID2"
```

### Весь канал

```bash
# Все видео канала
youtube-insight --channel "https://www.youtube.com/@pro_money_tg"

# Только последние 5 видео
youtube-insight --channel "@pro_money_tg" --max 5

# Все видео до определенного (включая его)
youtube-insight --channel "@pro_money_tg" --until "VIDEO_ID"
```

### Программный API

```python
from youtube_insight.pipeline import process_video, process_channel

# Одно видео
result = process_video("https://youtube.com/watch?v=XXX")

# Весь канал
results = process_channel("@channel_name", max_videos=10)

# Доступ к данным
print(result["insights"]["summary"])        # 2-3 предложения сути
print(result["insights"]["key_insights"])   # Список ключевых тезисов
print(result["insights"]["actionable_items"]) # Что делать
print(result["insights"]["fluff_score"])     # 0.0 = чистое золото, 1.0 = вода
```

## Формат вывода

Каждое видео даёт два файла:

**`VIDEO_ID_insight.json`** — полные данные:
```json
{
  "video": {"id": "...", "title": "...", "url": "...", "duration": 600},
  "transcript": {"text": "полный текст...", "segments": [...]},
  "insights": {
    "title": "Название видео",
    "summary": "2-3 предложения — суть",
    "key_insights": ["Тезис 1", "Тезис 2", "Тезис 3"],
    "actionable_items": ["Что сделать 1"],
    "key_numbers": ["цифра/статистика"],
    "timestamps": [{"time": "05:30", "topic": "О чём речь"}],
    "fluff_score": 0.35
  }
}
```

**`VIDEO_ID_summary.md`** — готовый Markdown-конспект:
- Название, канал, длительность
- Суть (2-3 предложения)
- Ключевые тезисы (нумерованный список)
- Что делать (checklist)
- Цифры и статистика
- Ключевые моменты с таймкодами
- Оценка воды

## Выбор Whisper-бэкенда

Скилл автоматически определяет железо:

| Железо | Бэкенд | Скорость (10 мин видео) |
|---|---|---|
| Mac M1/M2/M3/M4 | **mlx-whisper** (нативный Metal) | ~30 сек |
| Mac Intel | faster-whisper (CPU) | ~3 мин |
| Linux + NVIDIA | faster-whisper (CUDA) | ~40 сек |
| Linux без GPU | faster-whisper (CPU) | ~5 мин |
| Windows | faster-whisper (CPU) | ~5 мин |

Можно форсировать бэкенд:
```bash
# Установить mlx-whisper (Mac only)
pip install mlx-whisper

# Установить faster-whisper
pip install faster-whisper

# Установить оригинальный Whisper
pip install openai-whisper
```

## Промпт DeepSeek

Системный промпт заточен на выжимку сути:

```
Ты — профессиональный аналитик контента.
Убери: приветствия, прощания, self-promo, «подписывайтесь».
Выдели: 3-5 ключевых тезисов, actionable items, цифры/даты/проценты.
Оцени: сколько воды во fluff_score (0.0 = чистое золото).
```

Модель: `deepseek-chat` (DeepSeek V4 Flash без thinking — идеально для суммаризации).

## Для всего канала @pro_money_tg

Примерный расчёт для канала с ~100 видео по 10 минут:

```
1. Скачивание аудио:       ~5 мин (yt-dlp, зависит от интернета)
2. Транскрибация:          ~50 мин (mlx-whisper на M4, ~30 сек/видео)
3. Выжимка через DeepSeek: ~10 мин (API, ~3-5 сек/видео)
4. Итого:                  ~65 мин на 100 видео
```

На выходе: 100 JSON-файлов + 100 Markdown-конспектов + `channel_summary.json`.

## Интеграция с Whisper-Skill

Если у тебя уже установлен [Whisper-Skill](https://github.com/Mobiss11/Whisper-Skill), скилл использует его mlx-whisper автоматически. Ничего дополнительно ставить не нужно — определит и подхватит.

## Решение проблем

### "yt-dlp не установлен"
```bash
pip install yt-dlp
```

### "Whisper не установлен"
```bash
# Mac M1-M4
pip install mlx-whisper

# Другие
pip install faster-whisper
```

### "Sign in to confirm you're not a bot" (YouTube rate limiting)
- Добавь паузу между видео: `--sleep 5` (встроено 3 сек)
- Используй куки браузера: `yt-dlp --cookies-from-browser chrome ...`

### DeepSeek не работает
- Проверь `echo $DEEPSEEK_API_KEY`
- Проверь баланс на platform.deepseek.com

## Файлы скилла

| Файл | Назначение |
|---|---|
| `SKILL.md` | ← ты здесь |
| `setup.sh` | Установка одной командой |
| `youtube_insight/fetch.py` | Скачивание аудио через yt-dlp |
| `youtube_insight/transcribe.py` | Транскрибация (mlx/faster/openai) |
| `youtube_insight/densify.py` | Выжимка сути через DeepSeek |
| `youtube_insight/pipeline.py` | Оркестратор: CLI + Python API |
| `output/` | Результаты (создаётся авто) |

## Лицензия

MIT
