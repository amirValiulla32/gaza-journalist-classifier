#!/usr/bin/env python3
"""
Extract on-screen text from video frames using OCR.
Useful for detecting journalist names in reposted videos.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import json

# OCR library - install with: pip install pytesseract pillow
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_frames(video_path: str, num_frames: int = 5, output_dir: str = None) -> list:
    """
    Extract frames from video at different timestamps.

    Args:
        video_path: Path to video file
        num_frames: Number of frames to extract (default: 3 - start, middle, end)
        output_dir: Directory to save frames (default: temp directory)

    Returns:
        list of frame file paths
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get video duration first
    try:
        result = subprocess.run([
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path
        ], capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
    except Exception as e:
        print(f"⚠️ Could not get video duration: {e}")
        duration = 10.0  # Default fallback

    # Calculate timestamps to extract frames
    timestamps = []
    if num_frames == 1:
        timestamps = [1.0]  # First second
    elif num_frames == 2:
        timestamps = [1.0, duration - 1.0]
    else:
        # Distribute frames evenly (start, middle, end)
        for i in range(num_frames):
            t = max(1.0, (duration / (num_frames + 1)) * (i + 1))
            timestamps.append(min(t, duration - 1.0))

    frame_files = []

    for i, timestamp in enumerate(timestamps):
        output_file = output_path / f"frame_{i:03d}.jpg"

        try:
            # Extract frame at timestamp using ffmpeg
            subprocess.run([
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "2",  # High quality
                "-y",
                str(output_file)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            frame_files.append(str(output_file))

        except subprocess.CalledProcessError as e:
            print(f"⚠️ Could not extract frame at {timestamp}s: {e}")

    return frame_files


def extract_text_from_image(image_path: str, languages: str = "ara+eng") -> str:
    """
    Extract text from image using OCR.

    Args:
        image_path: Path to image file
        languages: OCR languages (default: "ara+eng" for Arabic + English)

    Returns:
        str with extracted text
    """
    if not OCR_AVAILABLE:
        return ""

    try:
        # Load image
        img = Image.open(image_path)

        # Perform OCR with Arabic first (primary language)
        text = pytesseract.image_to_string(img, lang=languages)

        return text.strip()

    except Exception as e:
        print(f"⚠️ OCR error on {image_path}: {e}")
        return ""


def extract_text_from_video(video_path: str, num_frames: int = 5) -> dict:
    """
    Extract text from video frames.

    Args:
        video_path: Path to video file
        num_frames: Number of frames to analyze

    Returns:
        dict with extracted text and metadata
    """
    video_path = Path(video_path).resolve()

    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return None

    if not OCR_AVAILABLE:
        print("❌ OCR not available. Install with:")
        print("   pip install pytesseract pillow")
        print("   brew install tesseract")
        print("   brew install tesseract-lang  # For Arabic support")
        return None

    print(f"\n{'='*60}")
    print(f"Extracting text from: {video_path.name}")
    print(f"{'='*60}\n")

    # Create temp directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📹 Extracting {num_frames} frames...")

        # Extract frames
        frame_files = extract_frames(str(video_path), num_frames, temp_dir)

        if not frame_files:
            print("❌ No frames extracted")
            return None

        print(f"✅ Extracted {len(frame_files)} frames")

        # Extract text from each frame
        all_text = []
        frame_results = []

        for i, frame_file in enumerate(frame_files):
            print(f"\n🔍 Analyzing frame {i+1}/{len(frame_files)}...")

            text = extract_text_from_image(frame_file)

            if text:
                print(f"✅ Found text ({len(text)} characters)")
                all_text.append(text)
                frame_results.append({
                    "frame": i,
                    "text": text,
                    "length": len(text)
                })
            else:
                print(f"⚠️ No text detected")

        # Combine all text
        combined_text = "\n\n".join(all_text)

        print(f"\n{'='*60}")
        print(f"TEXT EXTRACTION SUMMARY")
        print(f"{'='*60}\n")
        print(f"📊 Frames analyzed: {len(frame_files)}")
        print(f"✅ Frames with text: {len(frame_results)}")
        print(f"📝 Total characters: {len(combined_text)}")

        if combined_text:
            print(f"\n📄 Extracted text preview:")
            print(f"{'-'*60}")
            print(combined_text[:500])
            if len(combined_text) > 500:
                print(f"\n... ({len(combined_text) - 500} more characters)")
            print(f"{'-'*60}")

        return {
            "video_file": str(video_path),
            "video_name": video_path.name,
            "frames_analyzed": len(frame_files),
            "frames_with_text": len(frame_results),
            "combined_text": combined_text,
            "frame_results": frame_results
        }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_text_from_video.py <video_file> [num_frames]")
        print("\nExample: python extract_text_from_video.py video.mp4")
        print("         python extract_text_from_video.py video.mp4 5")
        print("\nWhat it does:")
        print("  - Extracts frames from video at different timestamps")
        print("  - Uses OCR to read text from frames")
        print("  - Useful for detecting journalist names in reposted videos")
        print("\nRequirements:")
        print("  - ffmpeg: brew install ffmpeg")
        print("  - tesseract: brew install tesseract tesseract-lang")
        print("  - Python packages: pip install pytesseract pillow")
        sys.exit(1)

    video_path = sys.argv[1]
    num_frames = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    result = extract_text_from_video(video_path, num_frames)

    if result:
        # Save to JSON
        output_file = Path(video_path).stem + "_ocr.json"
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_file}\n")
    else:
        print("\n❌ Text extraction failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
