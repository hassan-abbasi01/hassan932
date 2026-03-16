"""
Test Video Summarization Module
This script tests the video summarization functionality
"""
import os
import sys
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.video_service import VideoService
from models.video import Video

def test_summarization():
    """Test video summarization with different options"""
    
    print("\n" + "="*70)
    print("VIDEO SUMMARIZATION MODULE TEST")
    print("="*70)
    
    # Initialize MongoDB connection
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        db = client['snipx']
        videos_collection = db['videos']
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    # Initialize VideoService
    video_service = VideoService(videos_collection)
    
    # Test video path - use one from uploads
    test_video_path = None
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    
    if os.path.exists(uploads_dir):
        video_files = [f for f in os.listdir(uploads_dir) if f.endswith(('.mp4', '.avi', '.mov'))]
        if video_files:
            test_video_path = os.path.join(uploads_dir, video_files[0])
            print(f"✅ Found test video: {video_files[0]}")
    
    if not test_video_path or not os.path.exists(test_video_path):
        print("❌ No test video found in uploads folder")
        print("   Please upload a video first using the app")
        return
    
    # Create test video document
    video_doc = {
        'user_id': 'test_user',
        'filename': os.path.basename(test_video_path),
        'original_filename': os.path.basename(test_video_path),
        'filepath': test_video_path,
        'status': 'uploaded',
        'created_at': datetime.now(),
        'file_size': os.path.getsize(test_video_path),
        'outputs': {}
    }
    
    # Insert or update video document
    existing = videos_collection.find_one({'filepath': test_video_path})
    if existing:
        video_id = existing['_id']
        videos_collection.update_one({'_id': video_id}, {'$set': video_doc})
        print(f"✅ Updated existing video document: {video_id}")
    else:
        result = videos_collection.insert_one(video_doc)
        video_id = result.inserted_id
        print(f"✅ Created new video document: {video_id}")
    
    # Test different summarization options
    test_cases = [
        {
            'name': 'Short Summary - Action Focus',
            'options': {
                'summarize': True,
                'summary_length': 'short',
                'summary_focus': 'action'
            }
        },
        {
            'name': 'Medium Summary - Balanced',
            'options': {
                'summarize': True,
                'summary_length': 'medium',
                'summary_focus': 'balanced'
            }
        },
        {
            'name': 'Long Summary - Speech Focus',
            'options': {
                'summarize': True,
                'summary_length': 'long',
                'summary_focus': 'speech'
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print("\n" + "-"*70)
        print(f"TEST CASE {i}: {test_case['name']}")
        print("-"*70)
        
        try:
            # Process video with test options
            video_service.process_video(str(video_id), test_case['options'])
            
            # Get updated video document
            updated_video = videos_collection.find_one({'_id': video_id})
            
            if updated_video and 'summary' in updated_video.get('outputs', {}):
                summary_data = updated_video['outputs']['summary']
                
                print(f"\n✅ SUMMARIZATION SUCCESSFUL")
                print(f"Original Duration: {summary_data['original_duration']:.1f}s")
                print(f"Condensed Duration: {summary_data['condensed_duration']:.1f}s")
                print(f"Compression: {(1 - summary_data['condensed_duration']/summary_data['original_duration'])*100:.1f}%")
                print(f"Segments: {summary_data['segments_count']}")
                
                if summary_data.get('condensed_video_path'):
                    if os.path.exists(summary_data['condensed_video_path']):
                        file_size = os.path.getsize(summary_data['condensed_video_path'])
                        print(f"Condensed Video: {summary_data['condensed_video_path']}")
                        print(f"File Size: {file_size / (1024*1024):.2f} MB")
                    else:
                        print(f"⚠️ Condensed video file not found: {summary_data['condensed_video_path']}")
                
                # Print text summary preview
                if summary_data.get('text_summary'):
                    print("\nText Summary Preview (first 500 chars):")
                    print("-" * 70)
                    print(summary_data['text_summary'][:500])
                    if len(summary_data['text_summary']) > 500:
                        print("...")
            else:
                print("❌ Summarization failed - no summary data in outputs")
                if updated_video:
                    error = updated_video.get('outputs', {}).get('summary_error', 'Unknown error')
                    print(f"Error: {error}")
        
        except Exception as e:
            print(f"❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        # Ask user if they want to continue
        if i < len(test_cases):
            response = input("\nPress Enter to continue to next test, or 'q' to quit: ")
            if response.lower() == 'q':
                break
    
    print("\n" + "="*70)
    print("TESTING COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_summarization()
