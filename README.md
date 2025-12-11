# Gaza Journalist Video Classifier

Fully local video classification pipeline for categorizing journalist reports about Gaza.

## Features

- **100% Local**: No API costs, full privacy
- **Audio Extraction**: ffmpeg
- **Transcription**: whisper.cpp (fast C++ implementation)
- **Classification**: DeepSeek LLM via Ollama
- **Structured Output**: JSON with category, tags, confidence, and reasoning

## Quick Setup

### 1. Install Dependencies

```bash
# Install ffmpeg
brew install ffmpeg

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Setup whisper.cpp

```bash
# Clone and build
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make

# Download English model
bash ./models/download-ggml-model.sh base.en

cd ..
```

### 3. Setup Ollama + DeepSeek

```bash
# Install Ollama from https://ollama.ai
# Or with brew:
brew install ollama

# Pull DeepSeek model
ollama pull deepseek-r1:latest

# Start Ollama server
ollama serve
```

## Usage

```bash
# Basic usage
python classify_video.py path/to/video.mp4

# Example
python classify_video.py ~/Downloads/gaza_report.mp4
```

## Output

The script outputs:
1. **Console**: Classification results with transcript preview
2. **JSON File**: `{video_name}_classification.json` with full details

### Example Output

```json
{
  "video_file": "/path/to/video.mp4",
  "video_name": "video.mp4",
  "transcript": "Full transcript text...",
  "classification": {
    "category": "Willful Killing",
    "tags": ["Children", "Hospitals", "Journalists"],
    "confidence": "high",
    "reasoning": "Video shows direct evidence of..."
  }
}
```

## Categories

1. Destruction of Property
2. Displacement
3. IDF
4. Jewish Dissent
5. Inhumane Acts
6. Imprisonment
7. Resilience
8. Starvation of Civilian
9. Testimonials
10. Willful Killing

## Tags (Optional, Multiple)

Birth Prevention, Ceasefire Violation, Children, Food, Journalists, Healthcare workers, Hospitals, Hostages, Mosques, Prisoners, Schools, Water, Repression, Torture, Testimonials, Women, IDF, Settlers, Other

## Configuration

Environment variables for customization:

```bash
# Whisper.cpp paths
export WHISPER_CPP_PATH="./whisper.cpp/main"
export WHISPER_MODEL_PATH="./whisper.cpp/models/ggml-base.en.bin"

# LLM configuration
export LOCAL_LLM_URL="http://localhost:11434/api/generate"
export LOCAL_LLM_MODEL="deepseek-r1:latest"
```

## Troubleshooting

**"ffmpeg not found"**
```bash
brew install ffmpeg
```

**"whisper.cpp not found"**
```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp && make
```

**"Cannot connect to LLM"**
```bash
# Start Ollama
ollama serve

# In another terminal, pull model
ollama pull deepseek-r1:latest
```

**"Whisper model not found"**
```bash
cd whisper.cpp
bash ./models/download-ggml-model.sh base.en
```

## Future Enhancements

- [ ] Batch processing multiple videos
- [ ] Arabic language support
- [ ] Web UI for easier use
- [ ] Database storage
- [ ] Human review interface
- [ ] Video preview clips

## License

MIT License - For humanitarian documentation purposes
