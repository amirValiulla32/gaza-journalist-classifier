# Enhancement Implementation Roadmap

## Overview
Detailed implementation plan for enhancing the Gaza journalist video classification system from MVP to comprehensive multimodal archive platform.

## Phase 1: Vision Analysis Testing & Validation (Week 1-2)

### Objectives
- Test LLaVA vision analysis on pilot sample
- Measure accuracy improvement vs processing time cost
- Make data-driven decision on vision adoption

### Implementation Steps

**1. Install LLaVA via Ollama**
```bash
ollama pull llava:7b  # or llava:13b for better quality
```

**2. Create Frame Analysis Module**
File: `analyze_frame_content.py`
```python
def analyze_frame_content(frame_path: str) -> dict:
    """Use LLaVA to describe frame content."""
    # Load frame as base64
    # Call Ollama vision API
    # Return structured description
```

**3. Create Multimodal Classifier**
File: `classify_video_multimodal.py`
```python
def classify_video_multimodal(video_path: str, language: str = "auto") -> dict:
    """Full pipeline: audio + OCR + vision → classification."""
    # Extract audio → transcribe
    # Extract 15 frames → OCR + vision analysis
    # Combine all context → DeepSeek classification
```

**4. Testing Framework**
File: `test_vision_enhancement.py`
```python
# Test on 20 pilot videos
# Baseline: audio + OCR only
# Enhanced: audio + OCR + vision
# Compare: accuracy, time, confidence, missed content
# Output: comparison report
```

**5. Decision Criteria**
```
If accuracy_improvement > 10% AND avg_time < 3 min:
    → Adopt vision analysis for all videos
Elif accuracy_improvement > 5% AND critical_evidence:
    → Use vision for important videos only (flagged categories)
Else:
    → Stick with audio + OCR (simpler, faster, good enough)
```

### Deliverables
- [ ] analyze_frame_content.py module
- [ ] classify_video_multimodal.py enhanced classifier
- [ ] test_vision_enhancement.py testing framework
- [ ] Vision analysis test report (20 videos)
- [ ] Go/No-Go decision documentation

---

## Phase 2: Instagram Support (Week 2-3)

### Objectives
- Enable video downloads from Instagram URLs
- Handle multiple Instagram content types
- Implement unified platform detection

### Implementation Steps

**1. Platform Detection**
File: `platform_detector.py`
```python
def detect_platform(url: str) -> str:
    """Identify platform from URL."""
    # Twitter: x.com, twitter.com
    # Instagram: instagram.com
    # Facebook: facebook.com, fb.watch
    # YouTube: youtube.com, youtu.be
```

**2. Instagram Download Module**
File: `instagram_downloader.py`
```python
def download_instagram(url: str, output_dir: str) -> dict:
    """Download Instagram video with yt-dlp."""
    # Handle posts, reels, IGTV, stories
    # Use cookies for authentication
    # Extract metadata
    # Return download result
```

**3. Unified Downloader**
File: `unified_downloader.py`
```python
class UnifiedVideoDownloader:
    """Handle downloads from multiple platforms."""
    
    def process_url_list(self, url_file: str):
        # Detect platform for each URL
        # Route to appropriate downloader
        # Track progress in SQLite
        # Handle retries with exponential backoff
```

**4. Cookie Authentication**
```bash
# Export Instagram cookies from browser
# Use browser extension or manual export
# yt-dlp --cookies cookies.txt <instagram_url>
```

**5. Priority Queue for Stories**
```python
# Detect Instagram story URLs
# Flag as priority='urgent'
# Process immediately (24hr expiration)
```

### Deliverables
- [ ] platform_detector.py module
- [ ] instagram_downloader.py module
- [ ] unified_downloader.py main system
- [ ] Cookie authentication setup guide
- [ ] Test with 10 Instagram URLs (posts + stories + reels)

---

## Phase 3: Enhanced Multi-Tag System (Week 3-4)

### Objectives
- Add confidence scores per tag
- Track tag source (audio, vision, OCR)
- Implement visual tags from frame analysis
- Support dynamic tag suggestions

### Implementation Steps

