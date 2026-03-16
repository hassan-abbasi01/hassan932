# Filler Word Removal - API Quick Reference

## Quick Start

### Enable Filler Word Removal for Video
```python
POST /api/videos/{video_id}/process

{
  "remove_filler_words": true,
  "filler_removal_level": "medium",
  "detect_repeated_words": true
}
```

### Enable Filler Removal in Audio Enhancement
```python
POST /api/videos/{video_id}/process

{
  "enhance_audio": true,
  "remove_fillers": true,
  "detect_repeated_words": true,
  "noise_reduction": "moderate"
}
```

## Configuration Options

### `remove_filler_words` (boolean)
Enable/disable video filler word removal
- **Default**: `false`
- **Use**: Removes filler words and cuts video segments

### `filler_removal_level` (string)
Detection sensitivity level
- **Options**: `'conservative'` | `'medium'` | `'aggressive'`
- **Default**: `'medium'`

**Levels:**
- `conservative`: Only um, uh, er (3 words)
- `medium`: Common fillers (9 words)
- `aggressive`: All fillers (30+ words/phrases)

### `detect_repeated_words` (boolean)
Detect consecutive repeated words
- **Default**: `true`
- **Example**: Removes second occurrence in "I I think"

### `remove_fillers` (boolean)
Enable filler removal in audio enhancement
- **Default**: `false`
- **Use**: Audio-only filler removal (without video cutting)

### `noise_reduction` (string)
Noise reduction level (independent option)
- **Options**: `'none'` | `'light'` | `'moderate'` | `'strong'`
- **Default**: `'moderate'`

## Detected Filler Words

### Conservative Level
```
um, uh, er
```

### Medium Level
```
um, uh, er, ah, hmm, mm, hm, like, you know
```

### Aggressive Level
```
Single words:
um, uh, er, ah, hmm, mm, hm, mmm, like, so, well, 
right, actually, basically, literally

Multi-word phrases:
you know, but you know, i guess, i suppose, 
kind of, sort of, or something, you see, 
you know what i mean, mm-hmm
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "video_id": "abc123",
  "outputs": {
    "cleaned_video": "/uploads/video_cleaned.mp4",
    "filler_removal_stats": {
      "segments_removed": 15,
      "filler_words_removed": 12,
      "repeated_words_removed": 3,
      "original_duration": "120.50s",
      "cleaned_duration": "115.30s",
      "time_saved": "5.20s",
      "percentage_saved": "4.3%"
    }
  }
}
```

## Examples

### Example 1: Basic Filler Removal
```javascript
const options = {
  remove_filler_words: true
};

// Removes um, uh, er, ah, hmm, mm, hm, like, "you know"
```

### Example 2: Aggressive Cleanup
```javascript
const options = {
  remove_filler_words: true,
  filler_removal_level: 'aggressive',
  detect_repeated_words: true
};

// Removes all 30+ filler variations + repeated words
```

### Example 3: Conservative (Minimal Changes)
```javascript
const options = {
  remove_filler_words: true,
  filler_removal_level: 'conservative',
  detect_repeated_words: false
};

// Only removes um, uh, er
```

### Example 4: Audio Enhancement + Filler Removal
```javascript
const options = {
  enhance_audio: true,
  remove_fillers: true,
  noise_reduction: 'moderate'
};

// Enhances audio quality + removes fillers (no video cutting)
```

### Example 5: Complete Processing
```javascript
const options = {
  remove_filler_words: true,
  filler_removal_level: 'medium',
  detect_repeated_words: true,
  enhance_audio: true,
  noise_reduction: 'moderate',
  generate_subtitles: true,
  generate_thumbnail: true
};

// Full video processing pipeline
```

## WebSocket Progress Events

During processing, real-time progress updates:

```javascript
socket.on('processing_progress', (data) => {
  console.log(data);
  /*
  {
    video_id: "abc123",
    step: "removing_fillers",
    progress: 65,
    message: "Removing filler words from video...",
    timestamp: "2025-12-27T10:30:45Z"
  }
  */
});
```

## Processing Steps

1. **extracting_audio** - Extract audio from video
2. **loading_whisper** - Load Whisper AI model
3. **detecting_fillers** - Transcribe and detect fillers
4. **cutting_video** - Cut video segments
5. **concatenating** - Merge clean segments
6. **completed** - Processing complete

## Performance

| Video Length | Processing Time | GPU Required |
|--------------|----------------|--------------|
| 1 minute | ~30 seconds | Optional |
| 5 minutes | ~2-3 minutes | Recommended |
| 10 minutes | ~5-6 minutes | Recommended |
| 30+ minutes | ~15-20 minutes | Highly Recommended |

## Error Handling

### No Fillers Detected
```json
{
  "message": "No filler words detected",
  "cleaned_video": null,
  "note": "Original video unchanged"
}
```

### Whisper Error
```json
{
  "error": "Failed to load Whisper model",
  "fallback": "Using energy-based detection"
}
```

## Tips & Best Practices

### 1. **Choose the Right Level**
- **Interviews/Podcasts**: `medium` or `aggressive`
- **Presentations**: `medium`
- **Professional Content**: `conservative`

### 2. **Audio Quality Matters**
- Clear audio = better detection
- Background noise reduces accuracy
- Use noise reduction first if needed

### 3. **Review Before Publishing**
- Check cleaned video for any issues
- Some "fillers" might be intentional
- Adjust detection level if needed

### 4. **Combine with Other Features**
```javascript
// Recommended combination
{
  remove_filler_words: true,
  filler_removal_level: 'medium',
  detect_repeated_words: true,
  noise_reduction: 'moderate',
  generate_subtitles: true
}
```

### 5. **Performance Optimization**
- Use GPU for faster processing
- Process shorter videos first to test
- Conservative mode is fastest

## Limitations

1. **Language**: Optimized for English
2. **Context**: May remove intentional usage
3. **Speed**: Requires Whisper transcription
4. **Accuracy**: 95%+ with clear audio

## Support

For issues or questions:
- Check logs in console
- Review detected segments
- Adjust detection level
- Enable/disable repeated word detection

---

**Last Updated**: December 27, 2025
**API Version**: 1.0
**Whisper Model**: base
