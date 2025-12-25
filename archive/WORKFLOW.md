# Gaza Journalist Video Classification Workflow

Complete workflow for downloading and classifying journalist videos from Twitter/X.

## Quick Start (3-Step Process)

```bash
# Step 1: Download videos from URL list
python3 batch_download.py journalist_urls.txt

# Step 2: Classify all downloaded videos
python3 batch_classify.py downloads/ results.csv ar --parallel

# Step 3: Review results in results.csv
```

## Detailed Workflow

### Phase 1: Collect Tweet URLs

**Manual Collection (Current Approach):**
1. Visit journalist's Twitter profile
2. Find video tweets you want to archive
3. Click on each tweet
4. Copy the URL from browser (e.g., `https://x.com/Timesofgaza/status/1998648404470313065`)
5. Paste into a text file (one URL per line)

**URL File Format (`journalist_urls.txt`):**
```
# Journalist: Times of Gaza
# Collection date: 2025-01-10

https://x.com/Timesofgaza/status/1998648404470313065
https://x.com/Timesofgaza/status/1234567890123456789
https://x.com/Timesofgaza/status/9876543210987654321

# Lines starting with # are comments (ignored)
# Empty lines are also ignored
```

### Phase 2: Download Videos

**Command:**
```bash
python3 batch_download.py journalist_urls.txt
```

**What it does:**
- Downloads each video from the URL list
- Saves metadata (.info.json) alongside each video
- Skips already downloaded videos (resume-safe)
- Names files as: `YYYYMMDD_tweetid.mp4`

**Output structure:**
```
downloads/
├── 20251210_1998648343958900737.mp4
├── 20251210_1998648343958900737.info.json
├── 20251211_1234567890123456789.mp4
├── 20251211_1234567890123456789.info.json
└── .downloaded.txt (tracks what's been downloaded)
```

**Advanced usage:**
```bash
# Download to specific journalist folder
python3 batch_download.py urls.txt downloads/timesofgaza/

# Resume interrupted download
python3 batch_download.py urls.txt  # Automatically skips existing
```

### Phase 3: Classify Videos

**Basic Command:**
```bash
python3 batch_classify.py downloads/
```

**Language-Specific:**
```bash
# Auto-detect language (default)
python3 batch_classify.py downloads/ results.csv auto

# Explicit Arabic (recommended for Gaza content)
python3 batch_classify.py downloads/ results.csv ar

# English only
python3 batch_classify.py downloads/ results.csv en
```

**Parallel Processing (Faster):**
```bash
# Process 3 videos at once (default)
python3 batch_classify.py downloads/ results.csv ar --parallel

# Sequential processing (slower but safer)
python3 batch_classify.py downloads/ results.csv ar
```

**What it does:**
1. Finds all .mp4 and .mkv files in directory
2. For each video:
   - Extracts audio with ffmpeg
   - Transcribes with whisper.cpp
   - Classifies with DeepSeek LLM
3. Exports all results to CSV

### Phase 4: Review Results

**CSV Output (`classifications.csv`):**
```csv
video_file,video_name,tweet_url,journalist_handle,download_date,processing_date,language,duration,transcript,category,tags,confidence,reasoning
/path/to/video.mp4,video.mp4,https://x.com/...,Timesofgaza,2025-01-10T...,2025-01-10T...,ar,"المشهد...",Displacement,"Children, Women",high,"The transcript describes..."
```

**Columns explained:**
- `video_file`: Full path to video file
- `video_name`: Just the filename
- `tweet_url`: Original Twitter URL
- `journalist_handle`: Twitter username
- `download_date`: When video was published/downloaded
- `processing_date`: When classification was done
- `language`: Language code (en, ar, auto)
- `duration`: Video duration (future enhancement)
- `transcript`: Full transcribed text
- `category`: Main classification (one of 10 categories)
- `tags`: Comma-separated tags
- `confidence`: high/medium/low
- `reasoning`: AI explanation of classification

**Open in Excel/Google Sheets:**
- Import CSV with UTF-8 encoding
- Review classifications
- Sort by category, tags, confidence
- Filter by journalist, date, etc.

## Categories and Tags Reference

