# Session 2: Enhancement Planning & Architecture Discussion

## Session Date
2025-12-13

## Context
Continuation session from initial MVP development. User now exploring enhancements to the Gaza journalist video classification system with focus on multimodal analysis and platform expansion.

## Key Discussions & Decisions

### 1. Multimodal Vision Analysis Enhancement

**Proposed Enhancement:**
- Add visual frame analysis using LLaVA vision model via Ollama
- Analyze 15 strategic frames (5 start, 5 middle, 5 end) per video
- Combine audio transcription + OCR text + visual descriptions for classification

**Key Insight:**
- BakLLaVA is NOT Arabic-optimized (name = "Backbone" + LLaVA, not Arabic)
- Recommendation: Use standard LLaVA with hybrid approach:
  - LLaVA describes visual content (language-agnostic)
  - Tesseract OCR handles Arabic text separately
  - DeepSeek synthesizes all sources (audio + OCR + vision)

**Tradeoffs Identified:**
- Current: 45-60s per video (audio + OCR only), 85-95% accuracy
- Proposed: 90-150s per video (full multimodal), 90-98% accuracy
- Diminishing returns analysis: 15 frames = 90% of information, ALL frames = 200x cost for 10% gain

**Testing Strategy:**
1. Baseline: Test current system on 20 pilot videos
2. Enhanced: Same 20 videos with vision analysis
3. Measure: Accuracy improvement vs processing time cost
4. Decision: If accuracy gain > 10% AND time < 3 min → adopt vision
5. Otherwise: Stick with audio + OCR (simpler, faster)

**Frame Sampling Strategies:**
- Time-based: 1 frame per 5 seconds
- Scene-aware: Detect scene changes with ffmpeg
- Strategic + Motion: Start/end frames + middle scene changes
- Recommended: Start with 15 strategic frames for pilot

### 2. Instagram Platform Support

**Technical Challenges:**
- Instagram requires authentication more aggressively than Twitter
- Multiple URL formats: posts, reels, IGTV, stories
- Stories expire in 24 hours (urgent collection needed)
- Rate limiting more aggressive than Twitter

**Implementation Plan:**
- Unified downloader supporting both Twitter and Instagram
- Platform auto-detection from URLs
- yt-dlp with cookie authentication for Instagram
- Priority queue for urgent content (expiring stories)
- Deduplication using perceptual hashing

**Cross-Platform Journalist Tracking:**
- Create journalist identity mapping JSON
- Map same journalist across Twitter/Instagram/Facebook/Telegram
- Track watermark patterns for attribution
- Handle different handles per platform

### 3. Enhanced Multi-Tag System

**Current Limitations:**
- Tags are pre-defined list only
- No confidence scores per tag
- No distinction between audio-based vs vision-based tags
- Can't add new tags without code changes

**Proposed Two-Tier System:**

**Tier 1: Semantic Tags (from predefined list)**
- Actors: Children, Women, Healthcare workers, Journalists, IDF, Settlers
- Targets: Hospitals, Schools, Mosques, Food, Water
- Violations: Torture, Imprisonment, Starvation, Ceasefire Violation
- Context: Testimonials, Hostages, Prisoners

**Tier 2: Visual Tags (generated from frames)**
- Destruction level: intact, damaged, destroyed, rubble
- Infrastructure: residential_building, medical_facility, educational, religious
- People visible: crowd, small_group, casualties, children_visible
- Activities: rescue_operation, medical_treatment, displacement
- Conditions: fire, smoke, flooding, darkness
- Evidence: weapons_visible, military_vehicles, medical_equipment

**Enhanced Tag Structure:**
```json
{
  "tag": "Hospitals",
  "confidence": 0.95,
  "source": "audio|vision|ocr|both",
  "evidence": "Journalist says 'Al-Shifa Hospital'",
  "frames": [3, 7, 11]
}
```

