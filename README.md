# 🎬 YouTube Insight

**YouTube видео → транскрибация → выжимка сути без воды.**  
Whisper + DeepSeek V4. На своём железе. Полная приватность.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

## Что это

Ты даёшь ссылку на YouTube видео (или локальный файл) — скилл скачивает аудио, транскрибирует через Whisper, и прогоняет через DeepSeek V4 чтобы оставить **только суть**. Никаких «всем привет подписывайтесь на канал ставьте лайк» — только инсайты, тезисы, actionable items.

На выходе: JSON с полными данными + готовый Markdown-конспект.

## Почему это круто

- ⚡ **8x быстрее реального времени** на Mac M1-M4 (mlx-whisper, нативный Metal)
- 🧠 **Выжимает суть** — DeepSeek V4 сам убирает воду, оставляет тезисы и что делать
- 🔒 **Полная приватность** — всё локально, никакие данные не уходят третьим лицам
- 💰 **$0 после установки** — только API токены DeepSeek (~$0.01 за видео)
- 📁 **Любые форматы** — YouTube, локальные .mp4/.wav/.mp3, целые папки
- 🤝 **Проводит за руку** — интерактивный мастер `wizard.py` всё проверит и поставит

## Быстрый старт

```bash
git clone https://github.com/Mobiss11/youtube-insight.git
cd youtube-insight

# Мастер проведёт за руку — всё проверит и поставит
python wizard.py
```

Мастер **автоматически**:
1. Проверит есть ли [Whisper-Skill](https://github.com/Mobiss11/Whisper-Skill) — если нет, поставит
2. Определит твоё железо (Mac M4 → mlx-whisper, другие → faster-whisper)
3. Поставит yt-dlp, ffmpeg, certifi
4. Настроит DeepSeek API ключ
5. Запустит тестовый прогон на 19-секундном видео

## Использование

### YouTube

```bash
youtube-insight "https://www.youtube.com/watch?v=VIDEO_ID"
youtube-insight --channel "@channel_name"          # весь канал
youtube-insight --channel "@channel" --max 5        # последние 5 видео
youtube-insight --channel "@channel" --until "ID"   # до конкретного видео
youtube-insight --urls "url1,url2,url3"             # несколько
```

### Локальные файлы

```bash
youtube-insight --file "/path/to/video.mp4"
youtube-insight --file "podcast.wav" --title "Мой подкаст"
youtube-insight --dir "/path/to/folder"             # вся папка
```

### Python API

```python
from youtube_insight.pipeline import process_video, process_channel

result = process_video("https://youtube.com/watch?v=...")
print(result["insights"]["summary"])
print(result["insights"]["key_insights"])
```

## Формат вывода

**`VIDEO_ID_insight.json`:**
```json
{
  "video": {"title": "...", "duration": 809, "url": "..."},
  "transcript": {"text": "...", "segments": [...]},
  "insights": {
    "summary": "2-3 предложения сути",
    "key_insights": ["Тезис 1", "Тезис 2", "Тезис 3"],
    "actionable_items": ["Что сделать 1", "Что сделать 2"],
    "key_numbers": ["цифры и статистика"],
    "timestamps": [{"time": "05:30", "topic": "О чём речь"}],
    "fluff_score": 0.30
  }
}
```

**`VIDEO_ID_summary.md`** — готовый Markdown-конспект.

## Железо и скорость

| Железо | Whisper бэкенд | 10 мин видео | 1 час видео |
|---|---|---|---|
| Mac M1/M2/M3/M4 | mlx-whisper | ~30 сек | ~3 мин |
| NVIDIA GPU | faster-whisper (CUDA) | ~40 сек | ~4 мин |
| Intel/AMD CPU | faster-whisper (CPU) | ~5 мин | ~30 мин |

## Интеграция с Whisper-Skill

YouTube Insight использует [Whisper-Skill](https://github.com/Mobiss11/Whisper-Skill) для транскрибации. Если он не установлен — мастер поставит его автоматически. Whisper-Skill сам определяет оптимальный бэкенд под твоё железо (mlx-whisper / faster-whisper / whisper.cpp / whisperx / openvino).

## Требования

- Python 3.11+
- ffmpeg (для локальных видео)
- [Whisper-Skill](https://github.com/Mobiss11/Whisper-Skill) (мастер поставит сам)
- DeepSeek API ключ (опционально — для выжимки сути)

## Структура

```
youtube-insight/
├── wizard.py                  # Интерактивный мастер установки
├── setup.sh                   # Авто-установка одной командой
├── SKILL.md                   # Скилл для AI-ассистентов
├── README.md                  # ← ты здесь
└── youtube_insight/
    ├── fetch.py               # yt-dlp: скачивание YouTube
    ├── transcribe.py          # Whisper: транскрибация
    ├── densify.py             # DeepSeek: выжимка сути
    └── pipeline.py            # Оркестратор: CLI + Python API
```

## Лицензия

MIT

## Ссылки

- [Whisper-Skill](https://github.com/Mobiss11/Whisper-Skill) — фундамент для транскрибации
- [DeepSeek API](https://platform.deepseek.com/api_keys) — получить ключ
- [Vane-Skill](https://github.com/Mobiss11/vane-skill) — AI поисковик
