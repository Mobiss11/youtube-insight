#!/bin/bash
set -e

echo "========================================="
echo "  YouTube Insight — установка"
echo "========================================="
echo ""

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установи Python 3.11+"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VERSION"

# Install yt-dlp
echo ""
echo "📦 Устанавливаю yt-dlp..."
pip3 install yt-dlp -q 2>/dev/null || pip install yt-dlp -q

# Install Whisper (auto-detect best for platform)
echo "📦 Устанавливаю Whisper..."
if [[ "$(uname)" == "Darwin" ]] && [[ "$(uname -m)" == "arm64" ]]; then
    echo "   🍎 Apple Silicon — mlx-whisper"
    pip3 install mlx-whisper -q 2>/dev/null || pip install mlx-whisper -q
else
    echo "   💻 Стандартный — faster-whisper"
    pip3 install faster-whisper -q 2>/dev/null || pip install faster-whisper -q
fi

# Install the package itself
echo "📦 Устанавливаю youtube-insight..."
pip3 install -e . -q 2>/dev/null || pip install -e . -q

echo ""
echo "========================================="
echo "✅ Установка завершена!"
echo ""
echo "Использование:"
echo "  youtube-insight \"https://youtube.com/watch?v=VIDEO_ID\""
echo "  youtube-insight --channel \"@channel_name\""
echo "  youtube-insight --channel \"@channel\" --max 5"
echo "  youtube-insight --channel \"@channel\" --until \"VIDEO_ID\""
echo "  youtube-insight --urls \"url1,url2,url3\""
echo ""
echo "⚠️  Установи переменную окружения для DeepSeek:"
echo "  export DEEPSEEK_API_KEY=sk-..."
echo ""
echo "========================================="
