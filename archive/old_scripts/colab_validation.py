#!/usr/bin/env python3
"""
Multimodal Video Classifier Validation Script for Google Colab
Processes videos with Audio + Vision + OCR analysis
"""

import json
import subprocess
import pandas as pd
from pathlib import Path
import tempfile
import time
import re
from typing import Optional, Dict, List
import os
import requests

# ============================================================================
# Configuration
# ============================================================================

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
    "Birth Prevention", "Call to Action", "Ceasefire Violation", "Children",
    "Ethnic Cleansing", "Food", "Healthcare workers", "Hospitals", "IDF",
    "Journalists", "Media and Journalism", "Other", "Repression",
    "Schools", "Torture", "Water", "Women"
]

# Colab paths
WHISPER_CPP_PATH = "./whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL_PATH = "./whisper.cpp/models/ggml-base.bin"
LLAVA_MODEL = "llava-llama-3:8b"
LLM_MODEL = "qwen2.5:72b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# ============================================================================
# Helper Functions
# ============================================================================

def download_video(url: str, output_path: str) -> bool:
    """Download video using yt-dlp."""
    cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", output_path, url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and Path(output_path).exists()
    except Exception:
        return False

def extract_audio(video_path: str, audio_path: str) -> bool:
    """Extract audio from video."""
    cmd = [
        "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", "-y", audio_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False

def transcribe_audio(audio_path: str, language: str = "ar") -> str:
    """Transcribe audio using Whisper."""
    if not os.path.exists(WHISPER_CPP_PATH):
        return ""

    cmd = [WHISPER_CPP_PATH, "-m", WHISPER_MODEL_PATH, "-f", audio_path, "-nt"]
    if language != "auto":
        cmd.extend(["-l", language])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
        return result.stdout.strip()
    except Exception:
        return ""

def extract_frames(video_path: str, num_frames: int = 5) -> List[str]:
    """Extract frames from video."""
    temp_dir = tempfile.mkdtemp()

    # Get duration
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        duration = float(result.stdout.strip())
    except Exception:
        duration = 30.0

    # Extract frames
    frame_files = []
    interval = max(1.0, duration / (num_frames + 1))

    for i in range(num_frames):
        timestamp = interval * (i + 1)
        frame_file = Path(temp_dir) / f"frame_{i+1:03d}.jpg"
        cmd = ["ffmpeg", "-ss", str(timestamp), "-i", video_path,
               "-frames:v", "1", "-q:v", "2", "-y", str(frame_file)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            if frame_file.exists():
                frame_files.append(str(frame_file))
        except Exception:
            continue

    return frame_files

def extract_text_from_image(image_path: str) -> str:
    """OCR on image."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='ara+eng')
        return text.strip()
    except Exception:
        return ""

def analyze_frame_with_vision(image_path: str, context: str = "") -> str:
    """Analyze frame with LLaVA."""
    import base64

    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""Analyze this frame from a Gaza journalist report.

Audio context: {context[:500] if context else "No audio"}

Describe what you see:
- People: Who? (children, women, injured, medical staff, etc.)
- Setting: Where? (hospital, tent, destroyed building, etc.)
- Situation: What's happening?
- Evidence: Specific visual indicators?

Be factual and specific."""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": LLAVA_MODEL, "prompt": prompt, "images": [image_data], "stream": False},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("response", "")
    except Exception:
        pass
    return ""

def classify_multimodal(transcript: str, ocr_text: str, vision_analyses: List[str]) -> Dict:
    """Classify with all modalities."""

    system_prompt = f"""Analyze Gaza journalist reports using audio, text, and vision.

**CATEGORY DEFINITIONS:**
- "Willful Killing": Deaths, casualties, bodies, funerals
- "Starvation of Civilian": Food shortage, hunger, malnutrition
- "Destruction of Property": Bombed buildings, rubble (without deaths)
- "Displacement": Tent camps, temporary shelter, evacuated families
- "Inhumane Acts": Torture, degrading treatment
- "IDF": Israeli forces as primary focus
- "Resilience": Survival, hope despite suffering
- "Imprisonment": Detention, prisoners
- "Testimonials": Witness statements as primary format
- "Jewish Dissent": Israeli/Jewish opposition

**PRIORITY**: Deaths → Starvation → Destruction → Displacement

**CATEGORIES**: {json.dumps(CATEGORIES, indent=2)}
**TAGS**: {json.dumps(TAGS, indent=2)}

Respond in JSON:
{{
  "category": "name",
  "tags": ["tag1", "tag2"],
  "confidence": "high|medium|low",
  "reasoning": "Explain using all sources"
}}"""

    content = f"""{'='*80}
MULTIMODAL ANALYSIS
{'='*80}

1. AUDIO TRANSCRIPT:
{'-'*80}
{transcript or '[No audio]'}

2. ON-SCREEN TEXT (OCR):
{'-'*80}
{ocr_text or '[No text]'}

3. VISION ANALYSIS:
{'-'*80}
{chr(10).join(f'Frame {i+1}: {v}' for i, v in enumerate(vision_analyses)) if vision_analyses else '[No vision]'}

{'='*80}
Classify:
"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": LLM_MODEL,
                "prompt": f"{system_prompt}\n\n{content}",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "top_p": 0.9}
            },
            timeout=180
        )

        if response.status_code == 200:
            response_text = response.json().get("response", "")

            # Strip markdown
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
    except Exception as e:
        return {
            "category": "Unknown",
            "tags": [],
            "confidence": "low",
            "reasoning": f"Error: {str(e)}"
        }

    return {"category": "Unknown", "tags": [], "confidence": "low", "reasoning": "API error"}

def process_video_multimodal(video_path: str, language: str = "ar") -> Dict:
    """Full multimodal pipeline."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Audio transcription
        audio_path = Path(temp_dir) / "audio.wav"
        transcript = ""
        if extract_audio(video_path, str(audio_path)):
            transcript = transcribe_audio(str(audio_path), language)

        # Extract frames
        frame_files = extract_frames(video_path, num_frames=5)

        # OCR
        ocr_texts = []
        for frame_file in frame_files:
            text = extract_text_from_image(frame_file)
            if text:
                ocr_texts.append(text)
        ocr_text = "\n\n".join(ocr_texts)

        # Vision analysis (first 3 frames)
        vision_analyses = []
        for frame_file in frame_files[:3]:
            analysis = analyze_frame_with_vision(frame_file, transcript[:500])
            if analysis:
                vision_analyses.append(analysis)

        # Classify
        classification = classify_multimodal(transcript, ocr_text, vision_analyses)

        return {
            "transcript_length": len(transcript),
            "ocr_length": len(ocr_text),
            "vision_frames_analyzed": len(vision_analyses),
            **classification
        }

def normalize_category(cat: str) -> str:
    """Normalize category."""
    if pd.isna(cat):
        return "Unknown"
    cat = str(cat).strip()
    if cat == "Wilful Killing":
        cat = "Willful Killing"
    return cat

def normalize_tags(tags) -> list:
    """Normalize tags."""
    if pd.isna(tags):
        return []
    if isinstance(tags, str):
        tags = re.split(r'[,;]', tags)
    return [t.strip() for t in tags if t.strip()]

def run_validation(excel_file: str, sample_size: int = 30, output_dir: str = "validation_output"):
    """Main validation function."""

    print("Multimodal Classifier Validation\n")

    # Read Excel
    df = pd.read_excel(excel_file)
    print(f"Total entries: {len(df)}")

    # Filter processable
    df['source_type'] = df['Source Link/URL'].apply(
        lambda x: 'instagram' if 'instagram' in str(x).lower()
        else ('twitter' if 'twitter' in str(x).lower() or 'x.com' in str(x).lower()
        else ('youtube' if 'youtube' in str(x).lower()
        else ('facebook' if 'facebook' in str(x).lower()
        else 'other')))
    )

    processable = df[df['source_type'] != 'other']
    print(f"Processable: {len(processable)} videos\n")

    # Sample
    sample = processable.sample(n=min(sample_size, len(processable)), random_state=42)

    # Setup output
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    videos_path = output_path / "videos"
    videos_path.mkdir(exist_ok=True)

    results = []

    for idx, (i, row) in enumerate(sample.iterrows(), 1):
        url = row['Source Link/URL']
        human_category = normalize_category(row['Category'])
        human_tags = normalize_tags(row['Tags (optional)'])
        source = row['source_type']

        print(f"\n[{idx}/{len(sample)}] {source.upper()}")
        print(f"  Human: {human_category}")

        # Download
        video_path = videos_path / f"video_{i}.mp4"
        if download_video(url, str(video_path)):
            print(f"  [+] Downloaded")

            # Process
            try:
                start = time.time()
                classification = process_video_multimodal(str(video_path))
                elapsed = time.time() - start

                auto_category = classification['category']
                match = auto_category == human_category

                print(f"  [+] Auto: {auto_category} ({classification['confidence']})")
                print(f"  {'✓ MATCH' if match else '✗ MISMATCH'} | {elapsed:.1f}s")

                results.append({
                    "url": url,
                    "source": source,
                    "human_category": human_category,
                    "human_tags": human_tags,
                    "automated_category": auto_category,
                    "automated_tags": classification['tags'],
                    "category_match": match,
                    "confidence": classification['confidence'],
                    "processing_time": elapsed,
                    **classification
                })
            except Exception as e:
                print(f"  [ERROR] {str(e)}")
                results.append({"url": url, "source": source, "error": str(e), "human_category": human_category})
        else:
            print(f"  [ERROR] Download failed")
            results.append({"url": url, "source": source, "error": "Download failed", "human_category": human_category})

    # Report
    print("\n" + "="*80)
    print("VALIDATION REPORT")
    print("="*80)

    successful = [r for r in results if "error" not in r]
    matches = sum(1 for r in successful if r.get("category_match", False))

    print(f"\nProcessed: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(results) - len(successful)}")

    if successful:
        accuracy = 100 * matches / len(successful)
        print(f"\nCategory Accuracy: {matches}/{len(successful)} ({accuracy:.1f}%)")

        avg_time = sum(r.get("processing_time", 0) for r in successful) / len(successful)
        print(f"Avg processing time: {avg_time:.1f}s/video")

        print(f"\nConfidence:")
        for conf in ["high", "medium", "low"]:
            count = sum(1 for r in successful if r.get('confidence') == conf)
            print(f"  {conf.capitalize()}: {count} ({100*count/len(successful):.1f}%)")

    # Save
    output_file = output_path / "validation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults: {output_file}")

    return results
