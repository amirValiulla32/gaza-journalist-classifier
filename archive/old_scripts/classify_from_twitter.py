#!/usr/bin/env python3
"""
Standalone Twitter Video Classifier - Download and classify in one command.

This script combines Twitter video download + audio transcription + OCR + LLM classification
into a single convenient command. Completely standalone, doesn't depend on other scripts.

Usage:
    python3 classify_from_twitter.py "https://twitter.com/user/status/123456"
    python3 classify_from_twitter.py "https://twitter.com/user/status/123456" --keep-video
    python3 classify_from_twitter.py --urls urls.txt --output results/
"""

import os
import sys
import json
import subprocess
import tempfile
import argparse
from pathlib import Path
from typing import Dict, Optional, List
import re
import time

# ============================================================================
# Configuration
# ============================================================================

WHISPER_CPP_PATH = "./whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL_PATH = "./whisper.cpp/models/ggml-base.bin"
LOCAL_LLM_MODEL = "deepseek-v3.1:671b-cloud"  # Ollama model for classification
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Classification categories and tags (matching classify_video.py format)
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

# ============================================================================
# Twitter Download Functions
# ============================================================================

def download_from_twitter(url: str, output_dir: str = ".") -> Optional[Dict]:
    """
    Download video from Twitter URL using yt-dlp.

    Args:
        url: Twitter/X post URL
        output_dir: Directory to save video

    Returns:
        Dictionary with video info or None if failed
    """
    print(f"\nDownloading video from Twitter...")

    # Extract tweet ID from URL
    tweet_id_match = re.search(r'/status/(\d+)', url)
    if not tweet_id_match:
        print(f"[ERROR] Invalid Twitter URL: {url}")
        return None

    tweet_id = tweet_id_match.group(1)
    output_path = Path(output_dir) / f"tweet_{tweet_id}.mp4"

    # yt-dlp command
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]",
        "-o", str(output_path),
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and output_path.exists():
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"[+] Downloaded: {output_path.name} ({file_size_mb:.1f} MB)\n")

            return {
                "tweet_id": tweet_id,
                "source_url": url,
                "video_file": str(output_path),
                "file_size_mb": round(file_size_mb, 2),
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
        else:
            print(f"[ERROR] Download failed: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print(f"[ERROR] Download timeout after 120 seconds")
        return None
    except FileNotFoundError:
        print(f"[ERROR] yt-dlp not found. Install with: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"[ERROR] Download error: {str(e)}")
        return None

# ============================================================================
# Audio Processing Functions
# ============================================================================

def extract_audio(video_path: str, output_path: str) -> bool:
    """Extract audio from video using ffmpeg."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # WAV PCM format
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",  # Mono
        "-y",  # Overwrite
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False

def transcribe_audio(audio_path: str, language: str = "auto") -> str:
    """Transcribe audio using Whisper.cpp."""
    if not os.path.exists(WHISPER_CPP_PATH):
        print(f"[WARNING] Whisper binary not found at {WHISPER_CPP_PATH}")
        return ""

    if not os.path.exists(WHISPER_MODEL_PATH):
        print(f"[WARNING] Whisper model not found at {WHISPER_MODEL_PATH}")
        return ""

    # Build command
    cmd = [
        WHISPER_CPP_PATH,
        "-m", WHISPER_MODEL_PATH,
        "-f", audio_path,
        "-nt"  # No timestamps in output
    ]

    if language != "auto":
        cmd.extend(["-l", language])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True
        )

        transcript = result.stdout.strip()
        return transcript

    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Whisper error: {e.stderr if e.stderr else 'unknown'}")
        return ""
    except Exception as e:
        print(f"[WARNING] Transcription error: {str(e)}")
        return ""

# ============================================================================
# Frame Extraction and OCR Functions
# ============================================================================

def extract_frames(video_path: str, num_frames: int = 5, output_dir: str = None) -> List[str]:
    """Extract frames from video at evenly distributed intervals."""
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Get video duration
    cmd_duration = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]

    try:
        result = subprocess.run(cmd_duration, capture_output=True, text=True, timeout=10)
        duration = float(result.stdout.strip())
    except Exception:
        duration = 30.0

    # Extract frames at evenly distributed timestamps
    frame_files = []
    interval = max(1.0, duration / (num_frames + 1))

    for i in range(num_frames):
        timestamp = interval * (i + 1)
        frame_file = output_dir / f"frame_{i+1:03d}.jpg"

        cmd = [
            "ffmpeg", "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",
            str(frame_file)
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            if frame_file.exists():
                frame_files.append(str(frame_file))
        except Exception:
            continue

    return frame_files

def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using Tesseract OCR."""
    try:
        import pytesseract
        from PIL import Image

        # Open image
        img = Image.open(image_path)

        # Run OCR with Arabic and English
        text = pytesseract.image_to_string(img, lang='ara+eng')

        return text.strip()
    except ImportError as e:
        # Only print warning once
        if not hasattr(extract_text_from_image, '_warned'):
            print(f"[WARNING] pytesseract not installed: pip install pytesseract pillow")
            extract_text_from_image._warned = True
        return ""
    except Exception as e:
        # Silently skip errors for individual frames
        return ""

# ============================================================================
# Classification Functions
# ============================================================================

def classify_content(transcript: str, ocr_text: str) -> Dict:
    """Classify video content using local LLM."""
    import requests

    # Build prompt
    system_prompt = f"""You are analyzing field journalist reports documenting events in Gaza. Your task is to INTERPRET what is being documented, not just describe what the journalist said.

**CRITICAL INSTRUCTIONS:**
- INTERPRET what's happening based on the journalist's reporting
- Make EDUCATED INFERENCES about the situation being documented
- READ BETWEEN THE LINES: what is the journalist witnessing and why are they reporting it?
- When MULTIPLE categories could apply, choose the PRIMARY/MOST SPECIFIC one

**INFORMATION SOURCES:**
1. **AUDIO TRANSCRIPT**: Journalist's narration (often in Arabic)
2. **ON-SCREEN TEXT (OCR)**: Text overlays, casualty numbers, locations, timestamps

**CATEGORY DEFINITIONS & PRIORITY RULES:**

"Willful Killing" - PRIMARY if: deaths, casualties, bodies, funerals, martyrs
"Starvation of Civilian" - PRIMARY if: food shortage, hunger, malnutrition, aid blockade
"Destruction of Property" - PRIMARY if: bombed buildings, rubble, structural damage (NOT if also showing deaths → use Willful Killing)
"Displacement" - PRIMARY if: tent camps, temporary shelter, evacuated families (NOT if also showing destruction → use Destruction)
"Inhumane Acts" - Use if: torture, degrading treatment, severe suffering (NOT covered by other categories)
"IDF" - Use if: Israeli forces, soldiers, military operations are PRIMARY focus
"Resilience" - Use if: survival, hope, community strength (NOT if suffering dominates)
"Imprisonment" - Use if: detention, prisoners, captivity
"Testimonials" - Use if: survivor accounts, witness statements are PRIMARY format
"Jewish Dissent" - Use if: Israeli/Jewish opposition to actions

**DECISION RULES (when multiple apply):**
1. Deaths/casualties → ALWAYS "Willful Killing" (even if destruction/displacement shown)
2. Food/hunger focus → "Starvation of Civilian" (even if also displaced)
3. Building damage without deaths → "Destruction of Property"
4. Tent camps without destruction shown → "Displacement"
5. When truly ambiguous → choose MOST SPECIFIC category

**CATEGORIES:**
{json.dumps(CATEGORIES, indent=2)}

**TAGS** (choose ALL that apply):
{json.dumps(TAGS, indent=2)}

**EXAMPLES:**
- Video shows bodies + destroyed buildings → "Willful Killing" (deaths take priority)
- Video shows tents + families with no food → "Starvation of Civilian" (hunger is primary)
- Video shows bombed buildings, no casualties mentioned → "Destruction of Property"
- Video shows families in tents, cold weather → "Displacement"

Provide your response in this EXACT JSON format:
{{
  "category": "chosen category name",
  "tags": ["tag1", "tag2", ...],
  "confidence": "high|medium|low",
  "reasoning": "What is being documented and why it indicates this category. Focus on the SITUATION, not the transcript."
}}
"""

    # Build content
    content_sections = []
    content_sections.append("=" * 80)
    content_sections.append("CONTENT ANALYSIS")
    content_sections.append("=" * 80)

    content_sections.append("\n1. AUDIO TRANSCRIPT:")
    content_sections.append("-" * 80)
    if transcript and transcript.strip():
        content_sections.append(transcript)
    else:
        content_sections.append("[No audio transcription available]")

    content_sections.append("\n2. ON-SCREEN TEXT (OCR):")
    content_sections.append("-" * 80)
    if ocr_text and ocr_text.strip():
        content_sections.append(ocr_text)
    else:
        content_sections.append("[No on-screen text detected]")

    content_sections.append("\n" + "=" * 80)
    content_sections.append("Provide classification based on the above content:")
    content_sections.append("=" * 80)

    user_prompt = "\n".join(content_sections)

    # Call LLM
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": LOCAL_LLM_MODEL,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")

            # Strip markdown code blocks if present (LLM often wraps JSON in ```json ... ```)
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # Remove ```

            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```

            cleaned_response = cleaned_response.strip()

            try:
                classification = json.loads(cleaned_response)
                return classification
            except json.JSONDecodeError as e:
                print(f"\n[ERROR] JSON Parse Error: {str(e)}")
                print(f"Raw response ({len(response_text)} chars):")
                print(response_text[:500])
                return {
                    "category": "Unknown",
                    "tags": [],
                    "confidence": "low",
                    "reasoning": "Failed to parse LLM response"
                }
        else:
            return {
                "category": "Unknown",
                "tags": [],
                "confidence": "low",
                "reasoning": f"LLM API error: {response.status_code}"
            }

    except Exception as e:
        return {
            "category": "Unknown",
            "tags": [],
            "confidence": "low",
            "reasoning": f"Error: {str(e)}"
        }

# ============================================================================
# Main Processing Function
# ============================================================================

def process_tweet(url: str, language: str = "auto", keep_video: bool = False, output_dir: str = ".") -> Optional[Dict]:
    """
    Complete pipeline: download → classify → save.

    Args:
        url: Twitter URL
        language: Whisper language ('auto', 'ar', 'en')
        keep_video: Whether to keep video file after classification
        output_dir: Directory for output files

    Returns:
        Classification result dictionary
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Step 1: Download video
    download_info = download_from_twitter(url, str(output_dir))
    if not download_info:
        return None

    video_path = download_info["video_file"]
    tweet_id = download_info["tweet_id"]

    print(f"\nClassifying video...")

    # Step 2: Extract and transcribe audio
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "audio.wav"

        print("  Extracting audio...")
        audio_success = extract_audio(video_path, str(audio_path))

        if audio_success:
            print(f"  Transcribing audio (language: {language})...")
            transcript = transcribe_audio(str(audio_path), language)
            print(f"  [+] Transcription: {len(transcript)} characters")
        else:
            print("  [WARNING] Audio extraction failed")
            transcript = ""

        # Step 3: Extract frames and run OCR
        print("  Extracting frames for OCR...")
        frame_files = extract_frames(video_path, num_frames=5, output_dir=temp_dir)
        print(f"  [+] Extracted {len(frame_files)} frames")

        ocr_texts = []
        if frame_files:
            print("  Running OCR on frames...")
            for i, frame_file in enumerate(frame_files, 1):
                text = extract_text_from_image(frame_file)
                if text:
                    ocr_texts.append(f"Frame {i}: {text}")
                    print(f"      Frame {i}: {len(text)} chars")

        ocr_text = "\n\n".join(ocr_texts) if ocr_texts else ""
        print(f"  [+] OCR complete: {len(ocr_text)} total characters")

        # Step 4: Classify
        print("\n  Running classification...")
        classification = classify_content(transcript, ocr_text)

        print(f"  [+] Classification complete:")
        print(f"      Category: {classification.get('category')}")
        print(f"      Tags: {', '.join(classification.get('tags', []))}")
        print(f"      Confidence: {classification.get('confidence')}")

    # Build result
    result = {
        **download_info,
        "language": language,
        "transcript": transcript,
        "transcript_length": len(transcript),
        "ocr_text": ocr_text,
        "ocr_length": len(ocr_text),
        "category": classification.get("category"),
        "tags": classification.get("tags", []),
        "confidence": classification.get("confidence"),
        "reasoning": classification.get("reasoning")
    }

    # Save JSON
    output_file = output_dir / f"tweet_{tweet_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved: {output_file}")

    # Optionally delete video
    if not keep_video:
        try:
            os.remove(video_path)
            print(f"Video deleted (use --keep-video to preserve)")
        except Exception:
            pass
    else:
        print(f"Video saved: {video_path}")

    return result

# ============================================================================
# Batch Processing
# ============================================================================

def process_batch(urls_file: str, output_dir: str = "results", language: str = "auto", keep_video: bool = False):
    """Process multiple URLs from a file."""
    urls_file = Path(urls_file)

    if not urls_file.exists():
        print(f"[ERROR] File not found: {urls_file}")
        return

    # Read URLs
    with open(urls_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]

    if not urls:
        print(f"[ERROR] No valid URLs found in {urls_file}")
        return

    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING: {len(urls)} URLs")
    print(f"{'='*80}\n")

    results = {"successful": [], "failed": []}

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        print("-" * 80)

        result = process_tweet(url, language, keep_video, output_dir)

        if result:
            results["successful"].append(url)
            print(f"✅ Success")
        else:
            results["failed"].append(url)
            print(f"❌ Failed")

    # Print summary
    print(f"\n{'='*80}")
    print(f"📊 BATCH SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successful: {len(results['successful'])}/{len(urls)}")
    print(f"❌ Failed: {len(results['failed'])}/{len(urls)}")

    if results["failed"]:
        print(f"\nFailed URLs:")
        for url in results["failed"]:
            print(f"  - {url}")

    print(f"\n📁 Output directory: {output_dir}")

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Download and classify Twitter videos in one command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single tweet
  python3 classify_from_twitter.py "https://twitter.com/user/status/123456"

  # Keep video file
  python3 classify_from_twitter.py "URL" --keep-video

  # Specify language
  python3 classify_from_twitter.py "URL" --language ar

  # Batch process from file
  python3 classify_from_twitter.py --urls urls.txt --output results/
        """
    )

    # Single URL or batch mode
    parser.add_argument("url", nargs="?", help="Twitter URL to process")
    parser.add_argument("--urls", help="File containing list of URLs (one per line)")

    # Options
    parser.add_argument("--language", default="auto", choices=["auto", "ar", "en"],
                       help="Transcription language (default: auto)")
    parser.add_argument("--keep-video", action="store_true",
                       help="Keep video file after classification")
    parser.add_argument("--output", default=".",
                       help="Output directory for results (default: current directory)")

    args = parser.parse_args()

    # Validate input
    if not args.url and not args.urls:
        parser.print_help()
        sys.exit(1)

    # Batch or single mode
    if args.urls:
        process_batch(args.urls, args.output, args.language, args.keep_video)
    else:
        result = process_tweet(args.url, args.language, args.keep_video, args.output)
        if not result:
            sys.exit(1)

if __name__ == "__main__":
    main()
