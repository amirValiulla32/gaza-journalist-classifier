#!/usr/bin/env python3
"""
Multimodal Video Classifier - Combines Audio + OCR + Vision for comprehensive classification.

This enhanced classifier uses three sources of information:
1. Audio transcription (what the journalist says)
2. OCR text extraction (on-screen text, names, locations, statistics)
3. Vision analysis (what's visually shown in frames)

All three sources are combined and sent to LLM for accurate classification.
"""

import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

# Import our existing modules
from classify_video import extract_audio, transcribe_audio, LOCAL_LLM_MODEL, CATEGORIES, TAGS
from extract_text_from_video import extract_frames, extract_text_from_image, OCR_AVAILABLE
from analyze_frame_content import analyze_frames_batch

# Enhanced classification prompt for multimodal analysis
def build_multimodal_prompt(transcript: str, ocr_text: str, vision_descriptions: str) -> str:
    """
    Build enhanced LLM prompt with all three information sources.

    Args:
        transcript: Audio transcription
        ocr_text: Text extracted from frames (OCR)
        vision_descriptions: Visual descriptions from frame analysis

    Returns:
        Complete system + user prompt for LLM
    """
    system_prompt = f"""You are analyzing journalist reports about Gaza to classify them into categories and tags.

You have THREE sources of information available:

1. **AUDIO TRANSCRIPT**: What the journalist said in their narration
2. **ON-SCREEN TEXT (OCR)**: Text overlays, journalist names, locations, casualty numbers, organization names
3. **VISUAL CONTENT**: What is actually shown in video frames (buildings, people, activities, conditions)

IMPORTANT: Use ALL THREE sources to make accurate classifications. Visual evidence + audio narration = strongest classification.

**CATEGORIES** (choose exactly ONE most appropriate):
{json.dumps(CATEGORIES, indent=2)}

**TAGS** (choose ALL that apply):
{json.dumps(TAGS, indent=2)}

**CLASSIFICATION GUIDELINES**:
- If audio describes something AND visual frames confirm it → HIGH confidence
- If only audio mentions it (not shown in frames) → MEDIUM confidence
- If only shown in frames (not mentioned in audio) → Still valid, note "visual evidence only"
- If audio and visual contradict → Note the discrepancy, prefer visual evidence
- OCR text is especially useful for: journalist names, locations, statistics, dates, organization names

Provide your response in this EXACT JSON format:
{{
  "category": "chosen category name",
  "tags": ["tag1", "tag2", ...],
  "confidence": "high|medium|low",
  "reasoning": "Explain classification using evidence from all three sources. Format: 'Audio: [what was said]. Visual: [what was shown]. OCR: [text found]. Therefore: [conclusion].'",
  "visual_evidence": ["list of key visual elements that support classification"],
  "discrepancies": "any contradictions between audio and visual (or 'none')"
}}
"""

    # Build content sections
    content_sections = []

    content_sections.append("=" * 80)
    content_sections.append("MULTIMODAL CONTENT ANALYSIS")
    content_sections.append("=" * 80)

    # Audio transcript
    content_sections.append("\n1. AUDIO TRANSCRIPT (what journalist said):")
    content_sections.append("-" * 80)
    if transcript and transcript.strip():
        content_sections.append(transcript)
    else:
        content_sections.append("[No audio transcription available or audio is silent]")

    # OCR text
    content_sections.append("\n2. ON-SCREEN TEXT (text overlays from frames):")
    content_sections.append("-" * 80)
    if ocr_text and ocr_text.strip():
        content_sections.append(ocr_text)
    else:
        content_sections.append("[No on-screen text detected]")

    # Visual descriptions
    content_sections.append("\n3. VISUAL CONTENT (what is shown in frames):")
    content_sections.append("-" * 80)
    if vision_descriptions and vision_descriptions.strip():
        content_sections.append(vision_descriptions)
    else:
        content_sections.append("[No visual analysis available]")

    content_sections.append("\n" + "=" * 80)
    content_sections.append("Based on ALL THREE sources above, provide classification:")
    content_sections.append("=" * 80)

    user_prompt = "\n".join(content_sections)

    return system_prompt, user_prompt


