#!/usr/bin/env python3
"""
Vision Analysis Module - Describe video frame content using LLaVA vision model.

This module uses LLaVA (Large Language and Vision Assistant) via Ollama to:
- Analyze video frames and describe visual content
- Identify objects, people, activities, and conditions
- Support multimodal classification (vision + audio + OCR)
"""

import base64
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "llava:7b"

# Vision analysis prompt for Gaza journalist videos
VISION_PROMPT = """Describe what you see in this frame from a Gaza journalist video report.

Focus on identifying:

**Physical Elements:**
- Buildings/structures (intact, damaged, partially destroyed, completely destroyed, rubble)
- Infrastructure type (residential, hospital/medical, school/educational, mosque/religious, commercial)
- Conditions (fire, smoke, dust clouds, flooding, darkness, debris)

**People:**
- Approximate number (individual, small group 2-5, group 6-20, crowd 20+, or none visible)
- Types if identifiable (civilians, children, medical workers, emergency responders, armed personnel)
- Activities (rescue operations, medical treatment, fleeing/displacement, gathering, protesting)

**Objects/Equipment:**
- Medical equipment (hospital beds, IV stands, ambulances, stretchers)
- Emergency response (rescue equipment, firefighting)
- Military/conflict (weapons, vehicles, uniforms)
- Humanitarian (tents, food distribution, water containers, aid supplies)
- Media (cameras, press vests, microphones)

**Setting:**
- Indoor or outdoor
- Urban or camp environment
- Day or night
- Weather/atmospheric conditions

Be factual and specific. Only describe what is clearly visible in the frame.
If something is unclear or ambiguous, note that.
Avoid interpretation or assumptions - stick to observable facts.

Describe this frame:"""


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode image file to base64 string for Ollama API.

    Args:
        image_path: Path to image file

    Returns:
        Base64 encoded string
    """
    with open(image_path, 'rb') as f:
        image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')


def analyze_frame_with_llava(
    frame_path: str,
    model: str = VISION_MODEL,
    prompt: str = VISION_PROMPT
) -> Dict:
    """
    Analyze a video frame using LLaVA vision model via Ollama.

    Args:
        frame_path: Path to frame image file
        model: Ollama model to use (default: llava:7b)
        prompt: Analysis prompt

    Returns:
        Dictionary with analysis results:
        {
            'description': str,  # Visual description
            'success': bool,     # Whether analysis succeeded
            'error': str         # Error message if failed
        }
    """
    try:
        # Encode image to base64
        image_b64 = encode_image_to_base64(frame_path)

        # Call Ollama API
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for factual descriptions
                "top_p": 0.9
            }
        }

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=60  # Vision models can take longer
        )

        if response.status_code == 200:
            result = response.json()
            description = result.get('response', '').strip()

            return {
                'description': description,
                'success': True,
                'error': None
            }
        else:
            return {
                'description': '',
                'success': False,
                'error': f"Ollama API error: {response.status_code} - {response.text}"
            }

    except requests.exceptions.Timeout:
        return {
            'description': '',
            'success': False,
            'error': "Vision analysis timed out (>60s)"
        }
    except Exception as e:
        return {
            'description': '',
            'success': False,
            'error': f"Vision analysis error: {str(e)}"
        }


def analyze_frames_batch(
    frame_paths: List[str],
    include_timestamps: bool = True
) -> Dict:
    """
    Analyze multiple video frames and combine descriptions.

    Args:
        frame_paths: List of paths to frame images
        include_timestamps: Include frame position info in descriptions

    Returns:
        Dictionary with combined analysis:
        {
            'frame_descriptions': List[Dict],  # Individual frame results
            'combined_description': str,       # All descriptions combined
            'total_frames': int,
            'successful_frames': int,
            'failed_frames': int
        }
    """
    frame_descriptions = []
    successful = 0
    failed = 0

    print(f"\n🎬 Analyzing {len(frame_paths)} frames with LLaVA vision model...")

    for i, frame_path in enumerate(frame_paths, 1):
        frame_name = Path(frame_path).name
        print(f"  Frame {i}/{len(frame_paths)}: {frame_name}...", end=" ")

        result = analyze_frame_with_llava(frame_path)

        if result['success']:
            print(f"✅ ({len(result['description'])} chars)")
            successful += 1

            # Extract timestamp from frame filename if available
            # Format: frame_001.jpg, frame_002.jpg, etc.
            frame_number = i

            frame_descriptions.append({
                'frame_number': frame_number,
                'frame_path': frame_path,
                'description': result['description'],
                'success': True
            })
        else:
            print(f"❌ {result['error']}")
            failed += 1

            frame_descriptions.append({
                'frame_number': i,
                'frame_path': frame_path,
                'description': '',
                'success': False,
                'error': result['error']
            })

    # Combine all successful descriptions
    combined_parts = []
    for frame in frame_descriptions:
        if frame['success'] and frame['description']:
            if include_timestamps:
                # Determine position (start, middle, end)
                position = "start" if frame['frame_number'] <= len(frame_paths) // 3 else \
                          "middle" if frame['frame_number'] <= 2 * len(frame_paths) // 3 else \
                          "end"

                combined_parts.append(
                    f"Frame {frame['frame_number']} ({position}): {frame['description']}"
                )
            else:
                combined_parts.append(frame['description'])

    combined_description = "\n\n".join(combined_parts)

    print(f"\n✅ Vision analysis complete: {successful}/{len(frame_paths)} frames successful")
    print(f"📝 Combined description: {len(combined_description)} characters")

    return {
        'frame_descriptions': frame_descriptions,
        'combined_description': combined_description,
        'total_frames': len(frame_paths),
        'successful_frames': successful,
        'failed_frames': failed
    }


def main():
    """Test vision analysis on example frames."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 analyze_frame_content.py <frame1.jpg> [frame2.jpg ...]")
        print("\nExample:")
        print("  python3 analyze_frame_content.py frames/frame_001.jpg frames/frame_002.jpg")
        sys.exit(1)

    frame_paths = sys.argv[1:]

    # Verify frames exist
    for frame_path in frame_paths:
        if not Path(frame_path).exists():
            print(f"❌ Frame not found: {frame_path}")
            sys.exit(1)

    # Analyze frames
    result = analyze_frames_batch(frame_paths)

    # Print results
    print("\n" + "="*80)
    print("COMBINED VISUAL DESCRIPTION:")
    print("="*80)
    print(result['combined_description'])
    print("="*80)

    # Save to file
    output_file = "vision_analysis_output.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("VISION ANALYSIS RESULTS\n")
        f.write("="*80 + "\n\n")

        for frame in result['frame_descriptions']:
            if frame['success']:
                f.write(f"Frame {frame['frame_number']}: {Path(frame['frame_path']).name}\n")
                f.write(f"{frame['description']}\n\n")
                f.write("-"*80 + "\n\n")

        f.write("\nCOMBINED DESCRIPTION:\n")
        f.write("="*80 + "\n")
        f.write(result['combined_description'])

    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
