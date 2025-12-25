#!/usr/bin/env python3
"""
Validate classifier against human-labeled data from Excel spreadsheet.
"""

import json
import subprocess
import pandas as pd
from pathlib import Path
import tempfile
import re

# Import classification functions
from classify_from_twitter import (
    extract_audio, transcribe_audio, extract_frames,
    extract_text_from_image, classify_content
)

def download_video(url: str, output_path: str) -> bool:
    """Download video using yt-dlp (supports Instagram, Twitter, YouTube, Facebook)."""
    cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", output_path, url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and Path(output_path).exists()
    except Exception as e:
        print(f"    [ERROR] {str(e)}")
        return False

def classify_video(video_path: str, language: str = "ar") -> dict:
    """Run classification pipeline on video."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract audio and transcribe
        audio_path = Path(temp_dir) / "audio.wav"
        transcript = ""

        if extract_audio(video_path, str(audio_path)):
            transcript = transcribe_audio(str(audio_path), language)

        # Extract frames and OCR
        frame_files = extract_frames(video_path, num_frames=5, output_dir=temp_dir)
        ocr_texts = []
        for frame_file in frame_files:
            text = extract_text_from_image(frame_file)
            if text:
                ocr_texts.append(text)
        ocr_text = "\n\n".join(ocr_texts)

        # Classify
        classification = classify_content(transcript, ocr_text)

        return {
            "transcript_length": len(transcript),
            "ocr_length": len(ocr_text),
            "category": classification.get("category"),
            "tags": classification.get("tags", []),
            "confidence": classification.get("confidence"),
            "reasoning": classification.get("reasoning")
        }

def normalize_category(cat: str) -> str:
    """Normalize category for comparison."""
    if pd.isna(cat):
        return "Unknown"
    cat = str(cat).strip()
    # Fix typo: Wilful -> Willful
    if cat == "Wilful Killing":
        cat = "Willful Killing"
    return cat

def normalize_tags(tags) -> list:
    """Normalize tags for comparison."""
    if pd.isna(tags):
        return []
    if isinstance(tags, str):
        tags = re.split(r'[,;]', tags)
    return [t.strip() for t in tags if t.strip()]

def main():
    print("=" * 80)
    print("CLASSIFIER VALIDATION")
    print("=" * 80)

    # Read Excel file
    df = pd.read_excel('Gaza Archive Form (Responses)-6.xlsx')
    print(f"\nTotal entries: {len(df)}")

    # Filter out "Other" sources (keep Instagram, Twitter, YouTube, Facebook)
    df['source_type'] = df['Source Link/URL'].apply(
        lambda x: 'instagram' if 'instagram' in str(x).lower()
        else ('twitter' if 'twitter' in str(x).lower() or 'x.com' in str(x).lower()
        else ('youtube' if 'youtube' in str(x).lower() or 'youtu.be' in str(x).lower()
        else ('facebook' if 'facebook' in str(x).lower() or 'fb.watch' in str(x).lower()
        else 'other')))
    )

    processable = df[df['source_type'] != 'other']
    print(f"Processable: {len(processable)} videos")
    print(f"  Instagram: {(df['source_type']=='instagram').sum()}")
    print(f"  Twitter: {(df['source_type']=='twitter').sum()}")
    print(f"  YouTube: {(df['source_type']=='youtube').sum()}")
    print(f"  Facebook: {(df['source_type']=='facebook').sum()}")

    # Sample size
    sample_size = int(input(f"\nHow many videos to validate? (recommended: 10-20): ") or "10")
    sample_size = min(sample_size, len(processable))

    # Sample videos
    sample = processable.sample(n=sample_size, random_state=42)

    print(f"\nProcessing {sample_size} videos...")
    print("=" * 80)

    # Create output directory
    output_dir = Path("validation_videos")
    output_dir.mkdir(exist_ok=True)

    results = []

    for idx, (i, row) in enumerate(sample.iterrows(), 1):
        url = row['Source Link/URL']
        human_category = normalize_category(row['Category'])
        human_tags = normalize_tags(row['Tags (optional)'])
        source_type = row['source_type']

        print(f"\n[{idx}/{sample_size}] {source_type.upper()}")
        print(f"  URL: {url[:70]}...")
        print(f"  Human: {human_category} | Tags: {', '.join(human_tags) if human_tags else 'None'}")

        # Download
        video_path = output_dir / f"video_{i}.mp4"
        print(f"  Downloading...")

        if download_video(url, str(video_path)):
            print(f"  [+] Downloaded ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

            # Classify
            print(f"  Classifying...")
            try:
                classification = classify_video(str(video_path))
                auto_category = classification['category']
                auto_tags = classification['tags']

                # Compare
                category_match = auto_category == human_category
                tag_overlap = len(set(auto_tags) & set(human_tags))

                print(f"  [+] Automated: {auto_category} | Tags: {', '.join(auto_tags) if auto_tags else 'None'}")
                print(f"  Category: {'✓ MATCH' if category_match else '✗ MISMATCH'} | Confidence: {classification['confidence']}")

                results.append({
                    "url": url,
                    "source": source_type,
                    "video_file": str(video_path),
                    "human_category": human_category,
                    "human_tags": human_tags,
                    "automated_category": auto_category,
                    "automated_tags": auto_tags,
                    "category_match": category_match,
                    "tag_overlap": tag_overlap,
                    "confidence": classification['confidence'],
                    "transcript_length": classification['transcript_length'],
                    "ocr_length": classification['ocr_length'],
                    "reasoning": classification['reasoning']
                })

            except Exception as e:
                print(f"  [ERROR] Classification failed: {str(e)}")
                results.append({
                    "url": url,
                    "source": source_type,
                    "error": str(e),
                    "human_category": human_category,
                    "human_tags": human_tags
                })
        else:
            print(f"  [ERROR] Download failed")
            results.append({
                "url": url,
                "source": source_type,
                "error": "Download failed",
                "human_category": human_category,
                "human_tags": human_tags
            })

    # Generate report
    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)

    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    print(f"\nTotal processed: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        # Category accuracy
        category_matches = sum(1 for r in successful if r['category_match'])
        accuracy = 100 * category_matches / len(successful)

        print(f"\nCategory Accuracy: {category_matches}/{len(successful)} ({accuracy:.1f}%)")

        # By source
        print(f"\nBy source:")
        for source in ['instagram', 'twitter', 'youtube', 'facebook']:
            source_results = [r for r in successful if r['source'] == source]
            if source_results:
                source_matches = sum(1 for r in source_results if r['category_match'])
                print(f"  {source.capitalize()}: {source_matches}/{len(source_results)} ({100*source_matches/len(source_results):.1f}%)")

        # Confidence distribution
        print(f"\nConfidence distribution:")
        for conf in ["high", "medium", "low"]:
            count = sum(1 for r in successful if r.get('confidence') == conf)
            print(f"  {conf.capitalize()}: {count} ({100*count/len(successful):.1f}%)")

        # Mismatches
        mismatches = [r for r in successful if not r['category_match']]
        if mismatches:
            print(f"\nMismatches ({len(mismatches)}):")
            for r in mismatches[:5]:  # Show first 5
                print(f"  Human: {r['human_category']} → Automated: {r['automated_category']}")

    # Save results
    output_file = "validation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved: {output_file}")
    print(f"Videos saved: {output_dir}/")

if __name__ == "__main__":
    main()
