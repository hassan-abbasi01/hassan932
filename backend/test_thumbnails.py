#!/usr/bin/env python
"""Test script to verify thumbnail generation works"""

import os
import sys
import cv2
from moviepy.editor import VideoFileClip

# Test video path
VIDEO_PATH = r"C:\Users\PCP\Documents\FYP\backend\uploads\Snapchat-2016033859.mp4"

print(f"Testing thumbnail generation for: {VIDEO_PATH}")
print(f"File exists: {os.path.exists(VIDEO_PATH)}")
print(f"File size: {os.path.getsize(VIDEO_PATH)} bytes")

# Test 1: OpenCV
print("\n=== Test 1: OpenCV ===")
try:
    cap = cv2.VideoCapture(VIDEO_PATH)
    if cap.isOpened():
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"✓ OpenCV opened video successfully")
        print(f"  Total frames: {total_frames}")
        print(f"  FPS: {fps}")
        
        # Try to read first frame
        ret, frame = cap.read()
        if ret:
            print(f"✓ Successfully read first frame, shape: {frame.shape}")
            
            # Try to save it
            test_path = VIDEO_PATH.replace(".mp4", "_test_opencv.jpg")
            success = cv2.imwrite(test_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if success and os.path.exists(test_path):
                print(f"✓ Successfully saved test thumbnail: {test_path}")
                print(f"  File size: {os.path.getsize(test_path)} bytes")
            else:
                print(f"✗ Failed to save thumbnail")
        else:
            print(f"✗ Failed to read first frame")
        cap.release()
    else:
        print(f"✗ OpenCV could not open video")
except Exception as e:
    print(f"✗ OpenCV error: {e}")

# Test 2: MoviePy
print("\n=== Test 2: MoviePy ===")
try:
    clip = VideoFileClip(VIDEO_PATH)
    print(f"✓ MoviePy opened video successfully")
    print(f"  Duration: {clip.duration} seconds")
    print(f"  FPS: {clip.fps}")
    print(f"  Size: {clip.size}")
    
    # Try to get a frame
    frame = clip.get_frame(1.0)  # Get frame at 1 second
    print(f"✓ Successfully got frame at 1s, shape: {frame.shape}")
    
    # Convert and save
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    test_path = VIDEO_PATH.replace(".mp4", "_test_moviepy.jpg")
    success = cv2.imwrite(test_path, frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if success and os.path.exists(test_path):
        print(f"✓ Successfully saved test thumbnail: {test_path}")
        print(f"  File size: {os.path.getsize(test_path)} bytes")
    else:
        print(f"✗ Failed to save thumbnail")
    
    clip.close()
except Exception as e:
    print(f"✗ MoviePy error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Summary ===")
print("If both tests succeeded, thumbnail generation should work.")
print("Check the uploads folder for *_test_*.jpg files")