**1. Enhanced Tag Structure**
File: `tag_system.py`
```python
@dataclass
class EnhancedTag:
    tag: str
    confidence: float  # 0.0-1.0
    source: str  # 'audio', 'vision', 'ocr', 'both'
    evidence: str  # Why this tag was assigned
    frames: List[int] = None  # Frame numbers if vision-based

@dataclass
class VisualTag:
    tag: str
    confidence: float
    frames: List[int]
    description: str
```

**2. Tag Relationship System**
```python
TAG_HIERARCHY = {
    'Hospitals': {
        'parent': 'Medical Infrastructure',
        'implies': ['Healthcare workers'],
        'conflicts': [],
        'visual_evidence': ['medical_facility', 'medical_equipment_visible']
    }
}

def validate_tags(tags: List[EnhancedTag]) -> List[EnhancedTag]:
    """Add implied tags, check conflicts."""
```

**3. Enhanced Classification Output**
```python
# Old output
{
    "category": "Destruction",
    "tags": ["Hospitals", "Children"],
    "confidence": "high"
}

# New output
{
    "category": "Destruction of Property",
    "tags": [
        {"tag": "Hospitals", "confidence": 0.95, "source": "audio", "evidence": "..."},
        {"tag": "Children", "confidence": 0.88, "source": "both", "evidence": "..."}
    ],
    "visual_tags": [
        {"tag": "destroyed_building", "confidence": 0.92, "frames": [3,7,11,14]},
        {"tag": "medical_equipment_visible", "confidence": 0.85, "frames": [8,9]}
    ],
    "confidence": 0.91
}
```

**4. Dynamic Tag Suggestion**
```python
# Allow LLM to suggest new tags not in predefined list
# Track suggestions for later review
# Periodically review and add to standard tags
```

### Deliverables
- [ ] tag_system.py with enhanced structures
- [ ] Updated classify_content() for tag confidence
- [ ] Visual tag generation from frame analysis
- [ ] Tag validation with hierarchy
- [ ] CSV export with new tag format

---

## Phase 4: Unified URL Processing & Deduplication (Week 4-5)

### Objectives
- Single system for all URL processing
- Progress tracking with SQLite
- Deduplication via perceptual hashing
- Resume-safe operations

### Implementation Steps

**1. Progress Database**
File: `download_progress.db` (SQLite)
```sql
CREATE TABLE download_progress (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    platform TEXT,
    journalist TEXT,
    status TEXT,  -- pending, downloading, downloaded, classifying, completed, failed
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error TEXT,
    priority TEXT DEFAULT 'normal',
    video_path TEXT,
    metadata_path TEXT,
    video_hash TEXT,  -- for deduplication
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**2. Deduplication System**
File: `deduplication.py`
```python
def compute_perceptual_hash(video_path: str) -> str:
    """Compute hash for duplicate detection."""
    # Extract keyframe at 1 second
    # Compute perceptual hash (pHash)
    # Return hash string

def find_duplicates(video_path: str, archive: List[dict]) -> Optional[str]:
    """Check if video already exists."""
    # Compare perceptual hash
    # Compare duration + resolution
    # Return duplicate ID if found
```

**3. Enhanced Batch Processor**
File: `batch_process_all.py`
```python
class BatchProcessor:
    """Unified processing pipeline."""
    
    def process_url_list(self, url_file: str):
        # Load URLs from file
        # Update progress DB
        # Download videos (with dedup check)
        # Classify videos
        # Export to CSV
        # Update progress DB
    
    def resume_processing(self):
        # Query pending/failed from DB
        # Resume from checkpoint
