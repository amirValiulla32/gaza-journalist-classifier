#!/usr/bin/env python3
"""
Gaza Journalist Video Classifier
Fully local processing: whisper.cpp + DeepSeek LLM
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
import requests

# Configuration
WHISPER_CPP_PATH = os.getenv("WHISPER_CPP_PATH", "./whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", "./whisper.cpp/models/ggml-base.bin")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "deepseek-v3.1:671b-cloud")

# Classification categories and tags
CATEGORIES = [
    "Destruction of Property",
    "Displacement",
    "IDF",
    "Jewish Dissent",
    "Inhumane Acts",
    "Imprisonment",
    "Resilience",
    "Starvation of Civilian",
    "Testimonials",
    "Willful Killing"
]

TAGS = [
    "Birth Prevention",
    "Ceasefire Violation",
    "Children",
    "Food",
    "Journalists",
    "Healthcare workers",
    "Hospitals",
    "Hostages",
    "Mosques",
    "Prisoners",
    "Schools",
    "Water",
    "Repression",
    "Torture",
    "Testimonials",
    "Women",
    "IDF",
    "Settlers",
    "Other"
]


def extract_audio(video_path: str, output_path: str) -> bool:
    """Extract audio from video file using ffmpeg."""
    try:
        print(f"📹 Extracting audio from {video_path}...")
        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # WAV format for whisper.cpp
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",  # Mono
            "-y",  # Overwrite output
            output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Audio extracted to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error extracting audio: {e}")
        return False
    except FileNotFoundError:
        print("❌ ffmpeg not found. Install with: brew install ffmpeg")
        return False


def transcribe_audio(audio_path: str, language: str = "auto") -> str:
    """
    Transcribe audio using whisper.cpp.

    Args:
        audio_path: Path to audio file
        language: Language code ('en', 'ar', 'auto' for auto-detect)
    """
    try:
        print(f"🎤 Transcribing audio with whisper.cpp (language: {language})...")

        # Check if whisper.cpp exists
        if not os.path.exists(WHISPER_CPP_PATH):
            print(f"❌ whisper.cpp not found at {WHISPER_CPP_PATH}")
            print("Clone and build: git clone https://github.com/ggerganov/whisper.cpp && cd whisper.cpp && make")
            return ""

        # Check if model exists
        if not os.path.exists(WHISPER_MODEL_PATH):
            print(f"❌ Whisper model not found at {WHISPER_MODEL_PATH}")
            print("Download model: cd whisper.cpp && bash ./models/download-ggml-model.sh base.en")
            return ""

        # Build whisper command
        cmd = [
            WHISPER_CPP_PATH,
            "-m", WHISPER_MODEL_PATH,
            "-f", audio_path,
            "-nt",  # No timestamps in output
        ]

        # Add language parameter
        if language != "auto":
            cmd.extend(["-l", language])
        # If auto, let whisper detect the language

        # Run whisper.cpp
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        transcript = result.stdout.strip()
        print(f"✅ Transcription complete ({len(transcript)} characters)")
        return transcript

    except subprocess.CalledProcessError as e:
        print(f"❌ Error transcribing audio: {e.stderr}")
        return ""
    except Exception as e:
        print(f"❌ Error: {e}")
        return ""


def classify_content(transcript: str, ocr_text: str = None) -> dict:
    """Classify transcript using local DeepSeek LLM via Ollama.

    Args:
        transcript: Audio transcription text
        ocr_text: Optional text extracted from video frames (on-screen text)
    """
    try:
        print(f"🤖 Classifying content with DeepSeek...")

        # Build enhanced prompt with OCR if available
        content_to_analyze = f"AUDIO TRANSCRIPT:\n{transcript}"

        if ocr_text and ocr_text.strip():
            content_to_analyze += f"\n\nON-SCREEN TEXT (from video frames):\n{ocr_text}"
            print(f"📝 Including OCR text ({len(ocr_text)} characters)")

        system_prompt = f"""You are analyzing journalist reports about Gaza to classify them into categories and tags.

CATEGORIES (choose exactly ONE):
{json.dumps(CATEGORIES, indent=2)}

TAGS (choose ALL that apply, can be multiple or none):
{json.dumps(TAGS, indent=2)}

Analyze BOTH the audio transcript AND any on-screen text carefully.
On-screen text may include: location names, casualty numbers, dates, hospital/school names, journalist names, organization logos.

Provide:
1. The single most appropriate category
2. All relevant tags that apply to the content
3. Use information from BOTH sources to make accurate classification

Respond with valid JSON only in this exact format:
{{
  "category": "category name here",
  "tags": ["tag1", "tag2"],
  "confidence": "high/medium/low",
  "reasoning": "brief explanation mentioning key details from audio and/or on-screen text"
}}

Content to classify:

