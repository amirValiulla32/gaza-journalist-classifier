#!/usr/bin/env python3
"""
Check which video URLs in the Excel file are still accessible
Returns the URLs that fail to download
"""

import pandas as pd
import subprocess
from pathlib import Path
import json

def check_video_accessible(url: str) -> bool:
    """Check if video URL is accessible without downloading."""
    cmd = [
        "yt-dlp",
        "--skip-download",  # Don't actually download
        "--no-warnings",
        "--quiet",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0
    except:
        return False

def main():
    excel_file = "Gaza Archive Form (Responses)-6.xlsx"

    print(f"Reading {excel_file}...")
    df = pd.read_excel(excel_file)

    print(f"Total entries: {len(df)}\n")

    # Filter to processable platforms
    df['source'] = df['Source Link/URL'].apply(
        lambda x: 'instagram' if 'instagram' in str(x).lower()
        else ('twitter' if 'twitter' in str(x).lower() or 'x.com' in str(x).lower()
        else ('youtube' if 'youtube' in str(x).lower()
        else ('facebook' if 'facebook' in str(x).lower()
        else 'other')))
    )

    processable = df[df['source'] != 'other']
    print(f"Processable URLs: {len(processable)}\n")

    # Check each URL
    failed_urls = []
    accessible_urls = []

    print("Checking video accessibility...\n")
    print("=" * 80)

    for idx, (i, row) in enumerate(processable.iterrows(), 1):
        url = row['Source Link/URL']
        source = row['source']
        category = row['Category']

        print(f"[{idx}/{len(processable)}] {source.upper()}: {category[:30]}...")

        if check_video_accessible(url):
            print("  ✓ Accessible")
            accessible_urls.append({
                'row': i,
                'url': url,
                'source': source,
                'category': category
            })
        else:
            print("  ✗ FAILED")
            failed_urls.append({
                'row': i,
                'url': url,
                'source': source,
                'category': category
            })

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal checked: {len(processable)}")
    print(f"Accessible: {len(accessible_urls)} ({100*len(accessible_urls)/len(processable):.1f}%)")
    print(f"Failed: {len(failed_urls)} ({100*len(failed_urls)/len(processable):.1f}%)")

    # Save failed URLs to file
    if failed_urls:
        with open('failed_urls.json', 'w', encoding='utf-8') as f:
            json.dump(failed_urls, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Failed URLs saved to: failed_urls.json")

        # Also save as text for easy copying
        with open('failed_urls.txt', 'w', encoding='utf-8') as f:
            f.write("FAILED VIDEO URLS\n")
            f.write("=" * 80 + "\n\n")
            for item in failed_urls:
                f.write(f"Row {item['row']} | {item['source'].upper()} | {item['category']}\n")
                f.write(f"{item['url']}\n\n")
        print(f"✓ Failed URLs list saved to: failed_urls.txt")

    # Save accessible URLs
    if accessible_urls:
        with open('accessible_urls.json', 'w', encoding='utf-8') as f:
            json.dump(accessible_urls, f, indent=2, ensure_ascii=False)
        print(f"✓ Accessible URLs saved to: accessible_urls.json")

    # Breakdown by platform
    print(f"\nBreakdown by platform:")
    for source in ['instagram', 'twitter', 'youtube', 'facebook']:
        failed_count = sum(1 for x in failed_urls if x['source'] == source)
        total_count = sum(1 for x in processable.iterrows() if processable.loc[x[0], 'source'] == source)
        if total_count > 0:
            print(f"  {source.capitalize()}: {failed_count}/{total_count} failed ({100*failed_count/total_count:.1f}%)")

if __name__ == "__main__":
    main()
