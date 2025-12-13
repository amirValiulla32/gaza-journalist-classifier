#!/usr/bin/env python3
"""Extract specific metadata from video files."""

import subprocess
import json
import sys
from pathlib import Path
from datetime import timedelta


def extract_video_metadata(video_path: str) -> dict:
    """Extract key metadata from video file."""
    try:
        # Run ffprobe to get metadata
        result = subprocess.run([
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ], capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)

        # Extract format and streams info
        format_info = data.get("format", {})
        video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "audio"), {})

        # Parse duration
        duration_seconds = float(format_info.get("duration", 0))
        duration_td = timedelta(seconds=duration_seconds)
        duration_formatted = str(duration_td).split('.')[0]  # Remove microseconds

        # Parse file size
        file_size_bytes = int(format_info.get("size", 0))
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Get resolution
        width = video_stream.get("width", "unknown")
        height = video_stream.get("height", "unknown")
        resolution = f"{width}x{height}"

        # Get codecs
        video_codec = video_stream.get("codec_name", "unknown").upper()
        audio_codec = audio_stream.get("codec_name", "unknown").upper()
        format_name = format_info.get("format_name", "unknown").split(',')[0].upper()

        # Extract tags
        tags = format_info.get("tags", {})

        # Build metadata dictionary
        metadata = {
            "title": tags.get("title", "No title"),
            "duration_seconds": duration_seconds,
            "duration_formatted": duration_formatted,
            "resolution": resolution,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_mb, 2),
            "format": format_name,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "creation_date": tags.get("creation_time", "unknown"),
            "license": tags.get("comment", "unknown"),
            "source_url": extract_url_from_title(tags.get("title", "")),
            "encoder": tags.get("encoder", "unknown"),
            "language": tags.get("language", "unknown")
        }

        return metadata

    except subprocess.CalledProcessError as e:
        print(f"Error running ffprobe: {e}")
        return {}
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return {}


def extract_url_from_title(title: str) -> str:
    """Extract URL from title if present."""
    if "http://" in title or "https://" in title:
        # Simple extraction - find text starting with http
        parts = title.split()
        for part in parts:
            if part.startswith("http://") or part.startswith("https://"):
                return part
    return "No URL found"


def print_metadata(metadata: dict, video_name: str):
    """Print metadata in a nice format."""
    print(f"\n{'='*60}")
    print(f"METADATA: {video_name}")
    print(f"{'='*60}\n")

    print(f"📝 Title: {metadata['title']}")
    print(f"⏱️  Duration: {metadata['duration_formatted']} ({metadata['duration_seconds']}s)")
    print(f"📐 Resolution: {metadata['resolution']}")
    print(f"💾 File Size: {metadata['file_size_mb']} MB ({metadata['file_size_bytes']:,} bytes)")
    print(f"🎬 Format: {metadata['format']} ({metadata['video_codec']} video, {metadata['audio_codec']} audio)")
    print(f"📅 Creation Date: {metadata['creation_date']}")
    print(f"⚖️  License: {metadata['license']}")
    print(f"🔗 Source URL: {metadata['source_url']}")
    print(f"🔧 Encoder: {metadata['encoder']}")
    print(f"🌐 Language: {metadata['language']}")

    print(f"\n{'='*60}\n")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_metadata.py <video_file>")
        print("\nExample: python extract_metadata.py test_video.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    video_name = Path(video_path).name

    metadata = extract_video_metadata(video_path)

    if metadata:
        print_metadata(metadata, video_name)

        # Save to JSON
        output_file = Path(video_path).stem + "_metadata.json"
        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"💾 Metadata saved to: {output_file}\n")
    else:
        print("❌ Failed to extract metadata")
        sys.exit(1)


if __name__ == "__main__":
    main()