{content_to_analyze}"""

        # Call Ollama API
        response = requests.post(
            LOCAL_LLM_URL,
            json={
                "model": LOCAL_LLM_MODEL,
                "prompt": system_prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )

        if response.status_code != 200:
            print(f"❌ LLM API error: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "category": "Unknown",
                "tags": [],
                "confidence": "low",
                "reasoning": f"API Error: {response.status_code}"
            }

        result = json.loads(response.json()["response"])
        print(f"✅ Classification complete")
        return result

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to LLM at {LOCAL_LLM_URL}")
        print("Make sure Ollama is running: ollama serve")
        print(f"And model is pulled: ollama pull {LOCAL_LLM_MODEL}")
        return {
            "category": "Unknown",
            "tags": [],
            "confidence": "low",
            "reasoning": "LLM not available"
        }
    except Exception as e:
        print(f"❌ Error classifying content: {e}")
        return {
            "category": "Unknown",
            "tags": [],
            "confidence": "low",
            "reasoning": f"Error: {str(e)}"
        }


def classify_video(video_path: str, language: str = "auto", use_ocr: bool = False) -> dict:
    """
    Main function to process a video file.

    Args:
        video_path: Path to video file
        language: Language code ('en', 'ar', 'auto' for auto-detect)
        use_ocr: Enable OCR text extraction from video frames (default: False)
    """
    video_path = Path(video_path).resolve()

    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return None

    print(f"\n{'='*60}")
    print(f"Processing: {video_path.name}")
    print(f"{'='*60}\n")

    # Create temporary audio file (WAV for whisper.cpp)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio_path = temp_audio.name

    try:
        # Step 1: Extract audio
        if not extract_audio(str(video_path), temp_audio_path):
            return None

        # Step 2: Transcribe
        transcript = transcribe_audio(temp_audio_path, language)
        if not transcript:
            return None

        # Step 3: Extract OCR text (optional)
        ocr_text = None
        if use_ocr:
            try:
                from extract_text_from_video import extract_text_from_video
                print(f"\n📸 Extracting on-screen text with OCR...")
                ocr_result = extract_text_from_video(str(video_path), num_frames=5)
                if ocr_result and ocr_result.get('combined_text'):
                    ocr_text = ocr_result['combined_text']
                    print(f"✅ OCR extracted {len(ocr_text)} characters")
                else:
                    print(f"⚠️ No text detected in video frames")
            except ImportError:
                print(f"⚠️ OCR not available (install pytesseract and tesseract)")
            except Exception as e:
                print(f"⚠️ OCR error: {e}")

        # Step 4: Classify (with OCR if available)
        classification = classify_content(transcript, ocr_text)

        # Compile results
        result = {
            "video_file": str(video_path),
            "video_name": video_path.name,
            "language": language,
            "transcript": transcript,
            "ocr_text": ocr_text if use_ocr else None,
            "classification": classification
        }

        return result

    finally:
        # Cleanup temporary audio file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python classify_video.py <path_to_video> [language] [--ocr]")
        print("\nExamples:")
        print("  python classify_video.py video.mp4")
        print("  python classify_video.py video.mp4 ar")
        print("  python classify_video.py video.mp4 auto --ocr")
        print("\nLanguage codes: en (English), ar (Arabic), auto (auto-detect)")
        print("--ocr: Extract on-screen text for enhanced classification")
        print("\nSetup requirements:")
        print("1. Install ffmpeg: brew install ffmpeg")
        print("2. Clone whisper.cpp: git clone https://github.com/ggerganov/whisper.cpp")
        print("3. Build whisper.cpp: cd whisper.cpp && make")
        print("4. Download model: cd whisper.cpp && bash ./models/download-ggml-model.sh base")
        print("5. Install Ollama: https://ollama.ai")
        print("6. Pull DeepSeek: ollama pull deepseek-v3.1:671b-cloud")
        print("7. Start Ollama: ollama serve")
        print("\nOptional (for OCR):")
        print("8. Install tesseract: brew install tesseract tesseract-lang")
        print("9. Install Python packages: pip install pytesseract pillow")
        sys.exit(1)

    video_path = sys.argv[1]
    language = "auto"
    use_ocr = False

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg == "--ocr":
            use_ocr = True
        elif not arg.startswith("--"):
            language = arg

    result = classify_video(video_path, language, use_ocr)

    if result:
        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}\n")
        print(f"📁 Video: {result['video_name']}")
        print(f"\n📝 Transcript Preview:\n{result['transcript'][:500]}...")
        print(f"\n📊 Classification:")
        print(f"   Category: {result['classification']['category']}")
        print(f"   Tags: {', '.join(result['classification']['tags']) if result['classification']['tags'] else 'None'}")
        print(f"   Confidence: {result['classification']['confidence']}")
        print(f"   Reasoning: {result['classification']['reasoning']}")

        # Save to JSON file
        output_file = Path(video_path).stem + "_classification.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Full results saved to: {output_file}")
        print(f"\n{'='*60}\n")
    else:
        print("\n❌ Classification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