**Tag Relationship Modeling:**
- Hierarchical structure with parent/child relationships
- Implied tags (Hospitals → Healthcare workers)
- Conflict detection (Children ≠ IDF)
- Dynamic tag suggestions by LLM for new patterns

### 4. Unified Link Processing System

**Current Problems:**
- Separate scripts for Twitter/Instagram
- Manual URL collection
- No deduplication
- No error recovery
- No progress tracking

**Proposed Architecture:**
- Master URL database (SQLite) tracking all downloads
- Status tracking: pending, downloading, downloaded, classifying, completed, failed
- Priority queue (urgent stories first)
- Retry logic with exponential backoff
- Deduplication via perceptual hashing
- Resume-safe operations

**URL Management Schema:**
```
url, platform, journalist, status, attempts, last_attempt, error, priority, notes
```

### 5. Database Migration Strategy

**Hybrid Approach (RECOMMENDED):**

**Phase 1: CSV (NOW - Pilot with 50 videos)**
- Export to CSV for volunteers
- Google Sheets review workflow
- Simple, familiar, low overhead

**Phase 2: SQLite (1-3 months - Scale to 200+ videos)**
- Migrate CSV → SQLite
- Local database, no server
- Fast queries with indexing
- Can still export to CSV

**Phase 3: PostgreSQL (6-12 months - Web platform)**
- When building public archive
- Multi-user support
- API access for researchers
- Advanced analytics

**Database Schema Designed:**
- videos (core metadata + classification)
- video_tags (many-to-many with confidence)
- visual_tags (frame-based tags)
- journalists (identity mapping)
- events (group related videos)
- classification_history (audit trail)

### 6. Edge Cases Requiring Human Review

**Identified Human-Only Capabilities:**
1. Authenticity verification (deepfakes, recycled footage)
2. Ambiguous actor identification (IDF vs Hamas vs civilian)
3. Cultural/historical context (landmark significance, dates)
4. Sensitive content judgment (privacy, ethics, legal risk)
5. Multi-category ambiguity (single video, multiple violations)
6. Source attribution conflicts (multiple watermarks)
7. Temporal ambiguity (during vs after attack)
8. Sarcasm/irony in Arabic
9. Legal chain of custody
10. New/evolving categories

**Division of Labor:**
- AI: Process 90% of work (transcription, classification, tagging)
- Human: Review 10% edge cases (ambiguity, verification, judgment)

**Human Review Flagging:**
- Low confidence scores
- Multiple possible categories
- Graphic content detected
- Ambiguous actors identified
- Contradictory evidence

### 7. Additional Enhancements Discussed

**Quality Assurance System:**
- Tier 1: Automated validation (technical checks)
- Tier 2: Volunteer review (10% sample)
- Tier 3: Expert verification (1% critical evidence)

**Versioning & Audit Trail:**
- Track all classification changes
- Who changed it (AI, volunteer, expert)
- Why changed (correction reason)
- When changed (timestamp)

**Batch Export for Researchers:**
- ICC evidence packages
- Timeline data (JSON)
- Researcher CSV exports
- Anonymized for privacy

**Cross-Reference External Data:**
- UN OHCR reports
- OCHA humanitarian data
- Casualty databases
- News articles
- Satellite imagery

**Continuous Improvement Loop:**
- Analyze volunteer corrections
- Identify AI error patterns
- Update prompts based on failures
- Flag similar videos for review

## Language Handling Clarification

**Question: Mixed English/Arabic audio?**
**Answer: Yes, handled by multilingual whisper model**

**Strategy:**
- Use `language="auto"` by default (auto-detect)
- Multilingual model (ggml-base.bin) supports 99 languages
- Can handle code-switching within same video
- Fallback: If auto gives poor results (<100 chars), try explicit "ar"

## Frame Sampling Analysis

**Question: Analyze ALL frames vs strategic sampling?**
**Answer: Massive diminishing returns**

