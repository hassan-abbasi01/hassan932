# Video Summarization Module

## Overview

The Video Summarization module is an AI-powered feature that automatically analyzes videos and creates condensed versions by identifying and extracting the most important moments. It combines computer vision, audio transcription, and intelligent scene detection to produce meaningful video summaries.

## Features

### 1. **AI-Powered Scene Detection**
- Motion analysis to detect action sequences
- Face detection to identify people in frames
- Edge detection for visual complexity analysis
- Intelligent scoring system to rank moments

### 2. **Audio Transcription**
- Uses Whisper AI for accurate speech-to-text
- Identifies important dialogue segments
- Supports multiple languages
- Timestamps for precise alignment

### 3. **Flexible Summarization Options**

#### Summary Length
- **Short (15%)**: Quick highlights, most essential moments only
- **Medium (30%)**: Balanced summary with key scenes
- **Long (50%)**: Comprehensive summary with detailed coverage

#### Summary Focus
- **Balanced**: Equal weight to visual and audio content
- **Action**: Prioritizes high-motion scenes and activity
- **Speech**: Focuses on dialogue and spoken content

### 4. **Condensed Video Generation**
- Creates a new MP4 file with selected segments
- Smooth transitions between clips
- GPU-accelerated encoding when available
- Maintains original video quality

### 5. **Text Summary**
- Human-readable summary document
- Lists all key moments with timestamps
- Includes transcript excerpts
- Compression statistics

## Technical Implementation

### Backend Architecture

#### Location
- Main implementation: `backend/services/video_service.py`
- Method: `_summarize_video(video)`
- Helper methods:
  - `_detect_key_segments()` - Scene detection
  - `_transcribe_for_summary()` - Audio transcription
  - `_select_final_segments()` - Segment selection
  - `_create_condensed_video()` - Video generation
  - `_generate_text_summary()` - Text summary creation

#### Processing Pipeline

```
1. Scene Detection (25%)
   ├── Sample frames at 0.5s intervals
   ├── Calculate motion scores
   ├── Detect faces
   ├── Analyze edge density
   └── Rank moments by importance

2. Audio Transcription (50%)
   ├── Extract audio to WAV
   ├── Run Whisper model
   ├── Get timestamped segments
   └── Clean up temporary files

3. Segment Selection (65%)
   ├── Combine visual + audio scores
   ├── Apply focus weighting
   ├── Calculate target duration
   ├── Remove overlapping segments
   └── Sort chronologically

4. Video Generation (75-90%)
   ├── Extract selected clips
   ├── Add fade transitions
   ├── Concatenate segments
   ├── Encode with optimal settings
   └── Save summarized video

5. Summary Creation (90-100%)
   ├── Generate statistics
   ├── Format key moments
   ├── Add transcript excerpts
   └── Save text summary
```

### Dependencies

```python
# Core video processing
moviepy==1.0.3
opencv-python>=4.10.0

# AI models
whisper-timestamped==1.14.2
torch==2.7.1

# Audio processing
pydub==0.25.1
librosa==0.10.1

# Computer vision
numpy>=2.0,<2.3
PIL (Pillow==10.1.0)
```

### GPU Acceleration

The module automatically detects and uses GPU when available:
- NVIDIA GPUs: Uses CUDA for faster processing
- Automatic CPU fallback if GPU unavailable
- Optimized encoding settings per device

## API Endpoints

### 1. Process Video with Summarization

```http
POST /api/videos/{video_id}/process
Authorization: Bearer <token>
Content-Type: application/json

{
  "summarize": true,
  "summary_length": "medium",
  "summary_focus": "balanced"
}
```

**Response:**
```json
{
  "message": "Video processing started",
  "video_id": "507f1f77bcf86cd799439011"
}
```

### 2. Get Summary Data

```http
GET /api/videos/{video_id}/summary
Authorization: Bearer <token>
```

**Response:**
```json
{
  "summary": {
    "condensed_video_path": "/path/to/video_summarized.mp4",
    "text_summary": "📊 VIDEO SUMMARY...",
    "original_duration": 120.5,
    "condensed_duration": 36.2,
    "segments_count": 8,
    "segments": [
      {
        "start": 5.2,
        "end": 10.8,
        "duration": 5.6,
        "type": "visual",
        "text": ""
      }
    ],
    "summary_length": "medium",
    "summary_focus": "balanced"
  },
  "video_id": "507f1f77bcf86cd799439011",
  "filename": "my_video.mp4"
}
```

### 3. Download Summarized Video

```http
GET /api/videos/{video_id}/download/summarized
Authorization: Bearer <token>
```

**Response:** Binary MP4 file download

### 4. Download Text Summary

```http
GET /api/videos/{video_id}/download/summary_text
Authorization: Bearer <token>
```

**Response:** Text file download

## Frontend Integration

### Location
- Main component: `src/pages/Features.tsx`
- Tab: "Summarization"

### User Interface Elements

```tsx
// State variables
const [summaryLength, setSummaryLength] = useState('medium');
const [summaryFocus, setSummaryFocus] = useState('balanced');
const [summarizationProgress, setSummarizationProgress] = useState(0);

// Handler function
const handleSummarizeVideo = () => {
  processVideo(
    { 
      summarize: true,
      summary_length: summaryLength,
      summary_focus: summaryFocus
    },
    setSummarizationProgress,
    'Video summarized successfully'
  );
};
```

### Progress Tracking

The module emits real-time progress updates via WebSocket:

```javascript
// Progress events
- 'started' (0%) - Processing initiated
- 'summarizing' (25%) - Scene detection
- 'summarizing' (50%) - Audio transcription
- 'summarizing' (65%) - Segment selection
- 'summarizing' (75-90%) - Video generation
- 'completed' (100%) - Done
```

