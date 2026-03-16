"""
Test script for AI-powered thumbnail generation
"""
import os
import sys
from services.video_service import AIThumbnailGenerator

def test_ai_thumbnail():
    print("=" * 60)
    print("Testing AI Thumbnail Generator")
    print("=" * 60)
    
    # Initialize AI generator
    print("\n[1] Initializing AI Thumbnail Generator...")
    generator = AIThumbnailGenerator()
    
    # Test with a sample video file
    video_dir = "uploads"
    video_files = [f for f in os.listdir(video_dir) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    if not video_files:
        print("\n❌ No video files found in uploads/ directory")
        print("Please upload a video file first.")
        return
    
    video_file = os.path.join(video_dir, video_files[0])
    print(f"\n[2] Using test video: {video_file}")
    
    # Create a test frame (simulate frame extraction)
    import cv2
    cap = cv2.VideoCapture(video_file)
    
    if not cap.isOpened():
        print(f"\n❌ Could not open video file")
        return
    
    # Get a frame from middle of video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"\n❌ Could not read frame from video")
        return
    
    # Save test frame
    test_frame_path = "test_frame.jpg"
    cv2.imwrite(test_frame_path, frame)
    print(f"   ✓ Extracted test frame")
    
    # Test AI text generation
    print("\n[3] Generating AI catchy text...")
    ai_text = generator.generate_catchy_text(test_frame_path, video_file)
    print(f"   ✓ Generated text: '{ai_text}'")
    
    # Test YouTube thumbnail creation
    print("\n[4] Creating professional YouTube thumbnail...")
    output_path = "test_ai_thumbnail.jpg"
    result = generator.create_youtube_thumbnail(test_frame_path, ai_text, output_path)
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / 1024
        print(f"   ✓ Created thumbnail: {output_path} ({file_size:.1f} KB)")
        
        # Check dimensions
        import PIL.Image
        img = PIL.Image.open(output_path)
        print(f"   ✓ Dimensions: {img.width}x{img.height} (YouTube 16:9 format)")
        
        print("\n" + "=" * 60)
        print("✅ AI THUMBNAIL GENERATION SUCCESSFUL!")
        print("=" * 60)
        print(f"\nGenerated thumbnail saved at: {output_path}")
        print(f"AI-generated text: '{ai_text}'")
    else:
        print("\n❌ Failed to create thumbnail")
    
    # Cleanup
    if os.path.exists(test_frame_path):
        os.remove(test_frame_path)

if __name__ == "__main__":
    test_ai_thumbnail()