### Categories (Choose ONE per video)
1. Destruction of Property
2. Displacement
3. IDF
4. Jewish Dissent
5. Inhumane Acts
6. Imprisonment
7. Resilience
8. Starvation of Civilian
9. Testimonials
10. Willful Killing

### Tags (Multiple allowed)
- Birth Prevention
- Ceasefire Violation
- Children
- Food
- Journalists
- Healthcare workers
- Hospitals
- Hostages
- Mosques
- Prisoners
- Schools
- Water
- Repression
- Torture
- Testimonials
- Women
- IDF
- Settlers
- Other

## Pilot Demo Workflow (5 Journalists)

**Day 1-2: URL Collection**
```bash
# Create URL files for each journalist
mkdir -p url_lists/
nano url_lists/journalist1_urls.txt  # Paste URLs
nano url_lists/journalist2_urls.txt
# ... etc for 5 journalists
```

**Day 3: Batch Download**
```bash
# Download all journalists' videos
for url_file in url_lists/*.txt; do
    journalist=$(basename "$url_file" _urls.txt)
    python3 batch_download.py "$url_file" "downloads/$journalist/"
done
```

**Day 4: Batch Classification**
```bash
# Classify all videos (parallel processing)
for journalist_dir in downloads/*/; do
    journalist=$(basename "$journalist_dir")
    python3 batch_classify.py "$journalist_dir" "results_${journalist}.csv" ar --parallel
done

# Combine all results
cat results_*.csv > pilot_results_combined.csv
```

**Day 5: Review & Report**
- Open `pilot_results_combined.csv` in Google Sheets
- Review classifications for accuracy
- Generate summary statistics
- Prepare presentation for volunteer meeting

## Troubleshooting

### Download Issues
**Problem:** `yt-dlp: command not found`
```bash
pip3 install yt-dlp
```

**Problem:** Tweet deleted/unavailable
- URL will be marked as failed
- Check `failed_urls` in output
- Remove from URL file for future runs

### Classification Issues
**Problem:** `whisper.cpp not found`
```bash
# Build whisper.cpp
cd whisper.cpp && cmake -B build && cmake --build build
```

**Problem:** `Ollama connection failed`
```bash
# Start Ollama in separate terminal
ollama serve

# Verify model is installed
ollama list  # Should show deepseek-v3.1:671b-cloud
```

**Problem:** Poor transcription quality
```bash
# Use explicit language instead of auto
python3 batch_classify.py downloads/ results.csv ar
```

### CSV Issues
**Problem:** Arabic text shows as gibberish in Excel
- Import with UTF-8 encoding
- Or use Google Sheets (handles UTF-8 automatically)

## Performance Expectations

**Download speed:**
- ~10-30 seconds per video (depends on size)
- 50 videos ≈ 10-25 minutes

**Classification speed:**
- ~1-2 minutes per video (sequential)
- ~30-45 seconds per video (parallel, 3 workers)
- 50 videos ≈ 25-45 minutes (parallel)

**Pilot estimate (5 journalists, ~10 videos each):**
- URL collection: 30-60 minutes (manual)
- Download: ~10-15 minutes
- Classification: ~15-25 minutes (parallel)
- **Total: ~1-2 hours** for complete pilot

## Database Migration (Future)

When ready to scale beyond CSV:

**Option 1: SQLite (simple, file-based)**
```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    video_file TEXT,
    tweet_url TEXT,
    journalist_handle TEXT,
    download_date DATETIME,
    transcript TEXT,
    category TEXT,
    confidence TEXT,
    language TEXT
);

CREATE TABLE tags (
    video_id INTEGER,
    tag_name TEXT,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

**Option 2: PostgreSQL (production-ready)**
- Better for multi-user access
- More robust for 100+ journalists
- Can host on cloud for volunteer access

**Migration script:**
```python
# Read CSV and insert into database
import sqlite3
import csv

conn = sqlite3.connect('journalist_archive.db')
# ... import CSV data
```

## Next Steps

1. **Test the pilot workflow** with 1-2 journalists first
2. **Measure time and effort** to estimate full scale
3. **Review classification accuracy** with domain experts
4. **Iterate on categories/tags** if needed
5. **Scale to 100+ journalists** once validated
