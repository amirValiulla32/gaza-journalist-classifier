#!/usr/bin/env python3
"""
Twitter Video Downloader for Gaza Journalist Archive
Downloads all videos from a Twitter/X account with metadata.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


def download_twitter_videos(handle: str, output_dir: str = None) -> dict:
    """
    Download all videos from a Twitter handle.

    Args:
        handle: Twitter handle (with or without @)
        output_dir: Directory to save videos (default: ./downloads/handle_name/)

    Returns:
        dict with download statistics
    """
    # Clean handle
    handle = handle.lstrip('@')

    # Set output directory
    if output_dir is None:
        output_dir = f"./downloads/{handle}"

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"TWITTER VIDEO DOWNLOADER")
    print(f"{'='*60}\n")
    print(f"📱 Account: @{handle}")
    print(f"📁 Output: {output_path}")
    print(f"\n⏳ Downloading videos (this may take a while)...\n")

    # yt-dlp command for Twitter
    # Downloads videos, saves metadata, skips if already downloaded
    url = f"https://twitter.com/{handle}"

    try:
        result = subprocess.run([
            "yt-dlp",
            url,
            # Output format
            "-o", str(output_path / "%(upload_date)s_%(id)s_%(title)s.%(ext)s"),
            # Only download videos
            "--match-filter", "!is_live",
            # Save metadata
            "--write-info-json",
            "--write-description",
            # Quality
            "--format", "best",
            # Skip already downloaded
            "--download-archive", str(output_path / ".downloaded.txt"),
            # Don't re-download
            "--no-overwrites",
            # Verbose for debugging
            "--progress",
            # Ignore errors (some tweets might be deleted)
            "--ignore-errors",
            # Date after (optional - uncomment to limit to recent)
            # "--dateafter", "20240101",
        ], check=False, capture_output=False)

        success = result.returncode == 0

    except FileNotFoundError:
        print("\n❌ Error: yt-dlp not found!")
        print("Install with: pip install yt-dlp")
        print("Or: brew install yt-dlp")
        return {
            "success": False,
            "error": "yt-dlp not installed"
        }

    # Count downloaded videos
    video_files = list(output_path.glob("*.mp4")) + list(output_path.glob("*.mkv"))
    json_files = list(output_path.glob("*.info.json"))

    print(f"\n{'='*60}")
    print(f"DOWNLOAD COMPLETE")
    print(f"{'='*60}\n")
    print(f"✅ Videos downloaded: {len(video_files)}")
    print(f"📄 Metadata files: {len(json_files)}")
    print(f"📁 Location: {output_path}")

    # Create summary
    summary = {
        "journalist_handle": handle,
        "download_date": datetime.now().isoformat(),
        "videos_downloaded": len(video_files),
        "metadata_files": len(json_files),
        "output_directory": str(output_path),
        "success": True
    }

    # Save summary
    summary_file = output_path / "download_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"💾 Summary saved to: {summary_file}")
    print(f"\n{'='*60}\n")

    return summary


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python twitter_downloader.py <twitter_handle> [output_dir]")
        print("\nExamples:")
        print("  python twitter_downloader.py @journalist_name")
        print("  python twitter_downloader.py journalist_name")
        print("  python twitter_downloader.py @journalist_name ./custom_folder/")
        print("\nRequirements:")
        print("  - yt-dlp installed (pip install yt-dlp)")
        print("\nNote:")
        print("  - Downloads ALL videos from the account")
        print("  - Skips already downloaded videos (resume-safe)")
        print("  - Saves metadata alongside videos")
        sys.exit(1)

    handle = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    result = download_twitter_videos(handle, output_dir)

    if result.get("success"):
        print("✅ Download successful!")
        print(f"\nNext step: Run batch classifier on {result['output_directory']}")
        print(f"  python3 batch_classify.py {result['output_directory']}")
    else:
        print(f"\n❌ Download failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
