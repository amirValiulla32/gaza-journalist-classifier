#!/usr/bin/env python3
"""
Batch Twitter Video Downloader
Downloads videos from a list of tweet URLs.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def download_from_url_list(url_file: str, output_dir: str = "./downloads") -> dict:
    """
    Download videos from a text file containing tweet URLs.

    Args:
        url_file: Path to text file with one tweet URL per line
        output_dir: Directory to save videos (default: ./downloads/)

    Returns:
        dict with download statistics
    """
    url_file_path = Path(url_file).resolve()

    if not url_file_path.exists():
        print(f"❌ URL file not found: {url_file_path}")
        return {"success": False, "error": "URL file not found"}

    # Read URLs from file (skip empty lines and comments)
    with open(url_file_path, 'r') as f:
        urls = [line.strip() for line in f
                if line.strip() and not line.strip().startswith('#')]

    if not urls:
        print(f"❌ No URLs found in {url_file_path}")
        return {"success": False, "error": "No URLs in file"}

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"BATCH TWITTER VIDEO DOWNLOADER")
    print(f"{'='*60}\n")
    print(f"📝 URLs to process: {len(urls)}")
    print(f"📁 Output directory: {output_path}")
    print(f"\n⏳ Starting downloads...\n")

    # Download each URL
    successful = 0
    failed = 0
    failed_urls = []

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Downloading: {url}")

        try:
            # yt-dlp command for individual tweet
            result = subprocess.run([
                "yt-dlp",
                url,
                # Output format with date and tweet ID
                "-o", str(output_path / "%(upload_date)s_%(id)s.%(ext)s"),
                # Save metadata
                "--write-info-json",
                # Quality
                "--format", "best",
                # Skip if already downloaded
                "--download-archive", str(output_path / ".downloaded.txt"),
                "--no-overwrites",
                # Progress
                "--progress",
                # Ignore errors (tweet might be deleted)
                "--ignore-errors",
            ], check=False, capture_output=False)

            if result.returncode == 0:
                print(f"✅ Downloaded successfully")
                successful += 1
            else:
                print(f"⚠️ Download failed or already exists")
                failed += 1
                failed_urls.append(url)

        except FileNotFoundError:
            print("\n❌ Error: yt-dlp not found!")
            print("Install with: pip install yt-dlp")
            return {
                "success": False,
                "error": "yt-dlp not installed"
            }
        except Exception as e:
            print(f"❌ Error downloading {url}: {e}")
            failed += 1
            failed_urls.append(url)

    # Count downloaded files
    video_files = list(output_path.glob("*.mp4")) + list(output_path.glob("*.mkv"))
    json_files = list(output_path.glob("*.info.json"))

    print(f"\n{'='*60}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*60}\n")
    print(f"✅ Successful downloads: {successful}")
    print(f"⚠️ Failed/Skipped: {failed}")
    print(f"📹 Total video files: {len(video_files)}")
    print(f"📄 Total metadata files: {len(json_files)}")
    print(f"📁 Location: {output_path}")

    if failed_urls:
        print(f"\n⚠️ Failed URLs:")
        for url in failed_urls:
            print(f"   - {url}")

    # Create summary
    summary = {
        "download_date": datetime.now().isoformat(),
        "urls_processed": len(urls),
        "successful_downloads": successful,
        "failed_downloads": failed,
        "failed_urls": failed_urls,
        "total_video_files": len(video_files),
        "total_metadata_files": len(json_files),
        "output_directory": str(output_path),
        "success": True
    }

    print(f"\n{'='*60}\n")

    return summary


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python batch_download.py <url_file> [output_dir]")
        print("\nExample: python batch_download.py journalist_urls.txt")
        print("         python batch_download.py urls.txt ./downloads/journalist1/")
        print("\nURL file format:")
        print("  - One tweet URL per line")
        print("  - Lines starting with # are ignored (comments)")
        print("  - Empty lines are ignored")
        print("\nExample url file:")
        print("  # Journalist Name - Description")
        print("  https://x.com/Timesofgaza/status/1998648404470313065")
        print("  https://x.com/handle/status/123456789")
        print("\nRequirements:")
        print("  - yt-dlp installed (pip install yt-dlp)")
        sys.exit(1)

    url_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./downloads"

    result = download_from_url_list(url_file, output_dir)

    if result.get("success"):
        print("✅ Batch download complete!")
        print(f"\nNext step: Run batch classification")
        print(f"  python3 batch_classify.py {result['output_directory']}")
    else:
        print(f"\n❌ Batch download failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