```

**4. Retry Logic**
```python
def download_with_retry(url: str, max_retries: int = 3):
    """Download with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return download(url)
        except RateLimitError:
            wait = 2 ** attempt * 60  # 1min, 2min, 4min
            time.sleep(wait)
        except AuthRequired:
            log_auth_error(url)
            return None
```

### Deliverables
- [ ] SQLite progress database
- [ ] deduplication.py module
- [ ] batch_process_all.py unified system
- [ ] Resume functionality test
- [ ] Duplicate detection test

---

## Phase 5: Database Migration & Quality Assurance (Week 5-8)

### Objectives
- Migrate from CSV to SQLite for better querying
- Implement human review workflow
- Create quality assurance system
- Build journalist identity mapping

### Implementation Steps

**1. SQLite Database Schema**
File: `database/schema.sql`
```sql
-- Core tables: videos, video_tags, visual_tags, journalists, events
-- See detailed schema in session memory
```

**2. Data Migration**
File: `migrate_csv_to_db.py`
```python
def migrate_from_csv(csv_file: str, db_path: str):
    """Migrate existing CSV data to SQLite."""
    # Read CSV
    # Parse classification data
    # Insert into videos table
    # Parse tags into video_tags
    # Preserve all metadata
```

**3. Human Review Workflow**
File: `review_workflow.py`
```python
def flag_for_review(video: dict) -> bool:
    """Determine if video needs human review."""
    if video['confidence'] < 0.6:
        return True, "Low AI confidence"
    if detect_ambiguous_actors(video):
        return True, "Identity verification needed"
    if detect_graphic_content(video):
        return True, "Ethical review required"
    return False, None

def export_review_queue(db_path: str, output_csv: str):
    """Export videos flagged for review."""
    # Query videos with requires_review=TRUE
    # Export to CSV for volunteers
```

**4. Journalist Identity Mapping**
File: `journalist_mapping.json`
```json
{
    "mahmoud_shalha": {
        "canonical_name": "Mahmoud Shalha",
        "arabic_name": "محمود شلحة",
        "twitter": "@mahmoud_shalha",
        "instagram": "@mahmoud.shalha",
        "watermarks": ["MAHMOUD.SHALHA", "تصوير || محمود شلحة"]
    }
}
```

**5. Quality Metrics Dashboard**
File: `quality_dashboard.py`
```python
def generate_quality_report(db_path: str):
    """Analyze classification quality."""
    # Total videos processed
    # Accuracy by category
    # Confidence distribution
    # Human review stats
    # Common error patterns
```

### Deliverables
- [ ] SQLite database schema
- [ ] CSV to SQLite migration script
- [ ] Human review flagging system
- [ ] Journalist identity mapping
- [ ] Quality metrics dashboard

---

## Phase 6: Web Interface & API (Week 9-12)

### Objectives
- Simple web search interface
- API for researcher access
- Timeline visualization
- CSV/JSON export capabilities

### Implementation Steps

**1. FastAPI Backend**
File: `api/main.py`
```python
@app.get("/videos/search")
def search_videos(
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Search videos with filters."""

@app.get("/timeline")
def get_timeline(category: Optional[str] = None):
    """Get video counts over time."""

@app.get("/stats")
def get_statistics():
    """Archive statistics."""
```

**2. Web Interface**
File: `web/index.html` + `web/app.js`
```javascript
// Simple search form
// Timeline chart (Chart.js)
// Results table with filters
// Video player integration
// Export buttons (CSV/JSON)
```

**3. Timeline Visualization**
```python
def generate_timeline_data(category: str = None) -> dict:
    """Aggregate videos by date for visualization."""
    # Query videos grouped by date
    # Count by category
    # Format for Chart.js
```

### Deliverables
- [ ] FastAPI backend with search endpoints
- [ ] Simple web interface (HTML/JS/CSS)
- [ ] Timeline visualization
- [ ] Export functionality
- [ ] API documentation

---

## Testing Strategy

### Unit Tests
```python
# test_classification.py
def test_audio_transcription()
def test_ocr_extraction()
def test_vision_analysis()
def test_tag_confidence()
def test_deduplication()

# test_downloads.py
def test_twitter_download()
def test_instagram_download()
def test_platform_detection()
def test_retry_logic()

# test_database.py
def test_video_insertion()
def test_tag_queries()
def test_timeline_aggregation()
```

### Integration Tests
```python
# test_end_to_end.py
def test_full_pipeline():
    """Download → Classify → Store → Query"""
    
def test_multimodal_classification():
    """Audio + OCR + Vision → Enhanced classification"""

def test_batch_processing():
    """Process 10 videos in parallel"""