## Usage Examples

### Example 1: Quick Highlights

```json
{
  "summarize": true,
  "summary_length": "short",
  "summary_focus": "action"
}
```

**Result:** 15% of original video showing the most exciting action moments

### Example 2: Dialogue Summary

```json
{
  "summarize": true,
  "summary_length": "medium",
  "summary_focus": "speech"
}
```

**Result:** 30% of original video focused on important conversations

### Example 3: Comprehensive Overview

```json
{
  "summarize": true,
  "summary_length": "long",
  "summary_focus": "balanced"
}
```

**Result:** 50% of original video with balanced visual and audio content

## Output Files

### 1. Condensed Video
- **Format:** MP4 (H.264)
- **Naming:** `{original_name}_summarized.mp4`
- **Location:** Same directory as original
- **Contains:** Selected segments concatenated with transitions

### 2. Text Summary
- **Format:** Plain text (.txt)
- **Naming:** `{original_name}_summary.txt`
- **Contains:**
  - Video statistics
  - Compression ratio
  - Key moments with timestamps
  - Transcript excerpts

**Example:**
```
📊 VIDEO SUMMARY
==================================================
Original Duration: 120.5 seconds
Condensed Duration: 36.2 seconds
Compression: 70.0% reduction
Key Moments: 8

🎬 KEY MOMENTS:
--------------------------------------------------

1. [0:05 - 0:11] (5.6s)
   🎥 Visual highlight

2. [0:23 - 0:31] (8.2s)
   💬 "This is an important announcement about..."

3. [1:15 - 1:25] (10.0s)
   🎥 Visual highlight
...
```

## Testing

### Manual Testing

1. Upload a video through the web interface
2. Go to the "Summarization" tab
3. Select desired length and focus
4. Click "Summarize Video"
5. Monitor progress bar
6. Download results when complete

### Automated Testing

Run the test script:

```bash
cd backend
python test_summarization.py
```

The test script will:
- Connect to MongoDB
- Find a test video in uploads
- Run all summarization configurations
- Display results and statistics
- Verify output files exist

### Test Cases

1. **Short + Action**: Fast-paced highlights
2. **Medium + Balanced**: General purpose summary
3. **Long + Speech**: Detailed with dialogue

## Performance

### Processing Time

Depends on:
- Video duration
- Resolution
- GPU availability
- Summary length

**Benchmarks** (on GPU):
- 1 minute video: ~30-60 seconds
- 5 minute video: ~2-4 minutes
- 10 minute video: ~5-8 minutes

### Resource Usage

- **RAM**: 2-4 GB during processing
- **GPU VRAM**: 2-4 GB (if available)
- **Disk Space**: 30-70% of original file size for summary

## Troubleshooting

### Issue: "Whisper not available"

**Solution:**
```bash
pip install openai-whisper whisper-timestamped
```

### Issue: "No valid clips to concatenate"

**Causes:**
- Video too short
- No significant content detected
- Corruption in video file

**Solution:**
- Use longer videos (>30 seconds recommended)
- Try different focus settings
- Verify video file integrity

### Issue: Slow processing

**Solutions:**
- Ensure GPU is properly detected
- Close other GPU-intensive applications
- Use shorter summary length
- Lower video resolution

### Issue: Out of memory

**Solutions:**
- Process shorter videos
- Use CPU mode instead of GPU
- Increase system RAM
- Close other applications

## Future Enhancements

1. **Custom segment selection**: Allow users to manually select important moments
2. **Smart chapter detection**: Automatic chapter/scene boundaries
3. **Multi-video summarization**: Combine multiple videos into one summary
4. **Style transfer**: Apply different visual styles to summaries
5. **Sentiment analysis**: Detect emotional peaks and include them
6. **Music/sound detection**: Identify and preserve musical segments
7. **Face recognition**: Track specific people throughout video
8. **Object detection**: Focus on specific objects or activities

## Best Practices

### For Users

1. **Choose appropriate length**: 
   - Short: For social media clips
   - Medium: For general summaries
   - Long: For detailed overviews

2. **Select correct focus**:
   - Action: Sports, gaming, fast-paced content
   - Speech: Interviews, podcasts, presentations
   - Balanced: General content, mixed media

3. **Video recommendations**:
   - Minimum 30 seconds
   - Maximum 30 minutes (for optimal performance)
   - Good audio quality for speech focus
   - Stable lighting for better scene detection

### For Developers

1. **Error handling**: Always wrap processing in try-catch
2. **Resource cleanup**: Close video clips properly
3. **Progress updates**: Use emit_progress for user feedback
4. **GPU fallback**: Check has_gpu() before GPU operations
5. **Temporary files**: Clean up audio/frame extractions

## Configuration

### Adjustable Parameters

In `video_service.py`:

```python
# Scene detection
sample_interval = 0.5  # Frame sampling rate
threshold_percentile = 70  # Top % of moments to keep

# Summary lengths
length_targets = {
    'short': 0.15,   # 15%
    'medium': 0.30,  # 30%
    'long': 0.50     # 50%
}

# Whisper model
model = "base"  # Options: tiny, base, small, medium, large

# Transition duration
fade_duration = 0.3  # seconds
```

## License & Credits

- **Whisper AI**: OpenAI's speech recognition model
- **MoviePy**: Video editing library
- **OpenCV**: Computer vision operations
- **FFmpeg**: Video encoding backend

## Support

For issues or questions:
1. Check the troubleshooting section
2. Run test_summarization.py for diagnostics
3. Review GPU acceleration guide
4. Check MongoDB connection
5. Verify all dependencies installed

---

**Last Updated:** February 2026
**Module Version:** 1.0.0
