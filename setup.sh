#!/bin/bash
set -e

echo "🚀 Gaza Journalist Video Classifier - Setup"
echo "==========================================="
echo ""

# Check for brew
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Install from https://brew.sh"
    exit 1
fi

# Install ffmpeg
echo "📦 Installing ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    brew install ffmpeg
else
    echo "✅ ffmpeg already installed"
fi

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

# Setup whisper.cpp
echo ""
echo "🎤 Setting up whisper.cpp..."
if [ ! -d "whisper.cpp" ]; then
    git clone https://github.com/ggerganov/whisper.cpp
    cd whisper.cpp
    make
    bash ./models/download-ggml-model.sh base.en
    cd ..
    echo "✅ whisper.cpp installed and model downloaded"
else
    echo "✅ whisper.cpp already exists"
fi

# Install Ollama
echo ""
echo "🤖 Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    brew install ollama
else
    echo "✅ Ollama already installed"
fi

# Pull DeepSeek model
echo ""
echo "📥 Pulling DeepSeek model..."
ollama pull deepseek-r1:latest

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use the classifier:"
echo "  1. Start Ollama: ollama serve"
echo "  2. In another terminal: python classify_video.py your_video.mp4"
echo ""