```

### Performance Tests
```python
# test_performance.py
def test_classification_speed():
    """Ensure <3 min per video with vision"""

def test_database_queries():
    """Ensure <1s for common searches"""

def test_batch_throughput():
    """Measure videos/hour with parallel processing"""
```

---

## Deployment Checklist

### Local Deployment (Volunteers)
- [ ] Installation script (dependencies)
- [ ] Configuration guide (API keys, paths)
- [ ] Test data (sample videos)
- [ ] User manual (WORKFLOW.md updated)
- [ ] Troubleshooting guide

### Production Deployment (Archive Platform)
- [ ] PostgreSQL migration
- [ ] Web server setup (nginx + uvicorn)
- [ ] Domain and SSL
- [ ] Backup strategy
- [ ] Monitoring (logs, errors)
- [ ] Access control (who can query/download)

---

## Risk Mitigation

### Technical Risks
1. **Vision analysis too slow**: Fallback to audio+OCR only
2. **Instagram auth breaks**: Manual download workflow
3. **LLM hallucinations**: Human review for low confidence
4. **Database performance**: Index optimization, caching
5. **Storage costs**: Video compression, cloud storage

### Operational Risks
1. **Volunteer capacity**: Automate more, reduce review burden
2. **Data loss**: Regular backups, version control
3. **Quality degradation**: Continuous monitoring, error analysis
4. **Platform changes**: yt-dlp updates, retry logic

### Legal/Ethical Risks
1. **Privacy violations**: Blur faces, redact names (configurable)
2. **Copyright issues**: Fair use for human rights documentation
3. **Data security**: Encrypted storage, access controls
4. **Graphic content**: Warning labels, age restrictions

---

## Success Metrics

### Phase 1 (Pilot)
- ✅ Process 50 videos in <2 hours
- ✅ Achieve 85%+ accuracy
- ✅ <10% requiring human correction
- ✅ Vision analysis decision made with data

### Phase 2-3 (Scale)
- ✅ Process 200+ videos
- ✅ Instagram support working
- ✅ <5% duplicate videos
- ✅ Enhanced tags improving accuracy by 5%+

### Phase 4-5 (Platform)
- ✅ 1,000+ videos in database
- ✅ Search response <1 second
- ✅ Human review queue <10% of total
- ✅ Quality dashboard operational

### Phase 6 (Public Access)
- ✅ Web interface live
- ✅ API serving researchers
- ✅ Timeline visualization working
- ✅ Export functionality tested

---

## Resource Requirements

### Compute
- Local machine: 16GB RAM, GPU optional (for vision)
- Processing: ~1,000 videos = 50-83 hours compute
- Storage: ~500GB for 1,000 videos + metadata

### Services
- Ollama (local LLM): Free
- Whisper.cpp (local transcription): Free
- Tesseract OCR (local): Free
- yt-dlp (downloader): Free
- SQLite/PostgreSQL: Free

### External (Optional)
- Cloud storage (backups): ~$10-50/month
- Web hosting: ~$20-100/month
- Domain name: ~$10/year

---

## Timeline Summary

| Phase | Duration | Deliverables | Status |
|-------|----------|--------------|--------|
| 1. Vision Testing | 1-2 weeks | Vision analysis tested, decision made | Planned |
| 2. Instagram Support | 1 week | Instagram downloads working | Planned |
| 3. Enhanced Tags | 1 week | Multi-tier tag system | Planned |
| 4. Unified Processing | 1-2 weeks | Dedup + progress tracking | Planned |
| 5. Database Migration | 3 weeks | SQLite + QA workflow | Planned |
| 6. Web Interface | 4 weeks | Search + API + timeline | Planned |
| **Total** | **11-13 weeks** | **Comprehensive platform** | - |

---

## Next Immediate Actions

**When ready to implement:**
1. Confirm vision analysis testing priority
2. Install LLaVA: `ollama pull llava:7b`
3. Create testing framework for 20-video sample
4. Run baseline tests with current system
5. Implement vision analysis
6. Compare results and decide

**User's strategy: "Get 90% there, iterate with data"**
→ Perfect approach. Ship fast, learn from reality, improve based on actual needs.