def classify_multimodal_content(
    transcript: str,
    ocr_text: Optional[str] = None,
    vision_descriptions: Optional[str] = None
) -> Dict:
    """
    Classify video using multimodal inputs (audio + OCR + vision).

    Args:
        transcript: Audio transcription
        ocr_text: Text extracted from frames (optional)
        vision_descriptions: Visual frame descriptions (optional)

    Returns:
        Classification result dictionary
    """
    import requests

    print(f"\n🤖 Running multimodal classification with DeepSeek...")

    # Build prompts
    system_prompt, user_prompt = build_multimodal_prompt(transcript, ocr_text or "", vision_descriptions or "")

    # Call local LLM (DeepSeek via Ollama)
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": LOCAL_LLM_MODEL,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=120  # Multimodal analysis can take longer
        )

        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")

            try:
                # Parse JSON response
                classification = json.loads(response_text)
                print(f"✅ Classification complete:")
                print(f"   Category: {classification.get('category')}")
                print(f"   Tags: {', '.join(classification.get('tags', []))}")
                print(f"   Confidence: {classification.get('confidence')}")

                return classification

            except json.JSONDecodeError:
                print(f"⚠️ Could not parse LLM response as JSON")
                return {
                    "category": "Unknown",
                    "tags": [],
                    "confidence": "low",
                    "reasoning": "Failed to parse LLM response",
                    "visual_evidence": [],
                    "discrepancies": "none"
                }
        else:
            print(f"❌ LLM API error: {response.status_code}")
            return {
                "category": "Unknown",
                "tags": [],
                "confidence": "low",
                "reasoning": f"LLM API error: {response.status_code}",
                "visual_evidence": [],
                "discrepancies": "none"
            }

    except Exception as e:
        print(f"❌ Classification error: {str(e)}")
        return {
            "category": "Unknown",
            "tags": [],
            "confidence": "low",
            "reasoning": f"Error: {str(e)}",
            "visual_evidence": [],
            "discrepancies": "none"
        }


