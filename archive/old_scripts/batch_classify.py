#!/usr/bin/env python3
"""
Batch Video Classifier
Processes multiple videos and exports results to CSV.
"""

import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from classify_video import classify_video, extract_audio, transcribe_audio, classify_content

# Optional OCR support
try:
    from extract_text_from_video import extract_text_from_video
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def process_single_video(video_path: Path, language: str = "auto", use_ocr: bool = False) -> dict:
    """
    Process a single video file.

    Args:
        video_path: Path to video file
        language: Language code ('en', 'ar', 'auto')
        use_ocr: Enable OCR text extraction

    Returns:
        dict with classification results
    """
    print(f"\n📹 Processing: {video_path.name}")

    try:
        result = classify_video(str(video_path), language, use_ocr)

        if result:
            print(f"✅ Completed: {result['classification']['category']}")
            return result
        else:
            print(f"❌ Failed: {video_path.name}")
            return None

    except Exception as e:
        print(f"❌ Error processing {video_path.name}: {e}")
        return None


def batch_classify(
    input_dir: str,
    output_csv: str = None,
    language: str = "auto",
    parallel: bool = False,
    max_workers: int = 3,
    use_ocr: bool = False
) -> dict:
    """
    Batch classify all videos in a directory.

    Args:
        input_dir: Directory containing video files
        output_csv: Path to output CSV file (default: classifications.csv)
        language: Language code for transcription
        parallel: Enable parallel processing
        max_workers: Number of parallel workers (default: 3)
        use_ocr: Enable OCR text extraction from video frames

    Returns:
        dict with batch processing results
    """
    input_path = Path(input_dir).resolve()

    if not input_path.exists():
        print(f"❌ Directory not found: {input_path}")
        return {"success": False, "error": "Directory not found"}

    # Find all video files
    video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mkv"))

    if not video_files:
        print(f"❌ No video files found in {input_path}")
        return {"success": False, "error": "No video files found"}

    # Default output CSV
    if output_csv is None:
        output_csv = "classifications.csv"

    print(f"\n{'='*60}")
    print(f"BATCH VIDEO CLASSIFIER")
    print(f"{'='*60}\n")
    print(f"📁 Input directory: {input_path}")
    print(f"📹 Videos found: {len(video_files)}")
    print(f"📊 Output CSV: {output_csv}")
    print(f"🌐 Language: {language}")
    print(f"⚡ Parallel processing: {parallel} ({max_workers} workers)")
    print(f"📸 OCR enabled: {use_ocr}")
    print(f"\n⏳ Starting classification...\n")

    results = []
    successful = 0
    failed = 0

    if parallel and len(video_files) > 1:
        # Parallel processing
        print(f"🚀 Processing {len(video_files)} videos in parallel...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_video = {
                executor.submit(process_single_video, vf, language, use_ocr): vf
                for vf in video_files
            }

            for future in as_completed(future_to_video):
                result = future.result()
                if result:
                    results.append(result)
                    successful += 1
                else:
                    failed += 1
    else:
        # Sequential processing
        for video_file in video_files:
            result = process_single_video(video_file, language, use_ocr)
            if result:
                results.append(result)
                successful += 1
            else:
                failed += 1

    # Export to CSV
    print(f"\n{'='*60}")
    print(f"EXPORTING TO CSV")
    print(f"{'='*60}\n")

    csv_path = Path(output_csv).resolve()

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'video_file',
            'video_name',
            'tweet_url',
            'journalist_handle',
            'download_date',
            'processing_date',
            'language',
            'duration',
            'transcript',
            'ocr_text',
            'category',
            'tags',
            'confidence',
            'reasoning'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Extract metadata from info.json if available
            video_path = Path(result['video_file'])
            info_json = video_path.parent / (video_path.stem + ".info.json")

            tweet_url = ""
            journalist_handle = ""
            download_date = ""

            if info_json.exists():
                try:
                    with open(info_json, 'r') as f:
                        info = json.load(f)
                        tweet_url = info.get('webpage_url', '')
                        journalist_handle = info.get('uploader_id', '')
                        timestamp = info.get('timestamp', '')
                        if timestamp:
                            download_date = datetime.fromtimestamp(timestamp).isoformat()
                except Exception as e:
                    print(f"⚠️ Could not read metadata for {video_path.name}: {e}")

            # Write row
            writer.writerow({
                'video_file': result['video_file'],
                'video_name': result['video_name'],
                'tweet_url': tweet_url,
                'journalist_handle': journalist_handle,
                'download_date': download_date,
                'processing_date': datetime.now().isoformat(),
                'language': result['language'],
                'duration': '',  # Can add from metadata
                'transcript': result['transcript'],
                'ocr_text': result.get('ocr_text', ''),
                'category': result['classification']['category'],
                'tags': ', '.join(result['classification']['tags']),
                'confidence': result['classification']['confidence'],
                'reasoning': result['classification']['reasoning']
            })

    print(f"✅ CSV exported to: {csv_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING SUMMARY")
    print(f"{'='*60}\n")
    print(f"✅ Successfully classified: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total processed: {len(video_files)}")
    print(f"💾 Results saved to: {csv_path}")
    print(f"\n{'='*60}\n")

    return {
        "success": True,
        "total_videos": len(video_files),
        "successful": successful,
        "failed": failed,
        "output_csv": str(csv_path),
        "results": results
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python batch_classify.py <input_dir> [output_csv] [language] [--parallel] [--ocr]")
        print("\nExamples:")
        print("  python batch_classify.py ./downloads/")
        print("  python batch_classify.py ./downloads/ results.csv")
        print("  python batch_classify.py ./downloads/ results.csv ar")
        print("  python batch_classify.py ./downloads/ results.csv auto --parallel")
        print("  python batch_classify.py ./downloads/ results.csv ar --parallel --ocr")
        print("\nArguments:")
        print("  input_dir:   Directory containing video files (.mp4, .mkv)")
        print("  output_csv:  Output CSV file (default: classifications.csv)")
        print("  language:    Language code - en, ar, auto (default: auto)")
        print("  --parallel:  Enable parallel processing (faster for multiple videos)")
        print("  --ocr:       Extract on-screen text for enhanced classification")
        print("\nOutput CSV columns:")
        print("  - video_file, video_name, tweet_url, journalist_handle")
        print("  - download_date, processing_date, language, duration")
        print("  - transcript, ocr_text, category, tags, confidence, reasoning")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "classifications.csv"
    language = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else "auto"
    parallel = "--parallel" in sys.argv
    use_ocr = "--ocr" in sys.argv

    result = batch_classify(input_dir, output_csv, language, parallel, use_ocr=use_ocr)

    if result.get("success"):
        print("✅ Batch classification complete!")
    else:
        print(f"\n❌ Batch classification failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