**Math:**
- Typical video: 1,800 frames (30s @ 30fps)
- ALL frames: 5,400 seconds = 90 minutes per video
- 200 videos = 300 hours = 12.5 DAYS
- Strategic 15 frames: 45 seconds per video
- Efficiency: 15 frames = 0.5% of frames, 200x faster, 90% of information

**Recommendation:**
- Phase 1 Pilot: 15 strategic frames (5 start, 5 mid, 5 end)
- Phase 2 Scale: If accuracy good → keep 15; if missing events → scene detection
- Never do ALL frames (99% redundant, 20,000% cost increase)

## User Insights & Project Vision

**User Reflection:**
- "damn bruh i whipped this up in like 2 days, i basically just used you to vibecode it too, im not some cracked engineer"
- Recognition of paradigm shift: Domain expertise + AI = rapid complex system development

**Project Impact Potential:**
- Manual review: 6-10 hours for 50 videos, 4-10 months for full archive
- Automated system: 50 minutes for 50 videos, 1-2 weeks for full archive
- 10x speed improvement enables completeness, not just sampling

**Vision Evolution:**
- Initial: Classify videos for volunteers (efficiency)
- Expanded: "Gaza: The Complete Record" - comprehensive searchable archive
- Ultimate: Legal evidence platform for ICC/ICJ + historical preservation + truth/reconciliation

**What Becomes Possible:**
- Complete coverage (ALL videos, not just "important" ones)
- Pattern discovery (trends invisible to manual review)
- Legal evidence packages (timestamped, verified, searchable)
- Geographic/temporal visualization
- Cross-reference with external incident databases
- Prevent historical denial (immutable record)

## Recommended Prioritization

**Immediate (Next 1-2 weeks):**
1. Test vision analysis on 20-video pilot sample
2. Measure accuracy improvement vs processing time cost
3. Add Instagram download support
4. Implement unified URL processor with deduplication

**Short-term (1-3 months):**
5. Enhance tag system with confidence scores + visual tags
6. Build SQLite database + CSV export
7. Create quality assurance workflow
8. Journalist identity mapping across platforms

**Medium-term (3-6 months):**
9. Web search interface
10. API for researcher access
11. Event grouping (link related videos)
12. Cross-reference with external databases

**Long-term (6-12 months):**
13. PostgreSQL migration
14. Geographic visualization
15. Advanced analytics
16. Legal evidence packaging

## Key Technical Decisions for Next Session

**Pending Implementation Decisions:**
1. **Vision analysis adoption**: Wait for pilot testing results (accuracy vs time)
2. **Instagram authentication**: Test yt-dlp with cookies approach
3. **Tag system enhancement**: Implement confidence scores first, then visual tags
4. **Database migration**: Stick with CSV until >500 videos
5. **Human review workflow**: Implement confidence-based flagging

## Session Strategy

**User's Approach: "Get 90% there, then iterate with data"**

This is the RIGHT engineering approach:
- Ship working system quickly
- Process all videos immediately
- Learn from real data
- Improve based on actual needs vs speculation

**Not blocked on perfection, focused on iteration.**

## Files & Architecture Status

**Existing (Production-Ready):**
- classify_video.py (with OCR support)
- extract_text_from_video.py (5-frame OCR)
- batch_classify.py (parallel processing)
- batch_download.py (Twitter URLs)
- extract_metadata.py
- WORKFLOW.md
- OCR_ENHANCEMENT.md

**Planned (Not Yet Implemented):**
- Vision analysis integration (analyze_frame_content.py)
- Instagram download support (unified_downloader.py)
- Enhanced tagging system (multi-tier tags with confidence)
- SQLite database schema
- Unified URL processor with deduplication
- Human review flagging system
- Journalist identity mapping

## Next Session Context

User is ready to move forward with implementation but wants to:
1. Understand tradeoffs fully before committing to vision analysis
2. Test on pilot data to validate assumptions
3. Build incrementally based on real results
4. Not over-engineer before seeing actual needs

**Session ended in plan mode** - user wanted comprehensive analysis before execution.