def classify_video_multimodal(
    video_path: str,
    language: str = "auto",
    use_ocr: bool = True,
    use_vision: bool = True,
    num_frames: int = 15,
    frame_strategy: str = "sections"
) -> Dict:
    """
    Complete multimodal video classification pipeline.

    Args:
        video_path: Path to video file
        language: Whisper language ('auto', 'ar', 'en')
        use_ocr: Extract on-screen text with OCR
        use_vision: Analyze frame content with vision model
        num_frames: Number of frames to extract (default: 15)
        frame_strategy: Frame sampling strategy ('distributed' or 'sections')

    Returns:
        Complete classification result with all metadata
    """
    video_path = Path(video_path).resolve()

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return None

    print(f"\n{'='*80}")
    print(f"🎬 MULTIMODAL VIDEO CLASSIFICATION")
    print(f"{'='*80}")
    print(f"Video: {video_path.name}")
    print(f"Language: {language}")
    print(f"OCR: {'✅ Enabled' if use_ocr else '❌ Disabled'}")
    print(f"Vision: {'✅ Enabled' if use_vision else '❌ Disabled'}")
    if use_vision:
        print(f"Frames: {num_frames} ({frame_strategy} sampling)")
    print(f"{'='*80}\n")

    # Step 1: Extract and transcribe audio
    print("📍 Step 1/4: Audio Processing")
    print("-" * 80)

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "audio.wav"

        print("🎵 Extracting audio...")
        audio_success = extract_audio(str(video_path), str(audio_path))

        if not audio_success:
            print("⚠️ Audio extraction failed, continuing without audio...")
            transcript = ""
        else:
            print(f"🗣️ Transcribing audio (language: {language})...")
            transcript = transcribe_audio(str(audio_path), language)
            print(f"✅ Transcription complete: {len(transcript)} characters")

        # Step 2: Extract frames (used for both OCR and vision)
        print(f"\n📍 Step 2/4: Frame Extraction")
        print("-" * 80)

        ocr_text = ""
        vision_descriptions = ""

        if use_ocr or use_vision:
            frames_dir = Path(temp_dir) / "frames"
            frames_dir.mkdir(exist_ok=True)

            print(f"📸 Extracting {num_frames} frames ({frame_strategy} strategy)...")
            frame_files = extract_frames(
                str(video_path),
                num_frames=num_frames,
                output_dir=str(frames_dir),
                strategy=frame_strategy
            )

            if not frame_files:
                print("⚠️ No frames extracted")
            else:
                print(f"✅ Extracted {len(frame_files)} frames")

                # Step 3: OCR text extraction
                if use_ocr and OCR_AVAILABLE:
                    print(f"\n📍 Step 3a/4: OCR Text Extraction")
                    print("-" * 80)

                    ocr_texts = []
                    for i, frame_file in enumerate(frame_files, 1):
                        print(f"  Frame {i}/{len(frame_files)}...", end=" ")
                        text = extract_text_from_image(frame_file)
                        if text:
                            print(f"✅ ({len(text)} chars)")
                            ocr_texts.append(f"Frame {i}: {text}")
                        else:
                            print("⚠️ No text")

                    ocr_text = "\n\n".join(ocr_texts)
                    print(f"✅ OCR complete: {len(ocr_text)} total characters")

                # Step 4: Vision analysis
                if use_vision:
                    print(f"\n📍 Step 3b/4: Vision Analysis")
                    print("-" * 80)

                    vision_result = analyze_frames_batch(frame_files, include_timestamps=True)
                    vision_descriptions = vision_result.get('combined_description', '')

                    print(f"✅ Vision analysis complete: {vision_result['successful_frames']}/{vision_result['total_frames']} frames")
        else:
            print("⚠️ Both OCR and vision disabled, skipping frame extraction")

        # Step 5: Multimodal classification
        print(f"\n📍 Step 4/4: Multimodal Classification")
        print("-" * 80)

        classification = classify_multimodal_content(
            transcript=transcript,
            ocr_text=ocr_text if use_ocr else None,
            vision_descriptions=vision_descriptions if use_vision else None
        )

        # Build complete result
        result = {
            "video_file": str(video_path),
            "video_name": video_path.name,
            "language": language,
            "transcript": transcript,
            "transcript_length": len(transcript),
            "ocr_enabled": use_ocr,
            "ocr_text": ocr_text if use_ocr else None,
            "ocr_length": len(ocr_text) if use_ocr else 0,
            "vision_enabled": use_vision,
            "vision_descriptions": vision_descriptions if use_vision else None,
            "vision_length": len(vision_descriptions) if use_vision else 0,
            "num_frames_analyzed": num_frames if (use_ocr or use_vision) else 0,
            "frame_strategy": frame_strategy if (use_ocr or use_vision) else None,
            "category": classification.get("category"),
            "tags": classification.get("tags", []),
            "confidence": classification.get("confidence"),
            "reasoning": classification.get("reasoning"),
            "visual_evidence": classification.get("visual_evidence", []),
            "discrepancies": classification.get("discrepancies", "none")
        }

        return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("""
Multimodal Video Classifier - Audio + OCR + Vision

Usage:
  python3 classify_video_multimodal.py <video_file> [options]

Options:
  --language <ar|en|auto>    Transcription language (default: auto)
  --no-ocr                   Disable OCR text extraction
  --no-vision                Disable vision analysis
  --frames <N>               Number of frames to extract (default: 15)
  --strategy <distributed|sections>  Frame sampling strategy (default: sections)

Examples:
  # Full multimodal analysis (audio + OCR + vision)
  python3 classify_video_multimodal.py video.mp4

  # Arabic-only with vision
  python3 classify_video_multimodal.py video.mp4 --language ar

  # Audio + OCR only (no vision)
  python3 classify_video_multimodal.py video.mp4 --no-vision

  # Vision analysis with more frames
  python3 classify_video_multimodal.py video.mp4 --frames 30

Comparison with classify_video.py:
  - classify_video.py: Audio + OCR only (faster, 45-60s)
  - classify_video_multimodal.py: Audio + OCR + Vision (comprehensive, 90-150s)
""")
        sys.exit(1)

    # Parse arguments
    video_path = sys.argv[1]
    language = "auto"
    use_ocr = True
    use_vision = True
    num_frames = 15
    frame_strategy = "sections"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--language" and i + 1 < len(sys.argv):
            language = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--no-ocr":
            use_ocr = False
            i += 1
        elif sys.argv[i] == "--no-vision":
            use_vision = False
            i += 1
        elif sys.argv[i] == "--frames" and i + 1 < len(sys.argv):
            num_frames = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--strategy" and i + 1 < len(sys.argv):
            frame_strategy = sys.argv[i + 1]
            i += 2
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)

    # Run classification
    result = classify_video_multimodal(
        video_path=video_path,
        language=language,
        use_ocr=use_ocr,
        use_vision=use_vision,
        num_frames=num_frames,
        frame_strategy=frame_strategy
    )

    if result:
        # Print results
        print(f"\n{'='*80}")
        print("CLASSIFICATION RESULTS")
        print(f"{'='*80}\n")

        print(f"📁 Video: {result['video_name']}")
        print(f"📂 Category: {result['category']}")
        print(f"🏷️  Tags: {', '.join(result['tags'])}")
        print(f"📊 Confidence: {result['confidence']}")
        print(f"\n💭 Reasoning:")
        print(f"{result['reasoning']}\n")

        if result.get('visual_evidence'):
            print(f"👁️  Visual Evidence:")
            for evidence in result['visual_evidence']:
                print(f"   - {evidence}")
            print()

        if result.get('discrepancies') and result['discrepancies'] != "none":
            print(f"⚠️  Discrepancies: {result['discrepancies']}\n")

        print(f"📈 Processing Stats:")
        print(f"   Audio: {result['transcript_length']} chars")
        if result['ocr_enabled']:
            print(f"   OCR: {result['ocr_length']} chars")
        if result['vision_enabled']:
            print(f"   Vision: {result['vision_length']} chars ({result['num_frames_analyzed']} frames)")

        # Save to JSON
        output_file = Path(video_path).stem + "_multimodal.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Full results saved to: {output_file}")
        print(f"{'='*80}\n")

    else:
        print("❌ Classification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
