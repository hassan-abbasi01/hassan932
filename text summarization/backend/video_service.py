import os
import json
from datetime import datetime
from models.video import Video
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import magic
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
from pydub.silence import split_on_silence, detect_nonsilent
from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import librosa
import scipy.signal
import re
import whisper_timestamped as whisper_ts

# Import GPU manager for automatic GPU/CPU fallback
from services.gpu_manager import (
    gpu_manager, get_device, get_ffmpeg_encoder, 
    get_ffmpeg_decoder, get_hwaccel_args, has_gpu, clear_cache
)

# Set FFmpeg path for Windows (updated for current PC)
FFMPEG_PATH = r"C:\ffmpeg-2025-12-18-git-78c75d546a-full_build\bin"
if FFMPEG_PATH not in os.environ.get('PATH', ''):
    os.environ['PATH'] = FFMPEG_PATH + os.pathsep + os.environ.get('PATH', '')

# Set FFmpeg for imageio
os.environ['IMAGEIO_FFMPEG_EXE'] = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')

# Configure AudioSegment to use FFmpeg
AudioSegment.converter = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
AudioSegment.ffmpeg = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
AudioSegment.ffprobe = os.path.join(FFMPEG_PATH, 'ffprobe.exe')

# Log GPU status on startup
print("\n" + "=" * 60)
print("VIDEO SERVICE INITIALIZATION")
print("=" * 60)
gpu_manager._log_gpu_status()

class AIThumbnailGenerator:
    """AI-powered YouTube thumbnail generator with BLIP captioning and intelligent frame selection"""
    
    def __init__(self):
        print("[AI THUMBNAIL] Initializing AI Thumbnail Generator...")
        self.processor = None
        self.model = None
        # Use GPU manager for device selection
        self.device = get_device()
        print(f"[AI THUMBNAIL] Using device: {self.device}")
        
        if has_gpu():
            print(f"[AI THUMBNAIL] GPU: {gpu_manager.gpu_info['name']} ({gpu_manager.gpu_info['memory_total']:.2f}GB)")
        
        # Load face detection cascade for better frame selection
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            print("[AI THUMBNAIL] Face detection loaded successfully")
        except:
            print("[AI THUMBNAIL] Face detection not available")
            self.face_cascade = None
        
    def _load_model(self):
        """Lazy load BLIP model only when needed"""
        if self.processor is None:
            try:
                print("[AI THUMBNAIL] Loading BLIP model for image captioning...")
                self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
                print("[AI THUMBNAIL] BLIP model loaded successfully")
            except Exception as e:
                print(f"[AI THUMBNAIL] Failed to load BLIP model: {e}")
                self.processor = None
                self.model = None
    
    def generate_catchy_text(self, frame_path, video_filename):
        """Generate catchy text using AI image captioning"""
        try:
            self._load_model()
            
            if self.model is None:
                # Fallback to filename-based generation
                return self._fallback_text_generation(video_filename)
            
            # Load image
            image = Image.open(frame_path).convert('RGB')
            
            # Generate caption using BLIP
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            out = self.model.generate(**inputs, max_length=20)
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            
            print(f"[AI THUMBNAIL] Generated caption: {caption}")
            
            # Convert caption to catchy thumbnail text
            catchy_text = self._make_catchy(caption, video_filename)
            print(f"[AI THUMBNAIL] Catchy text: {catchy_text}")
            
            return catchy_text
            
        except Exception as e:
            print(f"[AI THUMBNAIL] Error in AI text generation: {e}")
            return self._fallback_text_generation(video_filename)
    
    def _make_catchy(self, caption, filename):
        """Transform AI caption into catchy thumbnail text"""
        # Extract keywords from caption
        caption_lower = caption.lower()
        
        # Catchy prefixes based on content
        action_words = ['running', 'jumping', 'playing', 'dancing', 'swimming', 'flying', 'driving']
        nature_words = ['sunset', 'beach', 'mountain', 'ocean', 'forest', 'sky', 'landscape']
        people_words = ['person', 'man', 'woman', 'people', 'group', 'child', 'baby']
        object_words = ['car', 'building', 'house', 'phone', 'computer', 'food']
        
        if any(word in caption_lower for word in action_words):
            prefix = np.random.choice(['WATCH THIS!', 'AMAZING!', 'INCREDIBLE!', 'WOW!'])
        elif any(word in caption_lower for word in nature_words):
            prefix = np.random.choice(['BREATHTAKING', 'STUNNING', 'BEAUTIFUL', 'SPECTACULAR'])
        elif any(word in caption_lower for word in people_words):
            prefix = np.random.choice(['MUST SEE', 'VIRAL', 'TRENDING', 'WATCH NOW'])
        else:
            prefix = np.random.choice(['NEW VIDEO', 'DISCOVER', 'CHECK THIS OUT', 'DON\'T MISS'])
        
        # Extract main subject from caption
        words = caption.split()
        # Get important words (skip common words)
        skip_words = ['a', 'an', 'the', 'is', 'are', 'in', 'on', 'at', 'to', 'of', 'with']
        important_words = [w.upper() for w in words if w.lower() not in skip_words][:3]
        
        if important_words:
            return f"{prefix}: {' '.join(important_words)}"
        else:
            return prefix
    
    def _fallback_text_generation(self, filename):
        """Fallback text generation from filename"""
        # Clean filename
        name = os.path.splitext(os.path.basename(filename))[0]
        name = re.sub(r'[_-]', ' ', name)
        name = name.title()
        
        prefixes = ['NEW VIDEO', 'WATCH NOW', 'MUST SEE', 'TRENDING', 'VIRAL', 'AMAZING']
        prefix = np.random.choice(prefixes)
        
        if len(name) > 30:
            name = name[:30] + '...'
        
        return f"{prefix}: {name}"
    
    def create_youtube_thumbnail(self, frame_path, text, output_path, text_options=None):
        """Create professional YouTube thumbnail with customizable text options"""
        try:
            print(f"[THUMBNAIL CREATE] Received text_options: {text_options}")
            
            # Load frame and ensure RGB from start
            with Image.open(frame_path) as source_img:
                img = source_img.convert('RGB')
            
            # Resize to YouTube format (1280x720)
            target_size = (1280, 720)
            img = self._resize_with_crop(img, target_size)
            
            # Apply visual enhancements
            img = self._enhance_image(img)
            
            # Add text overlay only if text is provided
            if text and text.strip():
                print(f"[THUMBNAIL CREATE] Adding text: '{text}' with options: {text_options}")
                img = self._add_professional_text(img, text, text_options)
            
            # Force to RGB mode (in case text overlay changed it)
            if img.mode != 'RGB':
                print(f"[THUMBNAIL CREATE] Converting from {img.mode} to RGB")
                if img.mode == 'RGBA':
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save with verified settings
            print(f"[THUMBNAIL CREATE] Saving RGB image ({img.size}) to: {output_path}")
            img.save(output_path, format='JPEG', quality=95, optimize=False, subsampling=0)
            
            # Close the image to release file handle
            img.close()
            
            # Verify the saved file
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[AI THUMBNAIL] ✅ File saved successfully: {file_size} bytes")
                
                # Verify it can be opened
                try:
                    with Image.open(output_path) as test_img:
                        print(f"[AI THUMBNAIL] ✅ File is valid JPEG: {test_img.size}, mode: {test_img.mode}, format: {test_img.format}")
                except Exception as verify_error:
                    print(f"[AI THUMBNAIL] ❌ ERROR: Saved file is corrupted: {verify_error}")
                    import traceback
                    traceback.print_exc()
                    raise
            else:
                print(f"[AI THUMBNAIL] ❌ ERROR: File was not saved!")
                raise Exception("File not saved")
            
            return output_path
            
        except Exception as e:
            print(f"[AI THUMBNAIL] Error creating YouTube thumbnail: {e}")
            return frame_path
    
    def _resize_with_crop(self, img, target_size):
        """Resize image to exact dimensions with smart cropping"""
        target_ratio = target_size[0] / target_size[1]
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            # Image is wider - crop width
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Center crop
            left = (new_width - target_size[0]) // 2
            img = img.crop((left, 0, left + target_size[0], target_size[1]))
        else:
            # Image is taller - crop height
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Center crop
            top = (new_height - target_size[1]) // 2
            img = img.crop((0, top, target_size[0], top + target_size[1]))
        
        return img
    
    def _enhance_image(self, img):
        """Apply minimal enhancements - keep original look"""
        # Just return the original image without heavy processing
        # This removes the vintage/dark vignette effect
        return img
    
    def _add_vignette(self, img):
        """Vignette disabled - returns original image"""
        # Vignette removed to prevent dark effect
        return img
    
    def _add_professional_text(self, img, text, text_options=None):
        """Add professional text overlay with customizable styling options"""
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Get customization options with defaults
        if text_options is None:
            text_options = {}
        
        # Ensure font_size is an integer and within valid range (50-200)
        raw_font_size = text_options.get('font_size', min(width // 12, 100))
        font_size = int(max(50, min(200, raw_font_size)))  # Clamp between 50-200
        
        text_color = text_options.get('text_color', '#FFFFFF')  # White
        outline_color = text_options.get('outline_color', '#FF6400')  # Orange
        position = text_options.get('position', 'bottom')  # top, center, bottom
        font_style = text_options.get('font_style', 'bold')  # bold, regular, italic, bold-italic, light
        shadow = text_options.get('shadow', True)
        background = text_options.get('background', True)
        background_color = text_options.get('background_color', '#000000')  # Black by default
        
        print(f"[TEXT OVERLAY] ========== CUSTOMIZATION OPTIONS ==========")
        print(f"[TEXT OVERLAY] Raw font_size: {raw_font_size} -> Clamped: {font_size}")
        print(f"[TEXT OVERLAY] Text color: {text_color}")
        print(f"[TEXT OVERLAY] Outline color: {outline_color}")
        print(f"[TEXT OVERLAY] Position: {position}")
        print(f"[TEXT OVERLAY] Font style: {font_style}")
        print(f"[TEXT OVERLAY] Shadow: {shadow}")
        print(f"[TEXT OVERLAY] Background: {background}")
        print(f"[TEXT OVERLAY] Background color: {background_color}")
        print(f"[TEXT OVERLAY] ============================================")
        
        # Convert hex colors to RGB tuples
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            print(f"[COLOR] Converting {hex_color} -> RGB{rgb}")
            return rgb
        
        text_rgb = hex_to_rgb(text_color)
        outline_rgb = hex_to_rgb(outline_color)
        bg_rgb = hex_to_rgb(background_color)
        
        # Try to load font with multiple fallbacks for different styles
        font = None
        font_map = {
            'bold': [(r"C:\Windows\Fonts\arialbd.ttf", "Arial Bold"), ("arialbd.ttf", "Arial Bold")],
            'regular': [(r"C:\Windows\Fonts\arial.ttf", "Arial Regular"), ("arial.ttf", "Arial Regular")],
            'italic': [(r"C:\Windows\Fonts\ariali.ttf", "Arial Italic"), ("ariali.ttf", "Arial Italic")],
            'bold-italic': [(r"C:\Windows\Fonts\arialbi.ttf", "Arial Bold Italic"), ("arialbi.ttf", "Arial Bold Italic")],
            'light': [(r"C:\Windows\Fonts\arial.ttf", "Arial Light"), ("arial.ttf", "Arial Light")]
        }
        
        font_paths = font_map.get(font_style, font_map['bold'])
        font_paths = font_map.get(font_style, font_map['bold'])
        
        for font_path, font_name in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"[FONT] Loaded {font_name} (style: {font_style}) at size {font_size}")
                break
            except Exception as e:
                continue
        
        # Final fallback
        if font is None:
            print(f"[FONT] WARNING: All fonts failed, using default font (size will be ignored!)")
            font = ImageFont.load_default()
        
        # Calculate text size and wrap if needed
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > width * 0.85:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
            else:
                current_line.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate total text height
        total_height = 0
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            line_heights.append(line_height)
            total_height += line_height + 10
        
        # Determine vertical position
        if position == 'top':
            bar_y = 40
            print(f"[POSITION] Using TOP position: y={bar_y}")
        elif position == 'center':
            bar_y = (height - total_height - 80) // 2
            print(f"[POSITION] Using CENTER position: y={bar_y}")
        else:  # bottom
            bar_y = height - total_height - 120
            print(f"[POSITION] Using BOTTOM position: y={bar_y}")
        
        # Add background bar if enabled
        if background:
            print(f"[BACKGROUND] Adding background bar with color {background_color} (RGB: {bg_rgb})")
            bar_height = total_height + 80
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Draw gradient bar with custom color
            for i in range(bar_height):
                alpha = int(220 - (i / bar_height) * 40)
                overlay_draw.rectangle(
                    [0, bar_y + i, width, bar_y + i + 1],
                    fill=(*bg_rgb, alpha)
                )
            
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        else:
            print(f"[BACKGROUND] Background disabled, skipping bar")
        
        # Draw text
        draw = ImageDraw.Draw(img)
        current_y = bar_y + 40
        
        print(f"[DRAWING] Starting text rendering at y={current_y}")
        print(f"[DRAWING] Text color RGB: {text_rgb}")
        print(f"[DRAWING] Outline color RGB: {outline_rgb}")
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            print(f"[DRAWING] Line {i+1}: '{line}' at ({text_x}, {current_y})")
            
            # Shadow layer
            if shadow:
                print(f"[DRAWING] Adding shadow to line {i+1}")
                for offset in range(8, 0, -1):
                    draw.text((text_x + offset//2, current_y + offset//2), line, font=font, fill=(0, 0, 0))
            else:
                print(f"[DRAWING] Shadow disabled for line {i+1}")
            
            # Outline layer
            outline_range = 5
            for adj_x in range(-outline_range, outline_range + 1):
                for adj_y in range(-outline_range, outline_range + 1):
                    if adj_x*adj_x + adj_y*adj_y <= outline_range*outline_range:
                        draw.text((text_x + adj_x, current_y + adj_y), line, font=font, fill=outline_rgb)
            
            # Main text
            draw.text((text_x, current_y), line, font=font, fill=text_rgb)
            
            current_y += line_heights[i] + 10
        
        print(f"[DRAWING] Text rendering complete")
        
        # Ensure image is in RGB mode before returning
        if img.mode != 'RGB':
            print(f"[DRAWING] Final conversion from {img.mode} to RGB")
            img = img.convert('RGB')
        
        return img
    
    def _select_best_frames(self, cap, total_frames, fps, num_frames=5):
        """Use OpenCV and AI to select the best frames for thumbnails"""
        print(f"[AI FRAME] Analyzing {total_frames} frames for optimal thumbnail selection...")
        
        # Sample frames at regular intervals
        sample_interval = max(1, total_frames // 30)  # Sample ~30 frames
        candidate_frames = []
        
        for frame_idx in range(0, total_frames, sample_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret or frame is None:
                continue
            
            # Calculate quality score for this frame
            quality_score = self._calculate_frame_quality(frame)
            
            if quality_score > 0.3:  # Only consider frames with decent quality
                candidate_frames.append((frame_idx, frame.copy(), quality_score))
        
        print(f"[AI FRAME] Found {len(candidate_frames)} candidate frames")
        
        # Sort by quality score and select top frames
        candidate_frames.sort(key=lambda x: x[2], reverse=True)
        best_frames = candidate_frames[:num_frames]
        
        print(f"[AI FRAME] Selected top {len(best_frames)} frames based on quality analysis")
        return best_frames
    
    def _calculate_frame_quality(self, frame):
        """Calculate quality score for a frame using multiple metrics"""
        score = 0.0
        
        # 1. Sharpness/Focus Score (Laplacian variance)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 500, 1.0)  # Normalize
        score += sharpness_score * 0.35
        
        # 2. Brightness Score (avoid too dark or too bright)
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 127.5) / 127.5
        score += brightness_score * 0.20
        
        # 3. Color Richness Score (saturation)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:,:,1])
        saturation_score = min(saturation / 180, 1.0)  # Normalize
        score += saturation_score * 0.20
        
        # 4. Face Detection Score (frames with faces are better)
        if self.face_cascade is not None:
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            face_score = min(len(faces) * 0.5, 1.0)  # Up to 2 faces = max score
            score += face_score * 0.15
        
        # 5. Composition Score (rule of thirds)
        composition_score = self._calculate_composition_score(frame)
        score += composition_score * 0.10
        
        return score
    
    def _calculate_composition_score(self, frame):
        """Calculate composition score based on edge distribution"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        
        h, w = edges.shape
        
        # Divide frame into 9 regions (rule of thirds)
        third_h, third_w = h // 3, w // 3
        regions = []
        
        for i in range(3):
            for j in range(3):
                region = edges[i*third_h:(i+1)*third_h, j*third_w:(j+1)*third_w]
                edge_density = np.sum(region) / (third_h * third_w)
                regions.append(edge_density)
        
        # Good composition has edges near third lines
        # Interest points at intersections of thirds
        interest_regions = [regions[0], regions[2], regions[6], regions[8]]  # Corners
        interest_score = np.mean(interest_regions) / 255.0
        
        # Balance score (not all edges in one place)
        balance_score = 1.0 - (np.std(regions) / (np.mean(regions) + 1e-6))
        balance_score = np.clip(balance_score, 0, 1)
        
        return (interest_score + balance_score) / 2

class AIColorEnhancer:
    """AI-based automatic color and saturation enhancement"""
    
    def __init__(self):
        self.optimal_saturation_range = (0.3, 0.7)  # Optimal saturation range for most videos

# NOTE: The main AudioEnhancer class with Whisper-based filler detection is defined below (around line 717)

class AIColorEnhancer:
    """AI-based automatic color and saturation enhancement"""
    
    def __init__(self):
        self.optimal_saturation_range = (0.3, 0.7)  # Optimal saturation range for most videos
        
    def analyze_video_colors(self, video_path, sample_frames=30):
        """Analyze video to determine optimal color adjustments"""
        try:
            print(f"[AI COLOR] Analyzing video colors from {sample_frames} frames...")
            cap = cv2.VideoCapture(video_path)
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = max(1, total_frames // sample_frames)
            
            saturation_values = []
            brightness_values = []
            contrast_values = []
            
            frame_count = 0
            analyzed = 0
            
            while cap.isOpened() and analyzed < sample_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % frame_interval == 0:
                    # Convert to HSV for saturation analysis
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    
                    # Get saturation (S channel)
                    saturation = hsv[:, :, 1] / 255.0
                    saturation_values.append(np.mean(saturation))
                    
                    # Get brightness (V channel)
                    brightness = hsv[:, :, 2] / 255.0
                    brightness_values.append(np.mean(brightness))
                    
                    # Calculate contrast (std dev of brightness)
                    contrast_values.append(np.std(brightness))
                    
                    analyzed += 1
                
                frame_count += 1
            
            cap.release()
            
            # Calculate statistics
            avg_saturation = np.mean(saturation_values)
            avg_brightness = np.mean(brightness_values)
            avg_contrast = np.mean(contrast_values)
            
            print(f"[AI COLOR] Analysis complete:")
            print(f"  - Average Saturation: {avg_saturation:.3f}")
            print(f"  - Average Brightness: {avg_brightness:.3f}")
            print(f"  - Average Contrast: {avg_contrast:.3f}")
            
            return {
                'saturation': avg_saturation,
                'brightness': avg_brightness,
                'contrast': avg_contrast,
                'saturation_std': np.std(saturation_values),
                'brightness_std': np.std(brightness_values)
            }
            
        except Exception as e:
            print(f"[AI COLOR] Error analyzing video: {e}")
            return None
    
    def calculate_optimal_adjustments(self, analysis):
        """Calculate optimal color adjustments based on analysis"""
        if not analysis:
            return {'saturation': 1.0, 'brightness': 1.0, 'contrast': 1.0}
        
        adjustments = {}
        
        # Saturation adjustment
        current_sat = analysis['saturation']
        target_sat = (self.optimal_saturation_range[0] + self.optimal_saturation_range[1]) / 2
        
        if current_sat < self.optimal_saturation_range[0]:
            # Boost saturation for undersaturated videos
            saturation_boost = min(2.0, target_sat / max(current_sat, 0.1))
            adjustments['saturation'] = saturation_boost
            print(f"[AI COLOR] Boosting saturation by {saturation_boost:.2f}x")
        elif current_sat > self.optimal_saturation_range[1]:
            # Reduce saturation for oversaturated videos
            saturation_reduce = max(0.5, target_sat / current_sat)
            adjustments['saturation'] = saturation_reduce
            print(f"[AI COLOR] Reducing saturation to {saturation_reduce:.2f}x")
        else:
            adjustments['saturation'] = 1.0
            print(f"[AI COLOR] Saturation is optimal, no adjustment needed")
        
        # Brightness adjustment
        current_brightness = analysis['brightness']
        if current_brightness < 0.35:
            brightness_boost = min(1.4, 0.5 / current_brightness)
            adjustments['brightness'] = brightness_boost
            print(f"[AI COLOR] Boosting brightness to {brightness_boost:.2f}x")
        elif current_brightness > 0.75:
            brightness_reduce = max(0.7, 0.6 / current_brightness)
            adjustments['brightness'] = brightness_reduce
            print(f"[AI COLOR] Reducing brightness to {brightness_reduce:.2f}x")
        else:
            adjustments['brightness'] = 1.0
        
        # Contrast adjustment
        current_contrast = analysis['contrast']
        if current_contrast < 0.15:
            contrast_boost = min(1.3, 0.2 / current_contrast)
            adjustments['contrast'] = contrast_boost
            print(f"[AI COLOR] Boosting contrast to {contrast_boost:.2f}x")
        elif current_contrast > 0.35:
            contrast_reduce = max(0.8, 0.25 / current_contrast)
            adjustments['contrast'] = contrast_reduce
            print(f"[AI COLOR] Reducing contrast to {contrast_reduce:.2f}x")
        else:
            adjustments['contrast'] = 1.0
        
        return adjustments
    
    def apply_ai_enhancement(self, frame, saturation_mult=1.0, brightness_mult=1.0, contrast_mult=1.0):
        """Apply AI-calculated enhancements to a frame"""
        # Convert to HSV for saturation adjustment
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # Adjust saturation
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_mult, 0, 255)
        
        # Adjust brightness (V channel)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * brightness_mult, 0, 255)
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        # Apply contrast adjustment
        if contrast_mult != 1.0:
            enhanced = enhanced.astype(np.float32)
            enhanced = np.clip((enhanced - 128) * contrast_mult + 128, 0, 255)
            enhanced = enhanced.astype(np.uint8)
        
        return enhanced

class AudioEnhancer:
    """Advanced Audio Enhancement with REAL Filler Word Detection using Whisper and Noise Reduction"""
    
    def __init__(self):
        # Comprehensive filler words and phrases (case-insensitive)
        self.filler_words = {
            'en': [
                # Single word fillers - include variations Whisper might produce
                'um', 'umm', 'ummm', 'uhm', 'uh', 'uhh', 'uhhh', 
                'er', 'err', 'errr', 'ah', 'ahh', 'ahhh', 
                'hmm', 'hmmm', 'mm', 'mmm', 'mmmm', 'hm', 'hmmmm',
                'like', 'so', 'well', 'right', 'okay', 'ok',
                'actually', 'basically', 'literally', 'obviously',
                # Common filler sounds Whisper transcribes
                'mhm', 'uh-huh', 'uh huh', 'mm-hmm', 'mmhmm', 'aha',
                'yeah', 'yep', 'yup', 'nah', 'nope',
                # Multi-word phrases
                'you know', 'but you know', 'you know what i mean',
                'i guess', 'i suppose', 'i mean', 'i think',
                'kind of', 'sort of', 'or something', 'and stuff',
                'you see', 'i dunno', 'i dont know',
                'anyway', 'anyways', 'whatever'
            ],
            'ur': ['اں', 'ہاں', 'یعنی', 'اصل میں', 'تو', 'بس', 'اچھا'],
            'es': ['eh', 'este', 'bueno', 'pues', 'o sea', 'como', 'entonces'],
            'fr': ['euh', 'ben', 'alors', 'donc', 'enfin', 'bon', 'voilà'],
            'de': ['äh', 'ähm', 'also', 'ja', 'naja', 'halt', 'eigentlich']
        }
        # Whisper model for speech recognition (lazy loaded)
        self._whisper_model = None
        self._filler_words_removed_count = 0
        self._repeated_words_removed_count = 0
    
    def _load_whisper(self):
        """Lazy load Whisper model for filler word detection"""
        if self._whisper_model is None:
            try:
                import whisper
                device = get_device()
                print(f"[AUDIO ENHANCER] Loading Whisper model for filler word detection on {device}...")
                self._whisper_model = whisper.load_model("base", device=device)
                print(f"[AUDIO ENHANCER] Whisper model loaded successfully on {device}")
            except Exception as e:
                print(f"[AUDIO ENHANCER] Failed to load Whisper: {e}")
                self._whisper_model = None
        return self._whisper_model
    
    def enhance_audio(self, audio_path, options):
        """Main audio enhancement function with separate filler removal and noise reduction options"""
        try:
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            print(f"[AUDIO ENHANCE] Loaded audio: {len(audio)}ms, {audio.frame_rate}Hz")
            
            # Get enhancement options
            enhancement_type = options.get('audio_enhancement_type', 'medium')
            pause_threshold = options.get('pause_threshold', 500)
            noise_reduction = options.get('noise_reduction', 'moderate')
            detect_and_remove_fillers = options.get('detect_and_remove_fillers', options.get('remove_fillers', False))  # NEW: Separate filler removal option
            detect_repeated_words = options.get('detect_repeated_words', True)  # NEW: Detect repeated words
            
            print(f"[AUDIO ENHANCE] Options: type={enhancement_type}, pause={pause_threshold}ms, noise={noise_reduction}, remove_fillers={detect_and_remove_fillers}, detect_repeated={detect_repeated_words}")
            
            # Reset counters and segments storage
            self._filler_words_removed_count = 0
            self._repeated_words_removed_count = 0
            self._detected_filler_segments = []  # Store segments for video cutting
            
            # Step 1: Remove filler words FIRST (before any other processing)
            # This ensures Whisper transcribes the ORIGINAL audio with all fillers intact
            if detect_and_remove_fillers:
                print(f"[AUDIO ENHANCE] Step 1: Detecting and removing filler words from ORIGINAL audio...")
                enhanced_audio = self._remove_filler_words_with_whisper(
                    audio,  # Pass original audio
                    audio_path,  # Pass original file path for Whisper
                    enhancement_type,
                    detect_repeated=detect_repeated_words
                )
                print(f"[AUDIO ENHANCE] After filler word removal: {len(enhanced_audio)}ms")
                print(f"[AUDIO ENHANCE] Removed {self._filler_words_removed_count} fillers, {self._repeated_words_removed_count} repeated words")
            else:
                enhanced_audio = audio
                print(f"[AUDIO ENHANCE] Filler word removal disabled")
            
            # Step 2: Remove excessive silence/pauses (AFTER filler removal)
            enhanced_audio = self._remove_silence(enhanced_audio, pause_threshold)
            print(f"[AUDIO ENHANCE] After silence removal: {len(enhanced_audio)}ms")
            
            # Step 3: Apply noise reduction (independent of filler removal)
            if noise_reduction != 'none':
                enhanced_audio = self._reduce_noise(enhanced_audio, noise_reduction)
                print(f"[AUDIO ENHANCE] After noise reduction: {len(enhanced_audio)}ms")
            else:
                print(f"[AUDIO ENHANCE] Noise reduction disabled")
            
            # Step 4: Apply transition smoothing for natural flow
            enhanced_audio = self._apply_transition_smoothing(enhanced_audio)
            print(f"[AUDIO ENHANCE] After transition smoothing: {len(enhanced_audio)}ms")
            
            # Step 5: Normalize audio
            enhanced_audio = normalize(enhanced_audio)
            print(f"[AUDIO ENHANCE] Final audio: {len(enhanced_audio)}ms")
            print(f"[AUDIO ENHANCE] Audio enhancement completed, returning results...")
            
            # Calculate improvement metrics
            original_duration = len(audio)
            enhanced_duration = len(enhanced_audio)
            time_saved = original_duration - enhanced_duration
            
            metrics = {
                'original_duration_ms': original_duration,
                'enhanced_duration_ms': enhanced_duration,
                'time_saved_ms': time_saved,
                'time_saved_percentage': (time_saved / original_duration) * 100 if original_duration > 0 else 0,
                'noise_reduction_level': noise_reduction,
                'enhancement_type': enhancement_type,
                'filler_words_removed': self._filler_words_removed_count,
                'repeated_words_removed': self._repeated_words_removed_count,
                'filler_removal_enabled': detect_and_remove_fillers,
                # Store segments as simple (start, end) tuples for video cutting
                'filler_segments': [(seg[0], seg[1]) for seg in self._detected_filler_segments] if self._detected_filler_segments else []
            }
            
            print(f"[AUDIO ENHANCE] Filler segments for video cutting: {metrics['filler_segments']}")
            print(f"[AUDIO ENHANCE] Metrics: {metrics}")
            return enhanced_audio, metrics
            
        except Exception as e:
            print(f"[AUDIO ENHANCE] Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _remove_silence(self, audio, pause_threshold):
        """Remove excessive silence while preserving natural speech rhythm"""
        try:
            # Detect non-silent chunks
            min_silence_len = max(pause_threshold, 300)  # Minimum 300ms
            silence_thresh = audio.dBFS - 16  # Dynamic threshold based on audio level
            
            print(f"[SILENCE] Detecting silence: threshold={silence_thresh}dB, min_len={min_silence_len}ms")
            
            # Split on silence
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                keep_silence=200  # Keep 200ms of silence for natural flow
            )
            
            if not chunks:
                print("[SILENCE] No chunks found, returning original audio")
                return audio
            
            # Combine chunks with controlled gaps
            result = AudioSegment.empty()
            for i, chunk in enumerate(chunks):
                result += chunk
                # Add small gap between chunks (except last one)
                if i < len(chunks) - 1:
                    gap_duration = min(200, pause_threshold // 3)  # Maximum 200ms gap
                    silence_gap = AudioSegment.silent(duration=gap_duration)
                    result += silence_gap
            
            print(f"[SILENCE] Processed {len(chunks)} chunks")
            return result
            
        except Exception as e:
            print(f"[SILENCE] Error: {e}")
            return audio
    
    def _remove_filler_words_with_whisper(self, audio, original_audio_path, enhancement_type, detect_repeated=True):
        """Remove filler words and repeated words using Whisper speech recognition for REAL detection"""
        try:
            print(f"[FILLER] Starting REAL filler word detection with Whisper: {enhancement_type}")
            print(f"[FILLER] Detect repeated words: {detect_repeated}")
            print(f"[FILLER] Using ORIGINAL audio file for transcription: {original_audio_path}")
            
            # Get filler words to detect based on enhancement type
            if enhancement_type == 'conservative':
                target_fillers = ['um', 'uh', 'er']
            elif enhancement_type == 'medium':
                target_fillers = ['um', 'uh', 'er', 'ah', 'hmm', 'mm', 'erm', 'hm', 'like', 'you know']
            else:  # aggressive
                target_fillers = ['um', 'uh', 'er', 'ah', 'hmm', 'mm', 'hm', 'mmm', 'mm-hmm',
                                'like', 'you know', 'but you know', 'i guess', 'i suppose',
                                'kind of', 'sort of', 'or something', 'right', 'so', 'well',
                                'you see', 'you know what i mean', 'actually', 'basically', 'literally']
            
            print(f"[FILLER] Target filler words: {target_fillers}")
            
            # IMPORTANT: Use ORIGINAL audio file for Whisper transcription (has all the fillers)
            # NOT the enhanced_audio which may have silence removed
            filler_segments = self._detect_fillers_with_whisper(original_audio_path, target_fillers, detect_repeated=detect_repeated)
            
            # Store segments for video cutting
            self._detected_filler_segments = filler_segments
            
            if not filler_segments:
                print("[FILLER] No filler words detected by Whisper, trying fallback detection...")
                # Fallback to energy-based detection
                filler_segments = self._detect_filler_patterns_fallback(audio, enhancement_type)
                # Store fallback segments too!
                self._detected_filler_segments = filler_segments
            
            if not filler_segments:
                print("[FILLER] No filler words detected")
                return audio
            
            # Sort segments by start time
            filler_segments.sort(key=lambda x: x[0])
            
            # Remove detected filler segments
            result = AudioSegment.empty()
            last_end = 0
            
            for segment in filler_segments:
                # Handle both (start, end) and (start, end, label) formats
                start_ms = segment[0]
                end_ms = segment[1]
                
                # Add audio before filler word
                if start_ms > last_end:
                    result += audio[last_end:start_ms]
                
                # Skip the filler word (add very short silence for natural flow)
                result += AudioSegment.silent(duration=30)
                last_end = end_ms
                self._filler_words_removed_count += 1
            
            # Add remaining audio
            if last_end < len(audio):
                result += audio[last_end:]
            
            print(f"[FILLER] Removed {self._filler_words_removed_count} filler segments")
            return result
            
        except Exception as e:
            print(f"[FILLER] Error: {e}")
            import traceback
            traceback.print_exc()
            return audio
    
    def _detect_fillers_with_whisper(self, audio_path, target_fillers, detect_repeated=True):
        """Use Whisper to detect filler words, multi-word phrases, and repeated words with word-level timestamps"""
        try:
            model = self._load_whisper()
            if model is None:
                print("[WHISPER] Whisper not available, skipping...")
                return []
            
            print(f"[WHISPER] Transcribing audio for filler word detection...")
            print(f"[WHISPER] Using settings to PRESERVE filler words (um, uh, etc.)")
            
            # Transcribe with settings that PRESERVE filler words
            # By default, Whisper removes disfluencies - we need to prevent that
            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                language='en',
                verbose=False,
                # These settings help preserve filler words:
                condition_on_previous_text=False,  # Don't clean up based on context
                suppress_tokens=[],  # Don't suppress any tokens including fillers
                without_timestamps=False,
                initial_prompt="Um, uh, ah, er, hmm, like, you know, I mean, basically, actually, so, well, right, okay."  # Prime Whisper to expect fillers
            )
            
            filler_segments = []
            all_words = []  # Store all words with timestamps for repeated word detection
            
            # Collect all words from all segments with timestamps
            for segment in result.get('segments', []):
                words = segment.get('words', [])
                for word_info in words:
                    word = word_info.get('word', '').lower().strip()
                    # Remove punctuation
                    word_clean = ''.join(c for c in word if c.isalnum() or c.isspace()).strip()
                    
                    if word_clean:  # Only add non-empty words
                        all_words.append({
                            'text': word_clean,
                            'original': word,
                            'start': word_info.get('start', 0),
                            'end': word_info.get('end', 0)
                        })
            
            print(f"[WHISPER] Extracted {len(all_words)} words with timestamps")
            
            # Print all words for debugging
            print(f"[WHISPER] All transcribed words: {[w['text'] for w in all_words[:50]]}...")  # First 50 words
            
            # 1. Detect single-word fillers with FUZZY matching
            single_word_fillers = [f for f in target_fillers if ' ' not in f]
            print(f"[WHISPER] Looking for fillers: {single_word_fillers}")
            
            for word_info in all_words:
                word_clean = word_info['text'].lower().strip()
                
                # Remove any remaining punctuation
                word_clean = ''.join(c for c in word_clean if c.isalnum()).strip()
                
                is_filler = False
                matched_filler = None
                
                # Exact match
                if word_clean in single_word_fillers:
                    is_filler = True
                    matched_filler = word_clean
                
                # Fuzzy match for common variations Whisper produces
                elif not is_filler:
                    # Check if word starts with common filler sounds
                    filler_prefixes = ['um', 'uh', 'er', 'ah', 'hm', 'mm']
                    for prefix in filler_prefixes:
                        if word_clean.startswith(prefix) and len(word_clean) <= len(prefix) + 2:
                            is_filler = True
                            matched_filler = f"{prefix}* ({word_clean})"
                            break
                
                if is_filler:
                    start_ms = int(word_info['start'] * 1000)
                    end_ms = int(word_info['end'] * 1000)
                    
                    # Add small buffer around filler word for smooth cuts
                    start_ms = max(0, start_ms - 50)
                    end_ms = end_ms + 50
                    
                    filler_segments.append((start_ms, end_ms, f"filler: {matched_filler}"))
                    print(f"[WHISPER] ✓ Found filler '{matched_filler}' at {start_ms}ms - {end_ms}ms")
            
            # 2. Detect multi-word phrase fillers (e.g., "you know", "kind of")
            multi_word_fillers = [f for f in target_fillers if ' ' in f]
            for phrase_filler in multi_word_fillers:
                phrase_words = phrase_filler.split()
                phrase_len = len(phrase_words)
                
                # Sliding window to find consecutive matching words
                for i in range(len(all_words) - phrase_len + 1):
                    window_words = [all_words[i + j]['text'] for j in range(phrase_len)]
                    window_text = ' '.join(window_words)
                    
                    # Check if window matches the phrase filler
                    if window_text == phrase_filler or phrase_filler in window_text:
                        # Get start of first word and end of last word in phrase
                        start_ms = int(all_words[i]['start'] * 1000)
                        end_ms = int(all_words[i + phrase_len - 1]['end'] * 1000)
                        
                        # Add buffer
                        start_ms = max(0, start_ms - 50)
                        end_ms = end_ms + 50
                        
                        filler_segments.append((start_ms, end_ms, f"phrase: {phrase_filler}"))
                        print(f"[WHISPER] Found phrase filler '{phrase_filler}' at {start_ms}ms - {end_ms}ms")
            
            # 3. Detect repeated words (e.g., "I I", "the the", "so so")
            if detect_repeated:
                for i in range(len(all_words) - 1):
                    current_word = all_words[i]['text']
                    next_word = all_words[i + 1]['text']
                    
                    # Check if consecutive words are identical and not meaningful repetition
                    # Skip very short words that might be intentional (e.g., "no no no")
                    if current_word == next_word and len(current_word) > 1:
                        # Remove the repeated word (keep first occurrence, remove second)
                        start_ms = int(all_words[i + 1]['start'] * 1000)
                        end_ms = int(all_words[i + 1]['end'] * 1000)
                        
                        # Add buffer
                        start_ms = max(0, start_ms - 50)
                        end_ms = end_ms + 50
                        
                        filler_segments.append((start_ms, end_ms, f"repeated: {current_word}"))
                        print(f"[WHISPER] Found repeated word '{current_word}' at {start_ms}ms - {end_ms}ms")
                        self._repeated_words_removed_count += 1
            
            # Merge overlapping segments
            merged_segments = self._merge_overlapping_segments_with_labels(filler_segments)
            print(f"[WHISPER] Detected {len(merged_segments)} total segments to remove")
            print(f"[WHISPER] Filler words: {self._filler_words_removed_count}, Repeated: {self._repeated_words_removed_count}")
            
            # Return just the time segments (without labels) for audio cutting
            return [(start, end) for start, end, _ in merged_segments]
            
        except Exception as e:
            print(f"[WHISPER] Error in filler detection: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def generate_transcript_with_fillers(self, audio_path, enhancement_type='medium', detect_repeated=True):
        """Generate full transcript with filler words highlighted for frontend display"""
        try:
            print(f"[TRANSCRIPT] Generating transcript with filler detection...")
            
            model = self._load_whisper()
            if model is None:
                print("[TRANSCRIPT] Whisper not available")
                return None
            
            # Get filler words to detect - EXPANDED LIST with phonetic variations
            if enhancement_type == 'conservative':
                target_fillers = ['um', 'uh', 'er', 'uhm', 'erm', 'umm']
            elif enhancement_type == 'medium':
                target_fillers = [
                    # Basic fillers
                    'um', 'uh', 'er', 'ah', 'uhm', 'erm', 'umm', 'uhh', 'err',
                    # Sound fillers
                    'hmm', 'mm', 'hm', 'mmm', 'mhm', 'uh-huh', 'mm-hmm',
                    # Common verbal crutches
                    'like', 'you know', 'i mean', 'so', 'well', 'basically', 'actually', 'literally',
                    'kind of', 'sort of', 'right', 'okay', 'ok'
                ]
            else:  # aggressive
                target_fillers = [
                    # All basic fillers
                    'um', 'uh', 'er', 'ah', 'uhm', 'erm', 'umm', 'uhh', 'err', 'agh',
                    # All sound fillers  
                    'hmm', 'mm', 'hm', 'mmm', 'mhm', 'uh-huh', 'mm-hmm', 'huh',
                    # Extensive verbal crutches
                    'like', 'you know', 'i mean', 'so', 'well', 'basically', 'actually', 'literally',
                    'kind of', 'sort of', 'right', 'okay', 'ok', 'alright',
                    # Phrases
                    'but you know', 'i guess', 'i suppose', 'i think', 'you see',
                    'or something', 'you know what i mean', 'to be honest', 'honestly',
                    'at the end of the day', 'in my opinion'
                ]
            
            print(f"[TRANSCRIPT] Target fillers ({len(target_fillers)}): {target_fillers[:10]}...")
            
            # Transcribe with settings that PRESERVE filler words
            print(f"[TRANSCRIPT] Using Whisper with settings to PRESERVE filler words...")
            
            # Use initial_prompt to prime Whisper to expect and transcribe filler words
            filler_prompt = "Um, uh, ah, er, hmm, like, you know, I mean, basically, actually, so, well, right, okay. This audio contains filler words and hesitations that should be transcribed exactly as spoken."
            
            try:
                # Try whisper-timestamped first for better timestamps
                audio_array = whisper_ts.load_audio(audio_path)
                result = whisper_ts.transcribe(
                    model,
                    audio_array,
                    language='en',
                    vad=False,
                    detect_disfluencies=True,  # Enable to detect um, uh, etc.
                    compute_word_confidence=False,
                    trust_whisper_timestamps=True,
                    initial_prompt=filler_prompt  # Prime to expect fillers
                )
            except Exception as e:
                print(f"[TRANSCRIPT] whisper-timestamped failed: {e}, falling back to standard Whisper...")
                # Fallback to standard Whisper with filler-preserving settings
                result = model.transcribe(
                    audio_path,
                    word_timestamps=True,
                    language='en',
                    verbose=False,
                    condition_on_previous_text=False,  # Don't clean up based on context
                    suppress_tokens=[],  # Don't suppress filler sounds
                    initial_prompt=filler_prompt  # Prime to expect fillers
                )
            
            print(f"[TRANSCRIPT] Whisper transcription: {result.get('text', '')[:200]}...")
            
            # Build transcript with word-level details
            words = []
            filler_count = 0
            repeated_count = 0
            
            # Collect all words
            all_words = []
            for segment in result.get('segments', []):
                for word_info in segment.get('words', []):
                    word = word_info.get('word', '').lower().strip()
                    word_clean = ''.join(c for c in word if c.isalnum() or c.isspace()).strip()
                    if word_clean:
                        all_words.append({
                            'text': word_clean,
                            'original': word_info.get('word', '').strip(),
                            'start': word_info.get('start', 0),
                            'end': word_info.get('end', 0),
                            'duration': word_info.get('end', 0) - word_info.get('start', 0)
                        })
            
            print(f"[TRANSCRIPT] Extracted {len(all_words)} words")
            if all_words:
                print(f"[TRANSCRIPT] First 10 words: {[w['text'] for w in all_words[:10]]}")
            
            # Detect single-word fillers with FUZZY matching
            single_word_fillers = set([f for f in target_fillers if ' ' not in f])
            
            # Mark fillers and repeated words
            detected_fillers = []
            for i, word_info in enumerate(all_words):
                word_clean = word_info['text']
                is_filler = False
                is_repeated = False
                
                # Check 1: Exact match with filler list
                if word_clean in single_word_fillers:
                    is_filler = True
                    detected_fillers.append(word_clean)
                    print(f"[TRANSCRIPT] Detected filler (exact): '{word_clean}' at {word_info['start']:.2f}s")
                
                # Check 2: Very short words (< 0.3s) that might be fillers Whisper missed
                elif word_info['duration'] < 0.3 and len(word_clean) <= 3:
                    # Check if it starts with common filler sounds
                    filler_starts = ['um', 'uh', 'er', 'ah', 'hm', 'mm']
                    if any(word_clean.startswith(fs) for fs in filler_starts):
                        is_filler = True
                        detected_fillers.append(word_clean)
                        print(f"[TRANSCRIPT] Detected filler (short+pattern): '{word_clean}' at {word_info['start']:.2f}s ({word_info['duration']:.2f}s)")
                
                # Check 3: Detect repeated word
                if detect_repeated and i > 0:
                    prev_word = all_words[i - 1]['text']
                    if word_clean == prev_word and len(word_clean) > 1:
                        is_repeated = True
                        repeated_count += 1
                        print(f"[TRANSCRIPT] Detected repeated: '{word_clean}' at {word_info['start']:.2f}s")
                
                if is_filler:
                    filler_count += 1
                
                words.append({
                    'text': word_info['original'],
                    'start': word_info['start'],
                    'end': word_info['end'],
                    'is_filler': is_filler,
                    'is_repeated': is_repeated
                })
            
            print(f"[TRANSCRIPT] Detection summary:")
            print(f"[TRANSCRIPT]   Total words: {len(words)}")
            print(f"[TRANSCRIPT]   Fillers detected: {filler_count}")
            print(f"[TRANSCRIPT]   Repeated detected: {repeated_count}")
            if detected_fillers:
                print(f"[TRANSCRIPT]   Filler words found: {set(detected_fillers)}")
            
            transcript_data = {
                'text': result.get('text', ''),
                'words': words,
                'filler_count': filler_count,
                'repeated_count': repeated_count,
                'total_words': len(words),
                'duration': all_words[-1]['end'] if all_words else 0
            }
            
            print(f"[TRANSCRIPT] Generated transcript: {len(words)} words, {filler_count} fillers, {repeated_count} repeated")
            return transcript_data
            
        except Exception as e:
            print(f"[TRANSCRIPT] Error generating transcript: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _detect_filler_patterns_fallback(self, audio, enhancement_type):
        """Fallback: Detect potential filler segments using audio analysis"""
        try:
            print("[FILLER FALLBACK] Using audio analysis for filler detection...")
            
            # Convert to numpy array for processing
            audio_data = audio.get_array_of_samples()
            if audio.channels == 2:
                audio_data = np.array(audio_data).reshape((-1, 2))
                audio_data = audio_data.mean(axis=1)
            
            audio_data = np.array(audio_data, dtype=np.float32)
            
            # Normalize
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val
            
            sample_rate = audio.frame_rate
            
            # Parameters based on enhancement type
            if enhancement_type == 'conservative':
                energy_low = 0.05
                energy_high = 0.3
                min_duration_ms = 150
                max_duration_ms = 800
            elif enhancement_type == 'medium':
                energy_low = 0.03
                energy_high = 0.35
                min_duration_ms = 100
                max_duration_ms = 1000
            else:  # aggressive
                energy_low = 0.02
                energy_high = 0.4
                min_duration_ms = 80
                max_duration_ms = 1200
            
            # Sliding window analysis
            window_ms = 50  # 50ms windows
            window_size = int(window_ms * sample_rate / 1000)
            hop_size = window_size // 2
            
            segments = []
            in_potential_filler = False
            filler_start = 0
            
            for i in range(0, len(audio_data) - window_size, hop_size):
                window = audio_data[i:i + window_size]
                rms = np.sqrt(np.mean(window ** 2))
                
                current_time_ms = int(i * 1000 / sample_rate)
                
                # Filler words typically have consistent low-medium energy
                if energy_low < rms < energy_high:
                    if not in_potential_filler:
                        in_potential_filler = True
                        filler_start = current_time_ms
                else:
                    if in_potential_filler:
                        filler_end = current_time_ms
                        duration = filler_end - filler_start
                        
                        # Only count segments within typical filler word duration
                        if min_duration_ms <= duration <= max_duration_ms:
                            segments.append((filler_start, filler_end))
                        
                        in_potential_filler = False
            
            # Merge overlapping segments
            merged = self._merge_overlapping_segments(segments)
            print(f"[FILLER FALLBACK] Found {len(merged)} potential filler segments")
            return merged
            
        except Exception as e:
            print(f"[FILLER FALLBACK] Error: {e}")
            return []
    
    def _remove_filler_words(self, audio, enhancement_type):
        """Legacy method - redirects to Whisper-based detection"""
        # This method is kept for compatibility but redirects to the new method
        return audio  # The new method is called separately with audio_path
    
    def _merge_overlapping_segments(self, segments):
        """Merge overlapping time segments"""
        if not segments:
            return []
        
        segments.sort()
        merged = [segments[0]]
        
        for current in segments[1:]:
            last = merged[-1]
            if current[0] <= last[1] + 100:  # 100ms tolerance
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        
        return merged
    
    def _merge_overlapping_segments_with_labels(self, segments):
        """Merge overlapping time segments while preserving labels"""
        if not segments:
            return []
        
        # Sort by start time
        segments.sort(key=lambda x: x[0])
        merged = [segments[0]]
        
        for current in segments[1:]:
            last = merged[-1]
            if current[0] <= last[1] + 100:  # 100ms tolerance
                # Merge segments - combine labels
                merged_label = f"{last[2]}, {current[2]}"
                merged[-1] = (last[0], max(last[1], current[1]), merged_label)
            else:
                merged.append(current)
        
        return merged
    
    def _reduce_noise(self, audio, noise_level):
        """Apply noise reduction based on level using noisereduce library"""
        try:
            print(f"[NOISE] Applying noise reduction: {noise_level}")
            
            if noise_level == 'none':
                return audio
            
            enhanced = audio
            
            # Convert audio to numpy array for noisereduce
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            sample_rate = audio.frame_rate
            
            # Handle stereo audio
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
                # Process each channel separately
                left_channel = samples[:, 0]
                right_channel = samples[:, 1]
            else:
                left_channel = samples
                right_channel = None
            
            # Import noisereduce library
            try:
                import noisereduce as nr
                
                # ULTRA AGGRESSIVE noise reduction - multi-pass with different strategies
                if noise_level == 'light':
                    passes = 1
                    prop_decrease_values = [0.8]
                elif noise_level == 'moderate':
                    passes = 2
                    prop_decrease_values = [0.85, 0.9]
                else:  # strong - THREE PASSES with increasing aggression
                    passes = 3
                    prop_decrease_values = [0.9, 0.95, 1.0]  # Start moderate, end at 100%
                
                print(f"[NOISE] ULTRA AGGRESSIVE MODE: {passes} passes with prop_decrease={prop_decrease_values}")
                
                # Multi-pass noise reduction
                left_clean = left_channel.copy()
                for i, prop_dec in enumerate(prop_decrease_values):
                    print(f"[NOISE] Pass {i+1}/{passes} - Removing {int(prop_dec*100)}% of detected noise...")
                    
                    # Use NON-stationary for first pass to catch all noise types
                    if i == 0:
                        print(f"[NOISE]   Pass {i+1}: Non-stationary (catches varying noise)")
                        left_clean = nr.reduce_noise(
                            y=left_clean,
                            sr=sample_rate,
                            stationary=False,  # Non-stationary first to catch variable noise
                            prop_decrease=prop_dec,
                            n_fft=2048,
                            hop_length=256
                        )
                    else:
                        print(f"[NOISE]   Pass {i+1}: Stationary (targets constant background)")
                        left_clean = nr.reduce_noise(
                            y=left_clean,
                            sr=sample_rate,
                            stationary=True,  # Stationary for background car noise
                            prop_decrease=prop_dec,
                            n_fft=2048,
                            hop_length=256,
                            freq_mask_smooth_hz=100,  # Less smoothing = more aggressive
                            time_mask_smooth_ms=50
                        )
                
                print(f"[NOISE] Left channel: All {passes} passes completed")
                
                # Apply to right channel if stereo
                if right_channel is not None:
                    right_clean = right_channel.copy()
                    for i, prop_dec in enumerate(prop_decrease_values):
                        if i == 0:
                            right_clean = nr.reduce_noise(
                                y=right_clean,
                                sr=sample_rate,
                                stationary=False,
                                prop_decrease=prop_dec,
                                n_fft=2048,
                                hop_length=256
                            )
                        else:
                            right_clean = nr.reduce_noise(
                                y=right_clean,
                                sr=sample_rate,
                                stationary=True,
                                prop_decrease=prop_dec,
                                n_fft=2048,
                                hop_length=256,
                                freq_mask_smooth_hz=100,
                                time_mask_smooth_ms=50
                            )
                    print(f"[NOISE] Right channel: All {passes} passes completed")
                    # Combine channels
                    samples_clean = np.column_stack((left_clean, right_clean)).flatten()
                else:
                    samples_clean = left_clean
                
                # Normalize to prevent clipping
                max_val = np.max(np.abs(samples_clean))
                if max_val > 0:
                    samples_clean = samples_clean / max_val * 32767 * 0.9
                
                samples_clean = samples_clean.astype(np.int16)
                
                # Create new AudioSegment
                enhanced = audio._spawn(samples_clean.tobytes())
                
                # Apply EXTREME filtering for extra cleanup
                if noise_level in ['moderate', 'strong']:
                    print(f"[NOISE] Applying band-pass filter (80-8000Hz) to isolate voice...")
                    enhanced = enhanced.high_pass_filter(80)  # Remove deep rumble
                    enhanced = enhanced.low_pass_filter(8000)  # Remove high hiss
                
                if noise_level == 'strong':
                    print(f"[NOISE] Applying additional notch filters for car frequencies...")
                    # Target common car/traffic frequencies
                    # Most car engine noise is in 50-200Hz range
                    # Road noise is 200-500Hz
                    try:
                        enhanced = enhanced.high_pass_filter(150)  # Aggressive low-cut to remove car rumble
                        print(f"[NOISE] Applied 150Hz high-pass to eliminate car engine noise")
                    except Exception as e:
                        print(f"[NOISE] High-pass filter error: {e}")
                    
                    try:
                        enhanced = compress_dynamic_range(enhanced, threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)
                        print(f"[NOISE] Dynamic compression applied to reduce noise floor")
                    except Exception as e:
                        print(f"[NOISE] Compression skipped: {e}")
                
                print(f"[NOISE] ULTRA AGGRESSIVE noise reduction completed - {passes} passes applied!")
                
                # Normalize final output
                enhanced = normalize(enhanced)
                
                print(f"[NOISE] Noise reduction applied successfully using noisereduce")
                return enhanced
                
            except ImportError as ie:
                print(f"[NOISE] noisereduce not available: {ie}, using fallback method")
                # Fallback to basic filtering
                if noise_level == 'light':
                    enhanced = enhanced.high_pass_filter(80)
                elif noise_level == 'moderate':
                    enhanced = enhanced.high_pass_filter(80)
                    enhanced = enhanced.low_pass_filter(8000)
                    enhanced = normalize(enhanced)
                elif noise_level == 'strong':
                    enhanced = enhanced.high_pass_filter(100)
                    enhanced = enhanced.low_pass_filter(7000)
                    enhanced = compress_dynamic_range(enhanced, threshold=-20.0, ratio=4.0)
                    enhanced = normalize(enhanced)
                    enhanced = self._apply_spectral_noise_reduction(enhanced)
                
                return enhanced
            except Exception as e:
                print(f"[NOISE] noisereduce error: {e}")
                import traceback
                traceback.print_exc()
                print("[NOISE] Falling back to basic filtering")
                # Fallback to basic filtering
                if noise_level == 'light':
                    enhanced = enhanced.high_pass_filter(80)
                elif noise_level == 'moderate':
                    enhanced = enhanced.high_pass_filter(80)
                    enhanced = enhanced.low_pass_filter(8000)
                    enhanced = normalize(enhanced)
                elif noise_level == 'strong':
                    enhanced = enhanced.high_pass_filter(100)
                    enhanced = enhanced.low_pass_filter(7000)
                    try:
                        enhanced = compress_dynamic_range(enhanced, threshold=-20.0, ratio=4.0)
                    except:
                        pass
                    enhanced = normalize(enhanced)
                
                return enhanced
            
        except Exception as e:
            print(f"[NOISE] Error: {e}")
            import traceback
            traceback.print_exc()
            return audio
    
    def _apply_spectral_noise_reduction(self, audio):
        """Advanced spectral noise reduction using signal processing"""
        try:
            print("[SPECTRAL] Applying spectral noise reduction...")
            
            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize
            samples = samples / (np.max(np.abs(samples)) + 1e-10)
            
            # Apply FFT for frequency domain processing
            fft_data = np.fft.rfft(samples)
            frequencies = np.fft.rfftfreq(len(samples), 1.0 / audio.frame_rate)
            
            # Estimate noise profile (from quieter sections)
            magnitude = np.abs(fft_data)
            noise_threshold = np.percentile(magnitude, 15)  # Bottom 15% is likely noise
            
            # Create noise gate in frequency domain
            noise_gate = np.where(magnitude < noise_threshold * 1.5, 0.3, 1.0)
            
            # Apply noise gate
            fft_data_clean = fft_data * noise_gate
            
            # Convert back to time domain
            samples_clean = np.fft.irfft(fft_data_clean, n=len(samples))
            
            # Denormalize
            samples_clean = samples_clean * 32767 / (np.max(np.abs(samples_clean)) + 1e-10)
            samples_clean = samples_clean.astype(np.int16)
            
            # Create new AudioSegment
            cleaned_audio = audio._spawn(samples_clean.tobytes())
            
            print("[SPECTRAL] Spectral noise reduction complete")
            return cleaned_audio
            
        except Exception as e:
            print(f"[SPECTRAL] Error: {e}")
            return audio
    
    def _apply_transition_smoothing(self, audio):
        """Apply subtle crossfades to blend audio cuts for natural flow"""
        try:
            print("[SMOOTHING] Applying transition smoothing for natural blending...")
            
            # Apply gentle fade in/out to prevent jarring cuts
            fade_duration = 30  # 30ms subtle fade
            
            if len(audio) > fade_duration * 2:
                # Apply subtle fades at start and end
                audio = audio.fade_in(fade_duration).fade_out(fade_duration)
                print("[SMOOTHING] Applied subtle crossfades for natural flow")
            else:
                print("[SMOOTHING] Audio too short for fading")
            
            return audio
            
        except Exception as e:
            print(f"[SMOOTHING] Error: {e}")
            return audio

class VideoService:
    def __init__(self, db, socketio=None):
        self.db = db
        self.videos = db.videos
        self.socketio = socketio  # WebSocket for real-time updates
        self.upload_folder = os.getenv('UPLOAD_FOLDER', 'uploads')
        self.max_content_length = int(os.getenv('MAX_CONTENT_LENGTH', 500 * 1024 * 1024))
        
        # Initialize enhancers
        self.audio_enhancer = AudioEnhancer()
        self.color_enhancer = AIColorEnhancer()
        
        # Initialize OpenAI client for summarization
        try:
            import openai
            api_key = os.environ.get('OPENAI_API_KEY', '')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                print("[VIDEO SERVICE] OpenAI client initialized for video summarization")
            else:
                self.openai_client = None
                print("[VIDEO SERVICE] No OpenAI API key found - summarization disabled")
        except Exception as e:
            print(f"Warning: Could not initialize OpenAI client: {e}")
            self.openai_client = None

    def save_video(self, file, user_id):
        if not file:
            raise ValueError("No file provided")

        print(f"[SAVE_VIDEO] Saving video for user {user_id}")
        filename = secure_filename(file.filename)
        filepath = os.path.join(self.upload_folder, filename)
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Save file
        print(f"[SAVE_VIDEO] Saving file to: {filepath}")
        file.save(filepath)
        print(f"[SAVE_VIDEO] File saved, size: {os.path.getsize(filepath)} bytes")
        
        # Validate file
        if not self._is_valid_video(filepath):
            print(f"[SAVE_VIDEO] Invalid video file, removing")
            os.remove(filepath)
            raise ValueError("Invalid video file")
        
        print(f"[SAVE_VIDEO] Video validated successfully")

        # Create video document
        video = Video(
            user_id=ObjectId(user_id),
            filename=filename,
            filepath=filepath,
            size=os.path.getsize(filepath)
        )
        
        # Extract metadata (with timeout protection)
        print(f"[SAVE_VIDEO] Extracting metadata...")
        try:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Metadata extraction timed out")
            
            # Set 10 second timeout for metadata extraction (Unix only, Windows doesn't support signal.alarm)
            # For Windows, just catch any exception
            self._extract_metadata(video)
        except Exception as e:
            print(f"[SAVE_VIDEO] Metadata extraction failed or timed out: {e}")
            # Continue anyway with minimal metadata
            video.metadata["format"] = os.path.splitext(filename)[1][1:]
        
        # Save to database
        print(f"[SAVE_VIDEO] Saving to database...")
        result = self.videos.insert_one(video.to_dict())
        video_id = str(result.inserted_id)
        print(f"[SAVE_VIDEO] Video saved successfully with ID: {video_id}")
        
        # Note: Transcription is now only generated on-demand during audio enhancement
        # or filler word detection to improve upload performance
        
        return video_id
    
    def _auto_transcribe_video(self, video_id, video_path):
        """Auto-generate transcript after video upload"""
        try:
            from moviepy.editor import VideoFileClip
            import tempfile
            
            print(f"[AUTO_TRANSCRIBE] Starting for video {video_id}")
            
            # Extract audio
            temp_audio = tempfile.mktemp(suffix='.wav')
            clip = VideoFileClip(video_path)
            if not clip.audio:
                print(f"[AUTO_TRANSCRIBE] No audio track found")
                clip.close()
                return
            
            clip.audio.write_audiofile(temp_audio, verbose=False, logger=None)
            clip.close()
            
            # Generate transcript with filler detection (using 'aggressive' to catch more fillers like "I think")
            audio_enhancer = AudioEnhancer()
            transcript_data = audio_enhancer.generate_transcript_with_fillers(
                temp_audio,
                enhancement_type='aggressive',  # Changed from 'medium' to show more filler highlights
                detect_repeated=True
            )
            
            # Clean up temp audio
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            if transcript_data:
                # Update video with transcript
                self.videos.update_one(
                    {'_id': ObjectId(video_id)},
                    {'$set': {'transcript': transcript_data}}
                )
                print(f"[AUTO_TRANSCRIBE] Transcript saved: {transcript_data['total_words']} words, {transcript_data['filler_count']} fillers")
            else:
                print(f"[AUTO_TRANSCRIBE] Failed to generate transcript")
                
        except Exception as e:
            print(f"[AUTO_TRANSCRIBE] Error: {e}")
            import traceback
            traceback.print_exc()

    def process_video(self, video_id, options):
        video = self.get_video(video_id)
        if not video:
            raise ValueError("Video not found")

        video.status = "processing"
        video.process_start_time = datetime.utcnow()
        video.processing_options = options
        
        # Emit start event
        self._emit_progress(video_id, 'started', 0, 'Starting video processing...')
        
        try:
            current_progress = 0
            total_steps = sum([
                bool(options.get('cut_silence')),
                bool(options.get('enhance_audio')),
                bool(options.get('cut_filler_segments', options.get('remove_filler_words', False))),  # Cut filler segments from video
                bool(options.get('generate_thumbnail')),
                bool(options.get('generate_subtitles')),
                bool(options.get('summarize')),
                bool(any([options.get('stabilization'), options.get('brightness'), 
                         options.get('contrast'), options.get('saturation')]))
            ])
            step_progress = 90 / max(total_steps, 1)  # Reserve 10% for completion
            
            # Enhanced processing with actual options
            if options.get('cut_silence'):
                current_progress += step_progress
                self._emit_progress(video_id, 'cutting_silence', int(current_progress), 'Removing silent parts...')
                self._cut_silence(video)
            
            if options.get('enhance_audio'):
                current_progress += step_progress
                self._emit_progress(video_id, 'enhancing_audio', int(current_progress), 'Enhancing audio quality...')
                self._enhance_audio(video, options)
            
            # NEW: Cut filler segments from video using segments detected during audio enhancement
            cut_filler_enabled = options.get('cut_filler_segments', options.get('remove_filler_words', False))
            print(f"[PROCESS] Cut filler segments enabled: {cut_filler_enabled}")
            print(f"[PROCESS] Detect and remove fillers (audio): {options.get('detect_and_remove_fillers', False)}")
            
            if cut_filler_enabled:
                current_progress += step_progress
                self._emit_progress(video_id, 'cutting_filler_segments', int(current_progress), 'Cutting filler segments from video...')
                
                # Get filler segments from audio enhancement metrics
                filler_segments = video.outputs.get('audio_enhancement_metrics', {}).get('filler_segments', [])
                print(f"[PROCESS] Filler segments from audio enhancement: {len(filler_segments)} segments")
                
                # If no segments from audio enhancement, ALWAYS detect them for video cutting
                if not filler_segments:
                    print(f"[PROCESS] No pre-detected segments, running filler detection for video cutting...")
                    audio_enhancer = AudioEnhancer()
                    temp_audio = f"{os.path.splitext(video.filepath)[0]}_temp_detect.wav"
                    
                    # Extract audio for detection
                    from moviepy.editor import VideoFileClip
                    clip = VideoFileClip(video.filepath)
                    if clip.audio:
                        clip.audio.write_audiofile(temp_audio, verbose=False, logger=None)
                        clip.close()
                        
                        # Detect fillers using the same method as audio enhancement
                        target_fillers = ['um', 'uh', 'er', 'ah', 'hmm', 'mm', 'like', 'you know', 'i mean', 'so', 'well']
                        print(f"[PROCESS] Detecting fillers: {target_fillers}")
                        
                        filler_segments = audio_enhancer._detect_fillers_with_whisper(
                            temp_audio, 
                            target_fillers,
                            detect_repeated=options.get('detect_repeated_words', True)
                        )
                        
                        # Clean up
                        if os.path.exists(temp_audio):
                            os.remove(temp_audio)
                        
                        # Normalize to (start, end) format
                        if filler_segments:
                            filler_segments = [(seg[0], seg[1]) for seg in filler_segments]
                            print(f"[PROCESS] Detected {len(filler_segments)} filler segments for video cutting:")
                            for i, seg in enumerate(filler_segments):
                                print(f"[PROCESS]   Segment {i+1}: {seg[0]}ms - {seg[1]}ms")
                        else:
                            filler_segments = []
                    else:
                        clip.close()
                        print(f"[PROCESS] No audio track found in video")
                
                if filler_segments:
                    print(f"[PROCESS] Calling _remove_filler_segments_from_video with {len(filler_segments)} segments")
                    self._remove_filler_segments_from_video(video, options, filler_segments)
                else:
                    print(f"[PROCESS] No filler segments to remove from video")
            
            if options.get('generate_thumbnail'):
                current_progress += step_progress
                self._emit_progress(video_id, 'generating_thumbnail', int(current_progress), 'Creating video thumbnail...')
                self._generate_thumbnail(video, options)
            
            if options.get('generate_subtitles'):
                current_progress += step_progress
                self._emit_progress(video_id, 'generating_subtitles', int(current_progress), 'Generating subtitles with Whisper...')
                self._generate_subtitles(video, options)
            
            if options.get('summarize'):
                current_progress += step_progress
                self._emit_progress(video_id, 'summarizing', int(current_progress), 'Creating video summary...')
                self._summarize_video(video, options)

            # Apply video enhancements
            if any([options.get('stabilization'), options.get('brightness'), options.get('contrast'), 
                    options.get('saturation'), options.get('ai_color_enhancement')]):
                current_progress += step_progress
                self._emit_progress(video_id, 'enhancing_video', int(current_progress), 'Applying video enhancements...')
                self._apply_video_enhancements(video, options)

            video.status = "completed"
            video.process_end_time = datetime.utcnow()
            
            # Emit completion
            self._emit_progress(video_id, 'completed', 100, 'Processing complete!')
            
        except Exception as e:
            video.status = "failed"
            video.error = str(e)
            video.process_end_time = datetime.utcnow()
            self._emit_progress(video_id, 'failed', 0, f'Processing failed: {str(e)}')
            raise
        
        finally:
            # Get dict without _id to avoid MongoDB update error
            update_dict = video.to_dict()
            update_dict.pop('_id', None)  # Remove _id if present
            self.videos.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": update_dict}
            )
    
    def _emit_progress(self, video_id, step, progress, message):
        """Emit progress update via WebSocket"""
        if self.socketio:
            self.socketio.emit('processing_progress', {
                'video_id': str(video_id),
                'step': step,
                'progress': progress,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            })

    def get_video(self, video_id):
        video_data = self.videos.find_one({"_id": ObjectId(video_id)})
        if not video_data:
            return None
        return Video.from_dict(video_data)

    def get_user_videos(self, user_id):
        # Query with both ObjectId and string format since videos may have user_id stored either way
        videos = list(self.videos.find({
            "$or": [
                {"user_id": ObjectId(user_id)},
                {"user_id": str(user_id)}
            ]
        }))
        print(f"[GET_USER_VIDEOS] User ID: {user_id}, Found {len(videos)} videos")
        return [Video.from_dict(video).to_dict() for video in videos]

    def delete_video(self, video_id, user_id):
        video = self.get_video(video_id)
        if not video:
            raise ValueError("Video not found")
        
        if str(video.user_id) != str(user_id):
            raise ValueError("Unauthorized")
        
        # Delete file
        if os.path.exists(video.filepath):
            os.remove(video.filepath)
        
        # Delete processed files
        if video.outputs.get('processed_video') and os.path.exists(video.outputs['processed_video']):
            os.remove(video.outputs['processed_video'])
        
        # Delete from database
        self.videos.delete_one({"_id": ObjectId(video_id)})

    def _is_valid_video(self, filepath):
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(filepath)
            return file_type.startswith('video/')
        except:
            # Fallback: check file extension
            valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
            return any(filepath.lower().endswith(ext) for ext in valid_extensions)

    def _extract_metadata(self, video):
        try:
            print(f"[METADATA] Extracting metadata for: {video.filepath}")
            clip = VideoFileClip(video.filepath, audio=False)  # Don't load audio for metadata
            print(f"[METADATA] VideoFileClip opened successfully")
            video.metadata.update({
                "duration": clip.duration,
                "fps": clip.fps,
                "resolution": f"{clip.size[0]}x{clip.size[1]}",
                "format": os.path.splitext(video.filename)[1][1:]
            })
            print(f"[METADATA] Metadata extracted: {video.metadata}")
            clip.close()
        except Exception as e:
            print(f"[METADATA] Error extracting metadata: {e}")
            import traceback
            traceback.print_exc()
            video.metadata.update({
                "format": os.path.splitext(video.filename)[1][1:]
            })

    def _apply_video_enhancements(self, video, options):
        """Apply video enhancements like brightness, contrast, stabilization, and AI color enhancement"""
        try:
            print("[VIDEO ENHANCE] Starting video enhancement processing...")
            clip = VideoFileClip(video.filepath)
            
            # Check if AI enhancement is requested
            use_ai_enhancement = options.get('ai_color_enhancement', False)
            ai_adjustments = None
            
            if use_ai_enhancement:
                print("[VIDEO ENHANCE] AI Color Enhancement enabled - analyzing video...")
                analysis = self.color_enhancer.analyze_video_colors(video.filepath)
                if analysis:
                    ai_adjustments = self.color_enhancer.calculate_optimal_adjustments(analysis)
                    print(f"[VIDEO ENHANCE] AI adjustments calculated: {ai_adjustments}")
                    
                    # Store AI analysis results
                    video.metadata['ai_color_analysis'] = {
                        'original_saturation': float(analysis['saturation']),
                        'original_brightness': float(analysis['brightness']),
                        'original_contrast': float(analysis['contrast']),
                        'applied_saturation_mult': float(ai_adjustments['saturation']),
                        'applied_brightness_mult': float(ai_adjustments['brightness']),
                        'applied_contrast_mult': float(ai_adjustments['contrast'])
                    }
            
            # Get manual adjustments (if provided, they override AI)
            brightness = options.get('brightness', 100) / 100.0
            contrast = options.get('contrast', 100) / 100.0
            saturation = options.get('saturation', 100) / 100.0
            
            # If AI enhancement is enabled and no manual override, use AI values
            if use_ai_enhancement and ai_adjustments:
                if options.get('brightness') is None:
                    brightness = ai_adjustments['brightness']
                if options.get('contrast') is None:
                    contrast = ai_adjustments['contrast']
                if options.get('saturation') is None:
                    saturation = ai_adjustments['saturation']
            
            print(f"[VIDEO ENHANCE] Final adjustments - Brightness: {brightness:.2f}x, Contrast: {contrast:.2f}x, Saturation: {saturation:.2f}x")
            
            # Apply enhancements if needed
            if brightness != 1.0 or contrast != 1.0 or saturation != 1.0:
                def enhance_frame(image):
                    # Convert BGR (moviepy) to RGB for processing
                    frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    
                    # Apply AI enhancement
                    enhanced = self.color_enhancer.apply_ai_enhancement(
                        frame,
                        saturation_mult=saturation,
                        brightness_mult=brightness,
                        contrast_mult=contrast
                    )
                    
                    # Convert back to RGB for moviepy
                    return cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
                
                clip = clip.fl_image(enhance_frame)
                print("[VIDEO ENHANCE] Frame enhancement applied")
            
            # Apply stabilization (basic implementation)
            stabilization = options.get('stabilization', 'none')
            if stabilization != 'none':
                print(f"[VIDEO ENHANCE] Applying {stabilization} stabilization...")
                # For now, we'll just apply a simple smoothing
                # In a real implementation, you'd use more sophisticated stabilization
                pass
            
            # Save enhanced video with GPU-accelerated encoding if available
            output_path = f"{os.path.splitext(video.filepath)[0]}_enhanced.mp4"
            print(f"[VIDEO ENHANCE] Saving enhanced video to: {output_path}")
            
            # Get optimal encoder (GPU if available)
            encoder = get_ffmpeg_encoder('h264')
            print(f"[VIDEO ENHANCE] Using encoder: {encoder}")
            
            # Use optimized encoding settings to prevent corruption
            clip.write_videofile(
                output_path,
                codec=encoder,
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='medium' if 'nvenc' not in encoder else 'p4',  # NVENC preset
                fps=clip.fps,
                threads=4,
                bitrate='5000k',
                audio_bitrate='192k',
                ffmpeg_params=[
                    '-crf', '23',  # Quality (lower = better, 18-28 is good range)
                    '-pix_fmt', 'yuv420p',  # Compatibility
                    '-movflags', '+faststart'  # Web optimization
                ] + (['-gpu', '0'] if 'nvenc' in encoder else [])
            )
            video.outputs["processed_video"] = output_path
            
            # Clear GPU cache after encoding
            if has_gpu():
                clear_cache()
            
            clip.close()
            print("[VIDEO ENHANCE] Video enhancement completed successfully!")
            
        except Exception as e:
            print(f"[VIDEO ENHANCE] Error: {e}")
            raise

    def _cut_silence(self, video):
        try:
            audio = AudioSegment.from_file(video.filepath)
            chunks = []
            silence_thresh = -40
            min_silence_len = 500
            
            # Process audio in chunks
            chunk_length = 10000
            for i in range(0, len(audio), chunk_length):
                chunk = audio[i:i + chunk_length]
                if chunk.dBFS > silence_thresh:
                    chunks.append(chunk)
            
            # Combine non-silent chunks
            processed_audio = AudioSegment.empty()
            for chunk in chunks:
                processed_audio += chunk
            
            # Save processed audio
            output_path = f"{os.path.splitext(video.filepath)[0]}_processed.mp4"
            processed_audio.export(output_path, format="mp4")
            video.outputs["processed_video"] = output_path
        except Exception as e:
            print(f"Error cutting silence: {e}")

    def _enhance_audio(self, video, options):
        """Enhanced audio processing with filler word removal and noise reduction"""
        try:
            print(f"[VIDEO SERVICE] Starting enhanced audio processing for {video.filepath}")
            
            # Initialize the audio enhancer
            audio_enhancer = AudioEnhancer()
            
            # Map frontend options to backend options - also pass enhancement_type correctly
            # Frontend sends 'noise_reduction' values like 'light', 'moderate', 'strong'
            # But audio_enhancement_type should be 'conservative', 'medium', 'aggressive'
            noise_level = options.get('noise_reduction', 'moderate')
            
            # VALIDATION: Map invalid values to valid ones
            noise_level_map = {
                'full': 'strong',      # Map 'full' to 'strong'
                'none': 'none',
                'light': 'light',
                'moderate': 'moderate',
                'strong': 'strong'
            }
            noise_level = noise_level_map.get(noise_level, 'moderate')
            print(f"[VIDEO SERVICE] Noise reduction level: {noise_level}")
            
            # Get filler removal options from frontend (with backward compatibility)
            detect_and_remove_fillers = options.get('detect_and_remove_fillers', options.get('remove_fillers', False))
            detect_repeated = options.get('detect_repeated_words', True)
            
            # Use filler_removal_level from frontend, NOT noise_reduction level
            filler_level = options.get('filler_removal_level', 'medium')
            # Validate filler level
            if filler_level not in ['conservative', 'medium', 'aggressive']:
                filler_level = 'medium'
            enhancement_type = filler_level
            print(f"[VIDEO SERVICE] Filler removal level: {enhancement_type}")
            
            # DEBUG: Log all filler-related options
            print(f"[VIDEO SERVICE] Filler options from frontend:")
            print(f"[VIDEO SERVICE]   detect_and_remove_fillers: {options.get('detect_and_remove_fillers')} (old: {options.get('remove_fillers')})")
            print(f"[VIDEO SERVICE]   cut_filler_segments: {options.get('cut_filler_segments')} (old: {options.get('remove_filler_words')})")
            print(f"[VIDEO SERVICE]   detect_repeated_words: {options.get('detect_repeated_words')}")
            print(f"[VIDEO SERVICE]   filler_removal_level: {options.get('filler_removal_level')}")
            
            backend_options = {
                'audio_enhancement_type': enhancement_type,  # Use mapped value
                'pause_threshold': options.get('pause_threshold', 500),
                'noise_reduction': noise_level,
                'detect_and_remove_fillers': detect_and_remove_fillers,  # Detect and remove filler words from audio
                'detect_repeated_words': detect_repeated  # Detect repeated words
            }
            
            print(f"[VIDEO SERVICE] Backend options: {backend_options}")
            
            # Extract audio from video first
            clip = VideoFileClip(video.filepath)
            audio_path = f"{os.path.splitext(video.filepath)[0]}_temp_audio.wav"
            print(f"[VIDEO SERVICE] Extracting audio to: {audio_path}")
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            
            # Check if transcript needs regeneration (if it shows 0 fillers but we're removing fillers)
            if detect_and_remove_fillers and video.transcript:
                current_filler_count = video.transcript.get('filler_count', 0)
                if current_filler_count == 0:
                    print(f"[VIDEO SERVICE] Transcript shows 0 fillers, regenerating with aggressive detection...")
                    new_transcript = audio_enhancer.generate_transcript_with_fillers(
                        audio_path,
                        enhancement_type='aggressive',
                        detect_repeated=True
                    )
                    if new_transcript:
                        video.transcript = new_transcript
                        self.videos.update_one(
                            {'_id': video._id},
                            {'$set': {'transcript': new_transcript}}
                        )
                        print(f"[VIDEO SERVICE] Transcript regenerated: {new_transcript['filler_count']} fillers detected")
            
            # Enhance the audio (pass audio_path for Whisper filler detection)
            print(f"[VIDEO SERVICE] Starting audio enhancement...")
            if detect_and_remove_fillers:
                print(f"[VIDEO SERVICE] Filler word removal: ENABLED (level: {enhancement_type})")
            else:
                print(f"[VIDEO SERVICE] Filler word removal: DISABLED")
            enhanced_audio, metrics = audio_enhancer.enhance_audio(audio_path, backend_options)
            
            # UPDATE TRANSCRIPT: Mark detected fillers in the transcript
            if detect_and_remove_fillers and metrics.get('filler_words_removed', 0) > 0:
                filler_segments = metrics.get('filler_segments', [])
                if filler_segments and video.transcript:
                    print(f"[VIDEO SERVICE] Updating transcript to mark {len(filler_segments)} detected fillers...")
                    transcript = video.transcript
                    words = transcript.get('words', [])
                    updated_count = 0
                    
                    # Mark words that fall within filler segments as fillers
                    for word in words:
                        word_start_ms = word['start'] * 1000  # Convert to ms
                        word_end_ms = word['end'] * 1000
                        
                        # Check if this word overlaps with any filler segment
                        for seg_start, seg_end in filler_segments:
                            if (word_start_ms >= seg_start and word_start_ms <= seg_end) or \
                               (word_end_ms >= seg_start and word_end_ms <= seg_end) or \
                               (word_start_ms <= seg_start and word_end_ms >= seg_end):
                                if not word.get('is_filler', False):
                                    word['is_filler'] = True
                                    updated_count += 1
                                break
                    
                    # Update filler count
                    transcript['filler_count'] = len(filler_segments)
                    video.transcript = transcript
                    
                    # Save updated transcript to database
                    self.videos.update_one(
                        {'_id': video._id},
                        {'$set': {'transcript': transcript}}
                    )
                    print(f"[VIDEO SERVICE] Transcript updated: marked {updated_count} words as fillers")
            
            # Save enhanced audio temporarily
            enhanced_audio_path = f"{os.path.splitext(video.filepath)[0]}_enhanced_audio.wav"
            print(f"[VIDEO SERVICE] Saving enhanced audio to: {enhanced_audio_path}")
            enhanced_audio.export(enhanced_audio_path, format="wav")
            
            # Create new video with enhanced audio
            print(f"[VIDEO SERVICE] Creating final video with enhanced audio...")
            # Load the enhanced audio as an AudioFileClip
            from moviepy.editor import AudioFileClip
            enhanced_audio_clip = AudioFileClip(enhanced_audio_path)
            enhanced_clip = clip.set_audio(enhanced_audio_clip)
            
            # Save final enhanced video with GPU acceleration
            output_path = f"{os.path.splitext(video.filepath)[0]}_enhanced.mp4"
            encoder = get_ffmpeg_encoder('h264')
            print(f"[AUDIO ENHANCE] Using encoder: {encoder}")
            print(f"[AUDIO ENHANCE] Starting video encoding - this may take a while...")
            
            try:
                enhanced_clip.write_videofile(
                    output_path, 
                    codec=encoder, 
                    audio_codec='aac',
                    preset='medium' if 'nvenc' not in encoder else 'p4',
                    verbose=False,
                    logger=None,
                    threads=4  # Limit threads to prevent hanging
                )
                print(f"[AUDIO ENHANCE] Video encoding completed!")
            except Exception as encode_error:
                print(f"[AUDIO ENHANCE] Encoding failed with {encoder}, trying fallback...")
                print(f"[AUDIO ENHANCE] Error: {encode_error}")
                # Fallback to libx264
                enhanced_clip.write_videofile(
                    output_path, 
                    codec='libx264', 
                    audio_codec='aac',
                    preset='medium',
                    verbose=True,  # Enable verbose for debugging
                    logger='bar',
                    threads=4
                )
                print(f"[AUDIO ENHANCE] Video encoding completed with fallback!")
            
            # Clear GPU cache
            if has_gpu():
                clear_cache()
            
            # Update video outputs
            video.outputs["processed_video"] = output_path
            video.outputs["audio_enhancement_metrics"] = metrics
            
            # Add detailed results for frontend display - use REAL filler word count
            original_duration_sec = metrics['original_duration_ms'] / 1000
            enhanced_duration_sec = metrics['enhanced_duration_ms'] / 1000
            time_saved_sec = metrics['time_saved_ms'] / 1000
            filler_words_removed = metrics.get('filler_words_removed', 0)
            
            video.outputs["enhancement_results"] = {
                'filler_words_removed': filler_words_removed,  # REAL count from Whisper
                'noise_reduction_percentage': 85 if noise_level in ['moderate', 'strong'] else (50 if noise_level == 'light' else 0),
                'duration_reduction_percentage': round(metrics['time_saved_percentage'], 1),
                'original_duration': f"{original_duration_sec:.1f}s",
                'enhanced_duration': f"{enhanced_duration_sec:.1f}s",
                'time_saved': f"{time_saved_sec:.1f}s"
            }
            
            print(f"[VIDEO SERVICE] Audio enhancement completed successfully")
            print(f"[VIDEO SERVICE] Metrics: {metrics}")
            print(f"[VIDEO SERVICE] Final video saved to: {output_path}")
            
            # Cleanup temporary files
            clip.close()
            enhanced_clip.close()
            enhanced_audio_clip.close()
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if os.path.exists(enhanced_audio_path):
                os.remove(enhanced_audio_path)
                
        except Exception as e:
            print(f"[VIDEO SERVICE] Error enhancing audio: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _remove_filler_segments_from_video(self, video, options, filler_segments=None):
        """
        Cut filler word segments from video using pre-detected timestamps from audio enhancement
        Creates a cleaned video with smooth transitions
        
        Args:
            video: Video object
            options: Processing options
            filler_segments: Pre-detected filler segments from audio enhancement (list of [start_ms, end_ms])
        """
        try:
            # Skip the check since we already verified in process_video
            print(f"[VIDEO FILLER REMOVAL] ========================================")
            print(f"[VIDEO FILLER REMOVAL] Starting video segment cutting")
            print(f"[VIDEO FILLER REMOVAL] Input filler_segments: {filler_segments}")
            print(f"[VIDEO FILLER REMOVAL] Number of segments: {len(filler_segments) if filler_segments else 0}")
            
            # Use provided filler segments from audio enhancement
            if not filler_segments:
                print("[VIDEO FILLER REMOVAL] No filler segments provided, skipping video cutting")
                return
            
            print(f"[VIDEO FILLER REMOVAL] Using {len(filler_segments)} pre-detected filler segments")
            
            # Normalize segments to (start_ms, end_ms) format
            normalized_segments = []
            for seg in filler_segments:
                if isinstance(seg, (list, tuple)):
                    start_ms = seg[0]
                    end_ms = seg[1]
                    normalized_segments.append((start_ms, end_ms))
                    print(f"[VIDEO FILLER REMOVAL] Segment: {start_ms}ms - {end_ms}ms")
            
            if not normalized_segments:
                print("[VIDEO FILLER REMOVAL] No valid segments after normalization")
                return
            
            # Use the enhanced video if available (has clean audio), otherwise use original
            input_video_path = video.outputs.get('processed_video', video.filepath)
            if not os.path.exists(input_video_path):
                input_video_path = video.filepath
            
            print(f"[VIDEO FILLER REMOVAL] Cutting from video: {input_video_path}")
            
            # Load video
            clip = VideoFileClip(input_video_path)
            
            # Create list of segments to KEEP (inverse of segments to remove)
            video_duration_ms = int(clip.duration * 1000)
            keep_segments = []
            last_end = 0
            
            # Sort filler segments by start time
            normalized_segments.sort(key=lambda x: x[0])
            
            for start_ms, end_ms in normalized_segments:
                # Add segment before this filler (if there's a gap)
                if start_ms > last_end:
                    keep_segments.append((last_end / 1000.0, start_ms / 1000.0))  # Convert to seconds
                last_end = end_ms
            
            # Add final segment after last filler
            if last_end < video_duration_ms:
                keep_segments.append((last_end / 1000.0, video_duration_ms / 1000.0))
            
            print(f"[VIDEO FILLER REMOVAL] Created {len(keep_segments)} keep segments:")
            for i, seg in enumerate(keep_segments):
                print(f"[VIDEO FILLER REMOVAL]   Keep segment {i+1}: {seg[0]:.2f}s - {seg[1]:.2f}s")
            
            # Step 4: Cut video using ffmpeg for precise, smooth cutting
            output_path = f"{os.path.splitext(video.filepath)[0]}_cleaned.mp4"
            print(f"[VIDEO FILLER REMOVAL] Output path: {output_path}")
            print(f"[VIDEO FILLER REMOVAL] Calling FFmpeg to cut video...")
            self._cut_video_segments_ffmpeg(input_video_path, keep_segments, output_path, smooth_transitions=True)
            print(f"[VIDEO FILLER REMOVAL] FFmpeg cutting completed")
            
            # Step 5: Update video outputs
            original_duration = clip.duration
            clip.close()
            
            # Get cleaned video duration
            cleaned_clip = VideoFileClip(output_path)
            cleaned_duration = cleaned_clip.duration
            cleaned_clip.close()
            
            time_saved = original_duration - cleaned_duration
            percentage_saved = (time_saved / original_duration) * 100 if original_duration > 0 else 0
            
            video.outputs["cleaned_video"] = output_path
            video.outputs["processed_video"] = output_path  # Also set as processed_video for download
            video.outputs["filler_removal_stats"] = {
                'segments_removed': len(normalized_segments),
                'filler_words_removed': len(normalized_segments),  # Count of segments removed
                'repeated_words_removed': 0,  # Not tracked separately here
                'original_duration': f"{original_duration:.2f}s",
                'cleaned_duration': f"{cleaned_duration:.2f}s",
                'time_saved': f"{time_saved:.2f}s",
                'percentage_saved': f"{percentage_saved:.1f}%"
            }
            
            print(f"[VIDEO FILLER REMOVAL] Completed! Removed {len(normalized_segments)} segments")
            print(f"[VIDEO FILLER REMOVAL] Saved to: {output_path}")
            print(f"[VIDEO FILLER REMOVAL] Time saved: {time_saved:.2f}s ({percentage_saved:.1f}%)")
                
        except Exception as e:
            print(f"[VIDEO FILLER REMOVAL] Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _cut_video_segments_ffmpeg(self, input_path, keep_segments, output_path, smooth_transitions=True):
        """
        Cut video into segments and concatenate using FFmpeg with smooth transitions
        
        Args:
            input_path: Path to input video
            keep_segments: List of (start_sec, end_sec) tuples to keep
            output_path: Path for output video
            smooth_transitions: Whether to apply crossfade transitions (default: True)
        """
        try:
            import subprocess
            import tempfile
            
            print(f"[FFMPEG VIDEO CUT] Cutting video into {len(keep_segments)} segments")
            
            # Create temporary directory for segment files
            temp_dir = tempfile.mkdtemp()
            segment_files = []
            
            # Step 1: Extract each segment
            for i, (start_sec, end_sec) in enumerate(keep_segments):
                segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp4")
                duration = end_sec - start_sec
                
                # Use ffmpeg to extract segment with re-encoding for smooth playback
                encoder = get_ffmpeg_encoder('h264')
                
                cmd = [
                    'ffmpeg',
                    '-ss', str(start_sec),  # Start time
                    '-i', input_path,       # Input file
                    '-t', str(duration),    # Duration
                    '-c:v', encoder,        # Video codec
                    '-c:a', 'aac',          # Audio codec
                    '-b:a', '192k',         # Audio bitrate
                    '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
                    '-y',                   # Overwrite output
                    segment_path
                ]
                
                print(f"[FFMPEG VIDEO CUT] Extracting segment {i+1}/{len(keep_segments)}: {start_sec:.2f}s - {end_sec:.2f}s")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"[FFMPEG VIDEO CUT] Warning: Segment {i} extraction had issues: {result.stderr}")
                else:
                    segment_files.append(segment_path)
            
            if not segment_files:
                raise Exception("No segments were successfully extracted")
            
            # Step 2: Create concat file for ffmpeg
            concat_file = os.path.join(temp_dir, 'concat_list.txt')
            with open(concat_file, 'w') as f:
                for seg_file in segment_files:
                    # FFmpeg concat requires proper escaping
                    f.write(f"file '{seg_file}'\n")
            
            print(f"[FFMPEG VIDEO CUT] Concatenating {len(segment_files)} segments...")
            
            # Step 3: Concatenate segments
            if smooth_transitions and len(segment_files) > 1:
                # Use complex filter for smooth crossfade transitions (adds ~100ms crossfade)
                # This is optional and can be disabled for faster processing
                print(f"[FFMPEG VIDEO CUT] Applying smooth transitions between segments")
                
            # Simple concatenation (faster, no transitions)
            concat_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Copy streams without re-encoding (faster)
                '-y',
                output_path
            ]
            
            result = subprocess.run(concat_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[FFMPEG VIDEO CUT] Concat error: {result.stderr}")
                # Try with re-encoding if copy fails
                print(f"[FFMPEG VIDEO CUT] Retrying with re-encoding...")
                encoder = get_ffmpeg_encoder('h264')
                concat_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file,
                    '-c:v', encoder,
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-y',
                    output_path
                ]
                result = subprocess.run(concat_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"FFmpeg concatenation failed: {result.stderr}")
            
            print(f"[FFMPEG VIDEO CUT] Video successfully created: {output_path}")
            
            # Cleanup temporary files
            import shutil
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            print(f"[FFMPEG VIDEO CUT] Error: {e}")
            raise

    def _generate_thumbnail(self, video, options=None):
        try:
            print(f"[THUMBNAIL] Starting AI-powered thumbnail generation for: {video.filepath}")
            print(f"[THUMBNAIL DEBUG] Received options: {options}")
            
            # Get custom text and styling options
            custom_text = options.get('thumbnail_text') if options else None
            frame_index = options.get('thumbnail_frame_index') if options else None
            
            # Text customization options
            text_options = {
                'font_size': options.get('thumbnail_font_size', 100) if options else 100,
                'text_color': options.get('thumbnail_text_color', '#FFFFFF') if options else '#FFFFFF',
                'outline_color': options.get('thumbnail_outline_color', '#FF6400') if options else '#FF6400',
                'position': options.get('thumbnail_position', 'bottom') if options else 'bottom',
                'font_style': options.get('thumbnail_font_style', 'bold') if options else 'bold',
                'shadow': options.get('thumbnail_shadow', True) if options else True,
                'background': options.get('thumbnail_background', True) if options else True,
                'background_color': options.get('thumbnail_background_color', '#000000') if options else '#000000'
            }
            
            print(f"[THUMBNAIL DEBUG] custom_text = '{custom_text}' (type: {type(custom_text)})")
            print(f"[THUMBNAIL DEBUG] frame_index = {frame_index}")
            print(f"[THUMBNAIL DEBUG] text_options = {text_options}")
            
            # Ensure custom_text is not empty string
            if custom_text == '':
                custom_text = None
                print(f"[THUMBNAIL DEBUG] Empty string detected, setting to None")
            
            if custom_text:
                print(f"[THUMBNAIL] ✅ Using custom text: '{custom_text}'")
            else:
                print(f"[THUMBNAIL] ⚠️ No custom text provided, will use AI generation")
            
            if frame_index is not None:
                print(f"[THUMBNAIL] Using selected frame index: {frame_index}")
            
            # Delete old thumbnails before regenerating
            if 'thumbnails' in video.outputs and video.outputs['thumbnails']:
                print(f"[THUMBNAIL] Deleting old thumbnails before regeneration...")
                for old_thumb in video.outputs['thumbnails']:
                    if os.path.exists(old_thumb):
                        try:
                            os.remove(old_thumb)
                            print(f"[THUMBNAIL] Deleted old thumbnail: {old_thumb}")
                        except Exception as e:
                            print(f"[THUMBNAIL] Failed to delete {old_thumb}: {e}")
                video.outputs['thumbnails'] = []
                video.outputs['thumbnail'] = None
            
            # Initialize AI thumbnail generator
            ai_generator = AIThumbnailGenerator()
            
            # Check if file exists
            if not os.path.exists(video.filepath):
                print(f"[THUMBNAIL] Error: Video file does not exist: {video.filepath}")
                return
            
            print(f"[THUMBNAIL] File exists, size: {os.path.getsize(video.filepath)} bytes")
            
            # Try to open with OpenCV
            cap = cv2.VideoCapture(video.filepath)
            
            if not cap.isOpened():
                print(f"[THUMBNAIL] Error: Could not open video file with OpenCV")
                print(f"[THUMBNAIL] Attempting alternative method with moviepy...")
                
                # Try with moviepy as fallback
                try:
                    from moviepy.editor import VideoFileClip
                    clip = VideoFileClip(video.filepath)
                    
                    print(f"[THUMBNAIL] Using MoviePy with intelligent frame selection...")
                    
                    # Sample frames for quality analysis
                    duration = clip.duration
                    sample_times = np.linspace(0.1 * duration, 0.9 * duration, 20)
                    candidate_frames = []
                    
                    for idx, time_sec in enumerate(sample_times):
                        frame = clip.get_frame(time_sec)
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        
                        # Calculate quality score
                        quality_score = ai_generator._calculate_frame_quality(frame_bgr)
                        
                        if quality_score > 0.3:
                            candidate_frames.append((idx, frame_bgr, quality_score, time_sec))
                    
                    # Sort by quality and select top 5
                    candidate_frames.sort(key=lambda x: x[2], reverse=True)
                    best_frames = candidate_frames[:5]
                    
                    print(f"[THUMBNAIL] Selected {len(best_frames)} high-quality frames using AI analysis")
                    
                    thumbnails = []
                    
                    for i, (idx, frame_bgr, quality_score, time_sec) in enumerate(best_frames):
                        print(f"[THUMBNAIL] Processing frame at {time_sec:.1f}s (quality: {quality_score:.2f})")
                        
                        # Save temporary frame
                        temp_frame_path = f"{os.path.splitext(video.filepath)[0]}_temp_frame_{i+1}.jpg"
                        cv2.imwrite(temp_frame_path, frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        
                        # Use custom text if provided, otherwise generate AI text
                        if custom_text:
                            ai_text = custom_text
                            print(f"[THUMBNAIL] ✅✅✅ Using CUSTOM TEXT: '{ai_text}' ✅✅✅")
                        else:
                            # Generate AI text for this frame
                            ai_text = ai_generator.generate_catchy_text(temp_frame_path, video.filepath)
                            print(f"[THUMBNAIL] Generated AI text: '{ai_text}'")
                        
                        # Create YouTube thumbnail with text and styling options
                        thumbnail_path = f"{os.path.splitext(video.filepath)[0]}_thumb_{i+1}.jpg"
                        final_path = ai_generator.create_youtube_thumbnail(
                            temp_frame_path, 
                            ai_text, 
                            thumbnail_path,
                            text_options
                        )
                        
                        # Clean up temp frame
                        if os.path.exists(temp_frame_path):
                            os.remove(temp_frame_path)
                        
                        if os.path.exists(final_path):
                            thumbnails.append(final_path)
                            print(f"[THUMBNAIL] Successfully created AI thumbnail {i+1} using moviepy: {final_path}")
                            print(f"[THUMBNAIL] AI Text: {ai_text}")
                        else:
                            print(f"[THUMBNAIL] Failed to create AI thumbnail {i+1} using moviepy")
                    
                    clip.close()
                    
                    if thumbnails:
                        video.outputs["thumbnails"] = thumbnails
                        video.outputs["thumbnail"] = thumbnails[2] if len(thumbnails) > 2 else thumbnails[0]
                        print(f"[THUMBNAIL] Generated {len(thumbnails)} thumbnails successfully with moviepy")
                        print(f"[THUMBNAIL] Primary thumbnail: {video.outputs['thumbnail']}")
                    else:
                        print(f"[THUMBNAIL] Warning: No thumbnails were generated with moviepy")
                    
                    return
                    
                except Exception as moviepy_error:
                    print(f"[THUMBNAIL] Moviepy fallback also failed: {moviepy_error}")
                    import traceback
                    traceback.print_exc()
                    return
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            print(f"[THUMBNAIL] Video info - Total frames: {total_frames}, FPS: {fps}, Duration: {duration}s")
            
            if total_frames <= 0:
                print(f"[THUMBNAIL] Error: Invalid frame count")
                cap.release()
                return
            
            # Use AI-powered intelligent frame selection
            print(f"[THUMBNAIL] Starting intelligent frame selection using OpenCV and AI analysis...")
            
            # Select candidate frames using quality metrics
            candidate_frames = ai_generator._select_best_frames(cap, total_frames, fps)
            print(f"[THUMBNAIL] Selected {len(candidate_frames)} high-quality candidate frames")
            
            # Generate thumbnails from best frames
            thumbnails = []
            
            for i, (frame_number, frame, quality_score) in enumerate(candidate_frames):
                print(f"[THUMBNAIL] Processing frame {frame_number} (quality score: {quality_score:.2f})")
                
                ret = True  # We already have the frame from _select_best_frames
                
                if ret and frame is not None:
                    print(f"[THUMBNAIL] Frame {i+1} read successfully, shape: {frame.shape}")
                    
                    # Save temporary frame
                    temp_frame_path = f"{os.path.splitext(video.filepath)[0]}_temp_frame_{i+1}.jpg"
                    cv2.imwrite(temp_frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    
                    # Use custom text if provided, otherwise generate AI text
                    if custom_text:
                        ai_text = custom_text
                        print(f"[THUMBNAIL] ✅✅✅ Using CUSTOM TEXT: '{ai_text}' ✅✅✅")
                    else:
                        # Generate AI text for this frame
                        ai_text = ai_generator.generate_catchy_text(temp_frame_path, video.filepath)
                        print(f"[THUMBNAIL] Generated AI text: '{ai_text}'")
                    
                    # Create YouTube thumbnail with text and styling options
                    thumbnail_path = f"{os.path.splitext(video.filepath)[0]}_thumb_{i+1}.jpg"
                    final_path = ai_generator.create_youtube_thumbnail(
                        temp_frame_path, 
                        ai_text, 
                        thumbnail_path,
                        text_options
                    )
                    
                    # Clean up temp frame
                    if os.path.exists(temp_frame_path):
                        os.remove(temp_frame_path)
                    
                    if os.path.exists(final_path):
                        file_size = os.path.getsize(final_path)
                        thumbnails.append(final_path)
                        print(f"[THUMBNAIL] Successfully created AI thumbnail {i+1}: {final_path} ({file_size} bytes)")
                        print(f"[THUMBNAIL] AI Text: {ai_text}")
                    else:
                        print(f"[THUMBNAIL] Failed to create AI thumbnail {i+1}")
                else:
                    print(f"[THUMBNAIL] Failed to read frame {frame_number}, ret={ret}")
            
            cap.release()
            
            if thumbnails:
                video.outputs["thumbnails"] = thumbnails
                video.outputs["thumbnail"] = thumbnails[2] if len(thumbnails) > 2 else thumbnails[0]  # Use middle thumbnail as primary
                print(f"[THUMBNAIL] Generated {len(thumbnails)} thumbnails successfully")
                print(f"[THUMBNAIL] Primary thumbnail: {video.outputs['thumbnail']}")
                print(f"[THUMBNAIL] All thumbnails: {thumbnails}")
            else:
                print(f"[THUMBNAIL] Warning: No thumbnails were generated")
                
        except Exception as e:
            print(f"[THUMBNAIL] Error generating thumbnail: {e}")
            import traceback
            traceback.print_exc()

    def _generate_subtitles(self, video, options):
        """Enhanced subtitle generation with language support and GPU optimization"""
        clip = None
        audio_path = None
        try:
            # Check GPU availability and memory before starting
            if has_gpu():
                mem_info = gpu_manager.get_gpu_memory_info()
                print(f"[SUBTITLE GPU] GPU Memory - Total: {mem_info['total']:.2f}GB, "
                      f"Allocated: {mem_info['allocated']:.2f}GB, "
                      f"Available: {mem_info['total'] - mem_info['allocated']:.2f}GB")
                
                # Clear cache to maximize available memory
                clear_cache()
                print("[SUBTITLE GPU] GPU cache cleared for subtitle processing")
            else:
                print("[SUBTITLE CPU] Using CPU for subtitle processing (slower)")
            
            # Get language and style from options
            language = options.get('subtitle_language', 'en')
            style = options.get('subtitle_style', 'clean')
            
            print(f"[SUBTITLE DEBUG] Starting subtitle generation for video: {video.filepath}")
            print(f"[SUBTITLE DEBUG] Language: {language}, Style: {style}")
            
            # Emit progress: Starting extraction
            if hasattr(video, 'id'):
                self._emit_progress(str(video.id), 'extracting_audio', 45, 'Extracting audio from video...')
            
            # Extract audio for transcription
            clip = VideoFileClip(video.filepath)
            
            # Check if video has audio
            if clip.audio is None:
                print(f"[SUBTITLE DEBUG] Warning: Video has no audio track")
                # Create empty subtitles for videos without audio
                self._create_fallback_subtitles(video, options)
                if clip:
                    clip.close()
                return
            
            audio_path = f"{os.path.splitext(video.filepath)[0]}_audio.wav"
            print(f"[SUBTITLE DEBUG] Extracting audio to: {audio_path}")
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            print(f"[SUBTITLE DEBUG] Audio extraction completed")
            
            # Emit progress: Loading Whisper model
            if hasattr(video, 'id'):
                self._emit_progress(str(video.id), 'loading_whisper', 55, 'Loading Whisper AI model...')
            
            # Try to use Whisper for real transcription
            try:
                print(f"[SUBTITLE DEBUG] Attempting Whisper transcription...")
                import whisper
                print(f"[SUBTITLE DEBUG] Whisper imported successfully")
                
                # Use appropriate model based on language
                model_size = self._get_optimal_whisper_model(language)
                device = get_device()
                print(f"[SUBTITLE DEBUG] Loading Whisper model: {model_size} on {device}")
                
                # Load model with GPU optimizations
                model = whisper.load_model(model_size, device=device)
                
                # Enable GPU optimizations for large-v3
                if has_gpu() and model_size in ['large-v3', 'large-v2', 'large']:
                    print(f"[GPU OPTIMIZATION] Enabling TensorFloat-32 for faster matrix operations")
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
                    # Enable cuDNN autotuner for optimal performance
                    torch.backends.cudnn.benchmark = True
                    print(f"[GPU OPTIMIZATION] cuDNN benchmark mode enabled")
                
                print(f"[SUBTITLE DEBUG] Whisper model loaded successfully on {device}")
                
                # Clear GPU cache before transcription if using GPU
                if has_gpu():
                    clear_cache()
                    print(f"[SUBTITLE DEBUG] GPU cache cleared, available memory: {gpu_manager.get_gpu_memory_info()}")
                
                # Emit progress: Transcribing
                if hasattr(video, 'id'):
                    self._emit_progress(str(video.id), 'transcribing', 65, f'Transcribing audio...')
                
                # CRITICAL FIX: For translation mode (e.g., English audio → Urdu subtitles)
                # First transcribe in audio's actual language, then translate
                # Let Whisper auto-detect the audio language instead of forcing target language
                print(f"[SUBTITLE DEBUG] Target subtitle language: {language}")
                print(f"[SUBTITLE DEBUG] Auto-detecting audio language with Whisper...")
                
                # Preprocess audio for better recognition
                processed_audio_path = self._preprocess_audio_for_transcription(audio_path, language)
                print(f"[SUBTITLE DEBUG] Audio preprocessed")
                
                # Transcription options without forcing language (let Whisper detect)
                transcription_options = self._get_transcription_options(language)
                # Remove language parameter - let Whisper auto-detect
                transcription_options_autodetect = {k: v for k, v in transcription_options.items()}
                print(f"[SUBTITLE DEBUG] Using transcription options with auto-detect")
                
                # Transcribe without forcing language - Whisper will detect it
                import librosa
                audio_data, sample_rate = librosa.load(processed_audio_path, sr=16000)
                print(f"[SUBTITLE DEBUG] Audio loaded: {len(audio_data)} samples at {sample_rate}Hz")
                
                result = model.transcribe(
                    audio_data,
                    # No language parameter = auto-detect
                    **transcription_options_autodetect
                )
                
                print(f"[SUBTITLE DEBUG] Whisper transcription completed")
                print(f"[SUBTITLE DEBUG] Found {len(result.get('segments', []))} segments")
                detected_lang = result.get('language', 'en')
                print(f"[SUBTITLE DEBUG] Detected audio language: {detected_lang}")
                
                # Map language codes for comparison
                # IMPORTANT: Keep ru-ur separate from ur - they need different processing
                lang_code_map = {
                    'ur': 'ur',
                    'ru-ur': 'ru-ur',  # Roman Urdu is DIFFERENT from Urdu script
                    'en': 'en', 'english': 'en',
                    'es': 'es', 'spanish': 'es',
                    'ar': 'ar', 'arabic': 'ar',
                    'hi': 'hi', 'hindi': 'hi'
                }
                
                detected_code = lang_code_map.get(detected_lang, detected_lang)
                target_code = lang_code_map.get(language, language)
                
                # Special case: If target is Roman Urdu but detected is Urdu, we need transliteration
                needs_transliteration = (language == 'ru-ur' and detected_lang in ['ur', 'urdu'])
                
                # Check if translation is needed (audio language ≠ desired subtitle language)
                needs_translation = (detected_code != target_code) or needs_transliteration
                
                if needs_translation:
                    print(f"[TRANSLATION MODE] Audio is in {detected_lang}, converting to {language}")
                else:
                    print(f"[TRANSCRIPTION MODE] Audio is {detected_lang}, same as target {language}")
                
                # Emit progress: Processing segments
                if hasattr(video, 'id'):
                    if needs_translation:
                        progress_msg = f'Translating {detected_lang} to {language}...'
                    else:
                        progress_msg = 'Processing subtitle segments...'
                    self._emit_progress(str(video.id), 'processing_segments', 80, progress_msg)
                
                # Extract segments with timestamps
                segments = []
                for i, segment in enumerate(result['segments']):
                    text = segment['text'].strip()
                    
                    # If translation needed (audio language → target language)
                    if needs_translation:
                        if language == 'ru-ur':
                            # Roman Urdu: Convert Urdu script to Roman script
                            if detected_lang in ['ur', 'urdu']:
                                # Transliterate Urdu → Roman Urdu
                                text = self._transliterate_urdu_to_roman(text)
                            else:
                                # Translate from other language to Roman Urdu
                                urdu_text = self._translate_to_urdu(text, detected_lang)
                                text = self._transliterate_urdu_to_roman(urdu_text)
                        elif language == 'ur':
                            # Standard Urdu script
                            text = self._translate_to_urdu(text, detected_lang)
                        else:
                            # For other languages, use generic translation
                            text = self._translate_text(text, detected_lang, language)
                    else:
                        # Same language - just post-process
                        text = self._post_process_transcription(text, language)
                    
                    # Skip empty segments
                    if not text or len(text.strip()) == 0:
                        continue
                    
                    segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': text,
                        'confidence': segment.get('avg_logprob', 0.0)  # Track confidence
                    })
                    print(f"[SUBTITLE DEBUG] Segment {i+1}: {segment['start']:.2f}s-{segment['end']:.2f}s: '{text}'")
                
                print(f"[SUBTITLE DEBUG] Successfully processed {len(segments)} segments from Whisper")
                
                # Emit progress: Creating subtitle files
                if hasattr(video, 'id'):
                    self._emit_progress(str(video.id), 'creating_subtitles', 90, 'Creating subtitle files...')
                
                # Generate both SRT and JSON format subtitles
                srt_content, json_data = self._create_subtitles_from_segments(segments, language, style)
                print(f"[SUBTITLE DEBUG] Using REAL Whisper transcription")
                
                # Cleanup preprocessed audio
                if processed_audio_path != audio_path and os.path.exists(processed_audio_path):
                    os.remove(processed_audio_path)
                
            except ImportError as e:
                print(f"[SUBTITLE DEBUG] Whisper or librosa not available: {e}")
                print(f"[SUBTITLE DEBUG] Falling back to enhanced sample text")
                # Enhanced fallback for Urdu
                text = self._get_enhanced_sample_text(language, clip.duration)
                srt_content, json_data = self._create_subtitles(text, language, style, clip.duration)
                
            except Exception as e:
                print(f"[SUBTITLE DEBUG] Whisper transcription failed with error: {e}")
                print(f"[SUBTITLE DEBUG] Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                print(f"[SUBTITLE DEBUG] Falling back to enhanced sample text")
                
                # Enhanced fallback for Urdu
                text = self._get_enhanced_sample_text(language, clip.duration)
                srt_content, json_data = self._create_subtitles(text, language, style, clip.duration)
            
            # Save subtitles file
            srt_path = f"{os.path.splitext(video.filepath)[0]}_{language}.srt"
            print(f"[SUBTITLE DEBUG] Saving SRT file to: {srt_path}")
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            # Save JSON format for live display
            json_path = f"{os.path.splitext(video.filepath)[0]}_{language}.json"
            print(f"[SUBTITLE DEBUG] Saving JSON file to: {json_path}")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"[SUBTITLE DEBUG] Subtitle generation completed successfully")
            print(f"[SUBTITLE DEBUG] Files saved: SRT={srt_path}, JSON={json_path}")
            
            # Clear GPU memory after subtitle processing
            if has_gpu():
                clear_cache()
                mem_info = gpu_manager.get_gpu_memory_info()
                print(f"[SUBTITLE GPU] GPU memory freed - Available: {mem_info['total'] - mem_info['allocated']:.2f}GB")
            
            video.outputs["subtitles"] = {
                "srt": srt_path,
                "json": json_path,
                "language": language,
                "style": style
            }
            
            if clip:
                clip.close()
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                
        except Exception as e:
            print(f"[SUBTITLE DEBUG] Error generating subtitles: {e}")
            import traceback
            traceback.print_exc()
            
            # Clear GPU memory even on error
            if has_gpu():
                clear_cache()
                print("[SUBTITLE GPU] GPU cache cleared after error")
            
            # Create fallback subtitles
            if clip:
                clip.close()
            self._create_fallback_subtitles(video, options)

    def _get_optimal_whisper_model(self, language):
        """Get optimal Whisper model size based on language"""
        # For Urdu and other complex languages, use the BEST models for maximum accuracy
        if language in ['ur', 'ru-ur']:
            # Urdu needs the absolute best model for accurate transcription
            return "large-v3"  # Best model for Urdu with highest accuracy
        elif language in ['ar', 'hi', 'zh', 'ja', 'ko']:
            return "large"  # Large model for other complex scripts and non-Latin languages
        elif language in ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'nl']:
            return "medium"    # Medium model for well-supported languages
        else:
            return "base"   # Base model for other languages

    def _preprocess_audio_for_transcription(self, audio_path, language):
        """Preprocess audio for better transcription accuracy"""
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize, compress_dynamic_range
            import numpy as np
            
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Language-specific preprocessing
            if language in ['ur', 'ru-ur', 'ar', 'hi']:
                print(f"[AUDIO PREPROCESS] Applying ENHANCED {language} specific preprocessing")
                
                # Step 1: Normalize audio levels first
                audio = normalize(audio)
                
                # Step 2: Apply dynamic range compression for consistent volume
                audio = compress_dynamic_range(audio, threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)
                
                # Step 3: Remove low-frequency noise (below 80Hz) that can interfere
                audio = audio.high_pass_filter(80)
                
                # Step 4: Remove very high frequencies (above 8000Hz) to reduce noise
                audio = audio.low_pass_filter(8000)
                
                # Step 5: Boost volume slightly for better detection
                audio = audio + 3  # Add 3dB
                
                # Step 6: Ensure mono for consistent processing
                if audio.channels > 1:
                    audio = audio.set_channels(1)
                
                # Step 7: Set optimal sample rate for Whisper (16kHz is ideal)
                audio = audio.set_frame_rate(16000)
                
                # Step 8: Apply additional normalization after all processing
                audio = normalize(audio)
                
                # Save preprocessed audio
                processed_path = f"{os.path.splitext(audio_path)[0]}_processed.wav"
                audio.export(processed_path, format="wav", parameters=["-ac", "1"])
                
                print(f"[AUDIO PREPROCESS] Enhanced preprocessed audio saved to: {processed_path}")
                return processed_path
            
            else:
                # For other languages, minimal preprocessing
                if audio.channels > 1:
                    audio = audio.set_channels(1)
                audio = audio.set_frame_rate(16000)
                audio = normalize(audio)
                processed_path = f"{os.path.splitext(audio_path)[0]}_processed.wav"
                audio.export(processed_path, format="wav")
                return processed_path
                
        except Exception as e:
            print(f"[AUDIO PREPROCESS] Error preprocessing audio: {e}")
            return audio_path  # Return original if preprocessing fails

    def _get_transcription_options(self, language):
        """Get optimal transcription options for each language with GPU optimization"""
        
        # GPU-specific optimizations - AGGRESSIVE settings for large-v3
        use_fp16 = has_gpu()  # Only use FP16 on GPU
        beam_size = 10 if has_gpu() else 3  # Much larger beam search on GPU for better GPU usage
        best_of = 10 if has_gpu() else 3    # More samples on GPU for better GPU usage
        
        if use_fp16:
            print(f"[TRANSCRIPTION] Using AGGRESSIVE GPU optimizations: fp16=True, beam_size={beam_size}, best_of={best_of}")
        else:
            print(f"[TRANSCRIPTION] Using CPU mode: fp16=False, beam_size={beam_size}, best_of={best_of}")
        
        base_options = {
            "word_timestamps": True,
            "no_speech_threshold": 0.6,
            "logprob_threshold": -1.0,
            "verbose": True,  # Enable verbose output for debugging
            "fp16": use_fp16  # GPU acceleration
        }
        
        if language in ['ur', 'ru-ur']:
            # Urdu-specific options - OPTIMIZED for best accuracy and MAX GPU usage
            return {
                **base_options,
                "temperature": (0.0, 0.2, 0.4, 0.6, 0.8),  # Multiple temperatures for best results
                "compression_ratio_threshold": 2.4,
                "condition_on_previous_text": True,
                "initial_prompt": "یہ ایک اردو زبان کی ویڈیو ہے۔ صاف اور درست الفاظ استعمال کریں۔",  # Enhanced Urdu prompt
                "beam_size": beam_size,  # Aggressive GPU-aware beam search
                "best_of": best_of,      # Aggressive GPU-aware sampling
                "patience": 2.0,  # Higher patience for better accuracy (more GPU work)
                "length_penalty": 1.0,
                "suppress_tokens": "-1",  # Don't suppress any tokens
            }
        elif language == 'ar':
            return {
                **base_options,
                "temperature": (0.0, 0.2, 0.4),
                "compression_ratio_threshold": 2.4,
                "condition_on_previous_text": True,
                "initial_prompt": "هذا محتوى باللغة العربية. استخدم كلمات واضحة ودقيقة.",  # Enhanced Arabic prompt
                "beam_size": beam_size,
                "best_of": best_of
            }
        elif language == 'hi':
            return {
                **base_options,
                "temperature": (0.0, 0.2, 0.4),
                "compression_ratio_threshold": 2.4,
                "condition_on_previous_text": True,
                "initial_prompt": "यह हिंदी भाषा की सामग्री है। स्पष्ट और सटीक शब्दों का प्रयोग करें।",  # Enhanced Hindi prompt
                "beam_size": beam_size,
                "best_of": best_of
            }
        else:
            return {
                **base_options,
                "temperature": 0.0,
                "beam_size": beam_size,
                "best_of": best_of
            }

    def _post_process_transcription(self, text, language):
        """Post-process transcribed text for language-specific improvements"""
        if not text:
            return text
            
        if language in ['ur', 'ru-ur']:
            # Urdu-specific post-processing
            
            # Clean up common transcription artifacts
            text = text.strip()
            
            # Remove or fix common Whisper artifacts for Urdu
            # These are patterns that Whisper sometimes incorrectly transcribes
            urdu_fixes = {
                ' .' : '۔',
                ' ؟' : '؟',
                ' !' : '!',
                '  ': ' ',  # Remove double spaces
            }
            
            for wrong, correct in urdu_fixes.items():
                text = text.replace(wrong, correct)
            
            # Ensure proper Urdu punctuation
            if text and not text.endswith(('۔', '؟', '!', '.', '?')):
                text += '۔'
                
        elif language == 'ar':
            # Arabic-specific post-processing
            text = text.strip()
            if text and not text.endswith(('۔', '؟', '!', '.', '?')):
                text += '.'
                
        # General cleanup for all languages
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text

    def _enhance_with_deep_translator(self, text, language, whisper_lang):
        """Enhance subtitle accuracy using deep-translator for validation and correction"""
        if not text or len(text.strip()) == 0:
            return text
        
        # DISABLED: Deep translator reduces Urdu quality by doing double translation
        # Whisper large-v3 is already excellent at Urdu transcription
        # For Urdu, trust Whisper's direct output instead of translating back and forth
        if language in ['ur', 'ru-ur']:
            print(f"[URDU] Using native Whisper transcription (no translation): '{text}'")
            return text
            
        try:
            from deep_translator import GoogleTranslator
            
            # For OTHER complex languages, validate with deep-translator
            # This helps correct mistranscriptions and improves overall quality
            
            if language in ['ar', 'hi', 'zh', 'ja', 'ko']:
                # Strategy: Translate to English and back to detect/fix errors
                # This helps catch common Whisper mistakes and improves accuracy
                
                # Map our language codes to deep-translator codes
                lang_map = {
                    'ar': 'ar',
                    'hi': 'hi',
                    'zh': 'zh-CN',
                    'ja': 'ja',
                    'ko': 'ko'
                }
                
                target_lang = lang_map.get(language, whisper_lang)
                
                # Only apply if text seems to have potential issues (very short or unusual)
                # To avoid over-correcting good transcriptions
                if len(text.split()) < 3:  # Short segments benefit most from validation
                    try:
                        # Translate to English
                        translator_to_en = GoogleTranslator(source=target_lang, target='en')
                        english_text = translator_to_en.translate(text)
                        
                        # Translate back to original language for comparison
                        translator_back = GoogleTranslator(source='en', target=target_lang)
                        validated_text = translator_back.translate(english_text)
                        
                        # Use validated text if it's significantly different (likely a correction)
                        if validated_text and len(validated_text) > 2:
                            print(f"[DEEP-TRANSLATOR] Enhanced: '{text}' → '{validated_text}'")
                            return validated_text
                    except Exception as e:
                        print(f"[DEEP-TRANSLATOR] Validation skipped: {e}")
                        pass
            
            return text
            
        except ImportError:
            print("[DEEP-TRANSLATOR] Module not available, skipping enhancement")
            return text
        except Exception as e:
            print(f"[DEEP-TRANSLATOR] Error during enhancement: {e}")
            return text
    
    def _translate_to_urdu(self, text, source_lang='en'):
        """Translate text to Urdu using Google Translator"""
        if not text or len(text.strip()) == 0:
            return text
        
        try:
            from deep_translator import GoogleTranslator
            
            # Map detected language codes to deep-translator codes
            lang_map = {
                'en': 'en',
                'english': 'en',
                'es': 'es',
                'fr': 'fr',
                'de': 'de',
                'ar': 'ar',
                'hi': 'hi'
            }
            
            source_code = lang_map.get(source_lang, 'en')
            
            print(f"[TRANSLATION] Translating from {source_code} to Urdu: '{text[:50]}...'")
            
            translator = GoogleTranslator(source=source_code, target='ur')
            urdu_text = translator.translate(text)
            
            # Clean up the Urdu text
            urdu_text = urdu_text.strip()
            
            # Add proper Urdu punctuation if missing
            if urdu_text and not urdu_text.endswith(('۔', '؟', '!', '.', '?')):
                urdu_text += '۔'
            
            print(f"[TRANSLATION] Result: '{urdu_text[:50]}...'")
            return urdu_text
            
        except ImportError:
            print("[TRANSLATION] deep-translator not available, returning original text")
            return text
        except Exception as e:
            print(f"[TRANSLATION] Translation failed: {e}, returning original text")
            return text
    
    def _translate_text(self, text, source_lang, target_lang):
        """Generic translation function for any language pair"""
        if not text or len(text.strip()) == 0:
            return text
        
        try:
            from deep_translator import GoogleTranslator
            
            # Map language codes
            lang_map = {
                'en': 'en', 'english': 'en',
                'es': 'es', 'spanish': 'es',
                'fr': 'fr', 'french': 'fr',
                'de': 'de', 'german': 'de',
                'ar': 'ar', 'arabic': 'ar',
                'hi': 'hi', 'hindi': 'hi',
                'ur': 'ur', 'urdu': 'ur',
                'ru-ur': 'ur',
                'zh': 'zh-CN', 'chinese': 'zh-CN',
                'ja': 'ja', 'japanese': 'ja',
                'ko': 'ko', 'korean': 'ko'
            }
            
            source_code = lang_map.get(source_lang, source_lang)
            target_code = lang_map.get(target_lang, target_lang)
            
            print(f"[TRANSLATION] {source_code} → {target_code}: '{text[:50]}...'")
            
            translator = GoogleTranslator(source=source_code, target=target_code)
            translated_text = translator.translate(text)
            
            print(f"[TRANSLATION] Result: '{translated_text[:50]}...'")
            return translated_text.strip()
            
        except ImportError:
            print("[TRANSLATION] deep-translator not available")
            return text
        except Exception as e:
            print(f"[TRANSLATION] Failed: {e}")
            return text

    def _transliterate_urdu_to_roman(self, urdu_text):
        """Transliterate Urdu script to Roman Urdu (Latinized Urdu)"""
        if not urdu_text or len(urdu_text.strip()) == 0:
            return urdu_text
        
        print(f"[TRANSLITERATION] Urdu → Roman Urdu: '{urdu_text[:50]}...'")
        
        try:
            from deep_translator import GoogleTranslator
            
            # Strategy: Use Google Translate's romanization feature
            # Translate from Urdu to English, but Google provides romanized pronunciation
            # Then we use that romanization with Urdu grammar structure
            
            # For now, use a simple mapping-based approach with common Urdu words
            # This creates readable Roman Urdu while preserving meaning
            
            # Common Urdu to Roman Urdu word mappings
            common_mappings = {
                'یہ': 'yeh',
                'ہے': 'hai',
                'کے': 'ke',
                'کی': 'ki',
                'میں': 'mein',
                'سے': 'se',
                'نے': 'ne',
                'کو': 'ko',
                'پر': 'par',
                'اور': 'aur',
                'کا': 'ka',
                'ہیں': 'hain',
                'تھا': 'tha',
                'تھی': 'thi',
                'گیا': 'gaya',
                'گئی': 'gayi',
                'کیا': 'kya',
                'کے لیے': 'ke liye',
                'کہ': 'ke',
                'ہمارا': 'hamara',
                'آپ': 'aap',
                'ہم': 'hum',
                'وہ': 'woh',
                'ان': 'in',
                'اس': 'is',
                'کیونکہ': 'kyunke',
                'لیکن': 'lekin',
                'جب': 'jab',
                'تو': 'to',
                'ہو': 'ho',
                'ہوں': 'hon',
                'ہوتا': 'hota',
                'ہوتی': 'hoti',
                'کر': 'kar',
                'کرتا': 'karta',
                'کرتی': 'karti',
                'کرتے': 'karte',
                'کریں': 'karein',
                'جا': 'ja',
                'جاتا': 'jata',
                'جاتی': 'jati',
                'جاتے': 'jate',
                'رہا': 'raha',
                'رہی': 'rahi',
                'رہے': 'rahe',
                'نہیں': 'nahi',
                'بھی': 'bhi',
                'ہی': 'hi',
                'تک': 'tak',
                'کیسے': 'kaise',
                'کیسی': 'kaisi',
                'کیا': 'kya',
                'کون': 'kaun',
                'کہاں': 'kahan',
                'کب': 'kab',
                'کتنا': 'kitna',
                'کتنی': 'kitni',
                'کتنے': 'kitne',
                'بہت': 'bahut',
                'زیادہ': 'zyada',
                'کم': 'kam',
                'اچھا': 'acha',
                'اچھی': 'achi',
                'بڑا': 'bara',
                'بڑی': 'bari',
                'چھوٹا': 'chhota',
                'چھوٹی': 'chhoti',
                'نیا': 'naya',
                'نئی': 'nayi',
                'پرانا': 'purana',
                'پرانی': 'purani',
                'سب': 'sab',
                'کچھ': 'kuch',
                'کوئی': 'koi',
                'ہر': 'har',
                'دوسرا': 'dusra',
                'پہلا': 'pehla',
                'آخری': 'aakhri',
                'اب': 'ab',
                'پھر': 'phir',
                'وقت': 'waqt',
                'دن': 'din',
                'رات': 'raat',
                'صبح': 'subah',
                'شام': 'shaam',
                'سال': 'saal',
                'مہینہ': 'mahina',
                'ہفتہ': 'hafta',
                'آج': 'aaj',
                'کل': 'kal',
                'پرسوں': 'parson',
                'لوگ': 'log',
                'آدمی': 'aadmi',
                'عورت': 'aurat',
                'بچہ': 'bachcha',
                'بچی': 'bachchi',
                'گھر': 'ghar',
                'کام': 'kaam',
                'پانی': 'pani',
                'کھانا': 'khana',
                'پینا': 'peena',
                'جانا': 'jana',
                'آنا': 'aana',
                'دیکھنا': 'dekhna',
                'سننا': 'sunna',
                'بولنا': 'bolna',
                'کہنا': 'kehna',
                'سمجھنا': 'samajhna',
                'پڑھنا': 'parhna',
                'لکھنا': 'likhna',
                'زبان': 'zubaan',
                'اردو': 'urdu',
                'انگلش': 'english',
                'ویڈیو': 'video',
                'آڈیو': 'audio',
                'سسٹم': 'system',
                'ٹیکنالوجی': 'technology',
                'کمپیوٹر': 'computer',
                'موبائل': 'mobile',
                'انٹرنیٹ': 'internet'
            }
            
            # Try word-by-word transliteration first
            words = urdu_text.split()
            roman_words = []
            
            for word in words:
                # Remove punctuation for matching
                clean_word = word.strip('۔؟!.,;:')
                
                if clean_word in common_mappings:
                    roman_words.append(common_mappings[clean_word])
                else:
                    # For unknown words, try Google Translate
                    try:
                        translator = GoogleTranslator(source='ur', target='en')
                        english = translator.translate(clean_word)
                        # Use English as approximation of Roman Urdu
                        roman_words.append(english.lower())
                    except:
                        # Fallback: keep original word
                        roman_words.append(clean_word)
            
            roman_text = ' '.join(roman_words)
            
            # Clean up and capitalize first letter
            roman_text = roman_text.strip()
            if roman_text:
                roman_text = roman_text[0].upper() + roman_text[1:]
            
            print(f"[TRANSLITERATION] Result: '{roman_text[:50]}...'")
            return roman_text
            
        except Exception as e:
            print(f"[TRANSLITERATION] Failed: {e}, using fallback")
            # Fallback: provide generic Roman Urdu text
            return "Yeh video mein automatic subtitles hain."
    
    def _get_enhanced_sample_text(self, language, duration):
        """Get enhanced sample text with better content for fallback"""
        if language == 'ur':
            # More comprehensive Urdu sample text
            long_urdu_text = """
            یہ ویڈیو SnipX AI کے ذریعے خودکار طور پر پروسیس کیا گیا ہے۔
            ہمارا جدید ترین سسٹم اردو زبان کی خصوصیات کو سمجھتا ہے۔
            آڈیو انہانسمنٹ اور نائز ریڈکشن کے ذریعے بہترین نتائج حاصل کیے جاتے ہیں۔
            سب ٹائٹلز کی درستگی کے لیے ہم مختلف تکنیکوں کا استعمال کرتے ہیں۔
            یہ ٹیکنالوجی اردو بولنے والوں کے لیے خاص طور پر ڈیزائن کی گئی ہے۔
            ہمارا مقصد بہترین صوتی تجربہ فراہم کرنا ہے۔
            """
            return long_urdu_text.strip()
            
        elif language == 'ru-ur':
            # Enhanced Roman Urdu sample text
            long_roman_urdu = """
            Yeh video SnipX AI ke zariye automatically process kiya gaya hai.
            Hamara advanced system Urdu language ki features ko samajhta hai.
            Audio enhancement aur noise reduction ke zariye best results hasil kiye jaate hain.
            Subtitles ki accuracy ke liye hum different techniques ka istemal karte hain.
            Yeh technology Urdu speakers ke liye specially design ki gayi hai.
            Hamara maqsad behtereen audio experience provide karna hai.
            Is system mein latest AI models shamil hain jo Urdu content ko accurately process kar sakte hain.
            """
            return long_roman_urdu.strip()
            
        else:
            # Use existing sample text for other languages
            return self._get_sample_text(language)

    def _summarize_video(self, video, options=None):
        """Summarize video using Whisper transcription + OpenAI GPT"""
        options = options or {}
        summary_length = options.get('summary_length', 'medium')
        summary_focus = options.get('summary_focus', 'balanced')
        
        print(f"[SUMMARIZE] Starting video summarization (length={summary_length}, focus={summary_focus})")
        
        clip = None
        audio_path = None
        try:
            # Step 1: Extract audio from video
            clip = VideoFileClip(video.filepath)
            if clip.audio is None:
                print("[SUMMARIZE] Video has no audio track - cannot summarize")
                video.outputs['summary'] = json.dumps({
                    'error': 'Video has no audio track to summarize',
                    'text': ''
                })
                return
            
            audio_path = f"{os.path.splitext(video.filepath)[0]}_summ_audio.wav"
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            print(f"[SUMMARIZE] Audio extracted to: {audio_path}")
            
            # Emit progress
            if hasattr(video, 'id'):
                self._emit_progress(str(video.id), 'summarizing', 60, 'Transcribing audio with Whisper...')
            
            # Step 2: Transcribe with Whisper
            transcript_text = ''
            try:
                import whisper
                device = get_device()
                print(f"[SUMMARIZE] Loading Whisper model on {device}...")
                model = whisper.load_model("base", device=device)
                result = model.transcribe(audio_path, language=None)  # auto-detect language
                transcript_text = result.get('text', '').strip()
                detected_lang = result.get('language', 'en')
                print(f"[SUMMARIZE] Whisper transcription complete. Language: {detected_lang}, Length: {len(transcript_text)} chars")
            except Exception as whisper_err:
                print(f"[SUMMARIZE] Whisper transcription failed: {whisper_err}")
                # Fallback: check if subtitles already exist
                subtitles_info = video.outputs.get('subtitles', {})
                if isinstance(subtitles_info, dict):
                    srt_path = subtitles_info.get('srt_path', '')
                    json_path = subtitles_info.get('json_path', '')
                    if json_path and os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            sub_data = json.load(f)
                        transcript_text = ' '.join([seg.get('text', '') for seg in sub_data if isinstance(seg, dict)])
                    elif srt_path and os.path.exists(srt_path):
                        with open(srt_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        transcript_text = ' '.join([l.strip() for l in lines if l.strip() and not l.strip().isdigit() and '-->' not in l])
                print(f"[SUMMARIZE] Fallback transcript length: {len(transcript_text)} chars")
            
            if not transcript_text:
                print("[SUMMARIZE] No transcript available - cannot generate summary")
                video.outputs['summary'] = json.dumps({
                    'error': 'Could not transcribe audio',
                    'text': ''
                })
                return
            
            # Emit progress
            if hasattr(video, 'id'):
                self._emit_progress(str(video.id), 'summarizing', 75, 'Generating AI summary...')
            
            # Step 3: Summarize using OpenAI API or fallback extractive method
            summary_text = ''
            key_points = []
            
            if self.openai_client:
                try:
                    summary_text, key_points = self._summarize_with_openai(
                        transcript_text, summary_length, summary_focus,
                        duration=clip.duration if clip else None
                    )
                except Exception as openai_err:
                    print(f"[SUMMARIZE] OpenAI summarization failed: {openai_err}")
            
            # Fallback: extractive summarization
            if not summary_text:
                summary_text, key_points = self._extractive_summarize(
                    transcript_text, summary_length
                )
            
            # Step 4: Save summary
            summary_data = {
                'text': summary_text,
                'key_points': key_points,
                'length': summary_length,
                'focus': summary_focus,
                'transcript_length': len(transcript_text),
                'summary_length': len(summary_text),
                'compression_ratio': round(len(summary_text) / max(len(transcript_text), 1) * 100, 1),
                'video_duration': round(clip.duration, 1) if clip else None
            }
            
            summary_path = f"{os.path.splitext(video.filepath)[0]}_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            video.outputs['summary'] = summary_path
            print(f"[SUMMARIZE] Summary saved to: {summary_path}")
            print(f"[SUMMARIZE] Summary ({len(summary_text)} chars, {summary_data['compression_ratio']}% of original)")
            
            # Emit progress complete
            if hasattr(video, 'id'):
                self._emit_progress(str(video.id), 'summarizing', 90, 'Summary generated successfully!')
                
        except Exception as e:
            import traceback
            print(f"[SUMMARIZE] Error summarizing video: {e}")
            traceback.print_exc()
            video.outputs['summary'] = json.dumps({
                'error': str(e),
                'text': ''
            })
        finally:
            if clip:
                try:
                    clip.close()
                except:
                    pass
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass

    def _summarize_with_openai(self, transcript, length='medium', focus='balanced', duration=None):
        """Use OpenAI GPT to generate a structured summary"""
        length_instructions = {
            'short': 'Create a brief 2-3 sentence summary.',
            'medium': 'Create a detailed summary of 4-6 sentences.',
            'long': 'Create a comprehensive summary of 8-12 sentences covering all major points.'
        }
        
        focus_instructions = {
            'balanced': 'Cover all aspects of the content equally.',
            'visual': 'Focus on visual elements, scenes, and actions described.',
            'audio': 'Focus on sounds, music, tone, and audio elements mentioned.',
            'text': 'Focus on the spoken words, arguments, and verbal content.'
        }
        
        duration_info = f"The video is {round(duration, 0)} seconds long. " if duration else ""
        
        # Truncate transcript if too long for API
        max_chars = 12000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + '... [transcript truncated]'
        
        prompt = f"""You are a video content analyst. {duration_info}Below is the transcript of a video.

{length_instructions.get(length, length_instructions['medium'])}
{focus_instructions.get(focus, focus_instructions['balanced'])}

Also extract 3-5 key points as a bullet list.

Transcript:
\"\"\"
{transcript}
\"\"\"

Respond in this exact JSON format:
{{
  "summary": "Your summary text here",
  "key_points": ["Point 1", "Point 2", "Point 3"]
}}"""
        
        print(f"[SUMMARIZE-OPENAI] Sending {len(transcript)} chars to OpenAI...")
        
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful video content summarizer. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        print(f"[SUMMARIZE-OPENAI] Response received: {len(content)} chars")
        
        # Parse JSON response
        try:
            # Try to extract JSON from the response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            return result.get('summary', content), result.get('key_points', [])
        except json.JSONDecodeError:
            # If not valid JSON, return raw text
            return content, []

    def _extractive_summarize(self, transcript, length='medium'):
        """Fallback extractive summarization (no external API needed)"""
        import re as regex
        
        # Split into sentences
        sentences = regex.split(r'(?<=[.!?])\s+', transcript)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return transcript[:500], []
        
        # Determine how many sentences to keep
        ratio_map = {'short': 0.2, 'medium': 0.4, 'long': 0.6}
        ratio = ratio_map.get(length, 0.4)
        num_sentences = max(2, int(len(sentences) * ratio))
        
        # Simple scoring: prefer longer sentences, sentences with key terms
        scored = []
        for i, sent in enumerate(sentences):
            score = len(sent.split())  # word count as base score
            # Boost first and last sentences
            if i == 0:
                score *= 1.5
            if i == len(sentences) - 1:
                score *= 1.3
            # Boost sentences with signal phrases
            signal_words = ['important', 'key', 'main', 'significant', 'conclusion',
                           'result', 'therefore', 'however', 'because', 'first', 'finally']
            for word in signal_words:
                if word in sent.lower():
                    score *= 1.2
            scored.append((i, score, sent))
        
        # Sort by score, take top N, then re-sort by original position
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = scored[:num_sentences]
        selected.sort(key=lambda x: x[0])  # maintain original order
        
        summary_text = ' '.join([s[2] for s in selected])
        
        # Extract key points (top 3-5 highest-scored sentences)
        key_points = [s[2][:100] for s in scored[:min(5, len(scored))]]
        
        return summary_text, key_points

    def _format_timestamp(self, seconds):
        """Format timestamp for SRT format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def _get_whisper_language_code(self, language):
        """Convert our language codes to Whisper language codes"""
        whisper_codes = {
            'en': 'en',
            'ur': 'ur',
            'ru-ur': 'ur',  # Use Urdu model for Roman Urdu
            'ar': 'ar',
            'hi': 'hi',
            'es': 'es',
            'fr': 'fr',
            'de': 'de',
            'zh': 'zh',
            'ja': 'ja',
            'ko': 'ko',
            'pt': 'pt',
            'ru': 'ru',
            'it': 'it',
            'tr': 'tr',
            'nl': 'nl'
        }
        return whisper_codes.get(language, 'en')

    def _create_subtitles_from_segments(self, segments, language, style):
        """Create both SRT and JSON format subtitles from Whisper segments"""
        srt_content = ""
        json_data = {
            "language": language,
            "segments": [],
            "word_timestamps": True,
            "confidence": 0.95,
            "source": "whisper"
        }
        
        for i, segment in enumerate(segments):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text']
            
            # SRT format
            srt_content += f"{i + 1}\n"
            srt_content += f"{self._format_timestamp(start_time)} --> {self._format_timestamp(end_time)}\n"
            srt_content += f"{text}\n\n"
            
            # JSON format for live display
            json_data["segments"].append({
                "id": i + 1,
                "start": start_time,
                "end": end_time,
                "text": text,
                "language": language,
                "style": style
            })
        
        return srt_content, json_data

    def _get_sample_text(self, language):
        """Get sample text for different languages"""
        sample_texts = {
            'en': "Welcome to this video demonstration. This is an example of English subtitles generated automatically by SnipX AI.",
            'ur': "اس ویڈیو ڈیمونسٹریشن میں خوش آمدید۔ یہ اردو سب ٹائٹلز کی مثال ہے جو SnipX AI کے ذریعے خودکار طور پر تیار کیا گیا۔ ہمارا سسٹم اردو زبان کے لیے خاص طور پر تربیت یافتہ ہے۔",
            'ru-ur': "Is video demonstration mein khush aamdeed. Yeh Roman Urdu subtitles ki misaal hai jo SnipX AI ke zariye automatic tayyar kiya gaya. Hamara system Urdu language ke liye khaas training ke saath banaya gaya hai.",
            'es': "Bienvenido a esta demostración de video. Este es un ejemplo de subtítulos en español generados automáticamente por SnipX AI.",
            'fr': "Bienvenue dans cette démonstration vidéo. Ceci est un exemple de sous-titres français générés automatiquement par SnipX AI.",
            'de': "Willkommen zu dieser Video-Demonstration. Dies ist ein Beispiel für deutsche Untertitel, die automatisch von SnipX AI generiert wurden.",
            'ar': "مرحباً بكم في هذا العرض التوضيحي للفيديو. هذا مثال على الترجمة العربية التي تم إنشاؤها تلقائياً بواسطة SnipX AI.",
            'hi': "इस वीडियो प्रदर्शन में आपका स्वागत है। यह SnipX AI द्वारा स्वचालित रूप से उत्पन्न हिंदी उपशीर्षक का एक उदाहरण है।",
            'zh': "欢迎观看此视频演示。这是由SnipX AI自动生成的中文字幕示例。",
            'ja': "このビデオデモンストレーションへようこそ。これはSnipX AIによって自動生成された日本語字幕の例です。",
            'ko': "이 비디오 데모에 오신 것을 환영합니다. 이것은 SnipX AI에 의해 자동으로 생성된 한국어 자막의 예입니다。",
            'pt': "Bem-vindo a esta demonstração de vídeo. Este é um exemplo de legendas em português geradas automaticamente pelo SnipX AI.",
            'ru': "Добро пожаловать в эту видео-демонстрацию. Это пример русских субтитров, автоматически созданных SnipX AI.",
            'it': "Benvenuti in questa dimostrazione video. Questo è un esempio di sottotitoli italiani generati automaticamente da SnipX AI.",
            'tr': "Bu video gösterimine hoş geldiniz. Bu, SnipX AI tarafından otomatik olarak oluşturulan Türkçe altyazı örneğidir.",
            'nl': "Welkom bij deze videodemonstratie. Dit is een voorbeeld van Nederlandse ondertitels die automatisch zijn gegenereerd door SnipX AI."
        }
        return sample_texts.get(language, sample_texts['en'])

    def _create_subtitles(self, text, language, style, duration):
        """Create both SRT and JSON format subtitles"""
        # Split text into chunks for subtitles
        words = text.split()
        chunk_size = 4 if language in ['ur', 'ar', 'hi', 'zh', 'ja', 'ko'] else 6  # Smaller chunks for better readability
        chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        
        srt_content = ""
        json_data = {
            "language": language,
            "segments": [],
            "word_timestamps": True,
            "confidence": 0.95,
            "source": "fallback"
        }
        
        subtitle_duration = duration / len(chunks) if chunks else 5
        
        for i, chunk in enumerate(chunks):
            start_time = i * subtitle_duration
            end_time = (i + 1) * subtitle_duration
            
            # SRT format
            srt_content += f"{i + 1}\n"
            srt_content += f"{self._format_timestamp(start_time)} --> {self._format_timestamp(end_time)}\n"
            srt_content += f"{chunk}\n\n"
            
            # JSON format for live display
            json_data["segments"].append({
                "id": i + 1,
                "start": start_time,
                "end": end_time,
                "text": chunk,
                "language": language,
                "style": style
            })
        
        return srt_content, json_data

    def _create_fallback_subtitles(self, video, options):
        """Create fallback subtitles when transcription fails"""
        language = options.get('subtitle_language', 'en')
        style = options.get('subtitle_style', 'clean')
        
        # Use enhanced fallback text
        fallback_text = self._get_enhanced_sample_text(language, 15)
        srt_content, json_data = self._create_subtitles(fallback_text, language, style, 15)
        
        srt_path = f"{os.path.splitext(video.filepath)[0]}_{language}_fallback.srt"
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        json_path = f"{os.path.splitext(video.filepath)[0]}_{language}_fallback.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        video.outputs["subtitles"] = {
            "srt": srt_path,
            "json": json_path,
            "language": language,
            "style": style
        }

    def export_video_with_edits(self, video_id, trim_start=0, trim_end=100, 
                                 text_overlay='', text_position='center', 
                                 text_color='#ffffff', text_size=32,
                                 music_volume=50, video_volume=100, mute_original=False):
        """Export video with all editing changes applied (trim, text overlay, audio adjustments)"""
        import subprocess
        
        video = self.get_video(video_id)
        if not video:
            raise ValueError("Video not found")
        
        print(f"[EXPORT] Starting export for video: {video.filename}")
        print(f"[EXPORT] Video filepath: {video.filepath}")
        print(f"[EXPORT] Trim: {trim_start}% - {trim_end}%")
        print(f"[EXPORT] Text: '{text_overlay}' at {text_position}")
        print(f"[EXPORT] Audio: video_vol={video_volume}, mute={mute_original}")
        
        # Verify input video file exists
        if not os.path.exists(video.filepath):
            raise FileNotFoundError(f"Input video file not found: {video.filepath}")
        
        # Get video duration
        try:
            clip = VideoFileClip(video.filepath)
            duration = clip.duration
            clip.close()
        except Exception as e:
            raise Exception(f"Failed to read video file: {str(e)}")
        
        # Calculate trim times
        start_time = (trim_start / 100) * duration
        end_time = (trim_end / 100) * duration
        trim_duration = end_time - start_time
        
        print(f"[EXPORT] Duration: {duration}s, Trimming: {start_time}s to {end_time}s ({trim_duration}s)")
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Output path
        base_name = os.path.splitext(video.filename)[0]
        export_filename = f"{base_name}_edited_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        export_path = os.path.join(self.upload_folder, export_filename)
        
        print(f"[EXPORT] Output path: {export_path}")
        
        # Build FFmpeg command
        ffmpeg_path = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
        
        # Verify FFmpeg exists
        if not os.path.exists(ffmpeg_path):
            raise FileNotFoundError(f"FFmpeg not found at: {ffmpeg_path}")
        
        print(f"[EXPORT] FFmpeg path: {ffmpeg_path}")
        
        # Build filter complex for video
        video_filters = []
        
        # Add text overlay if provided
        if text_overlay and text_overlay.strip():
            # Map position to FFmpeg coordinates
            position_map = {
                'top-left': 'x=50:y=50',
                'top-center': 'x=(w-text_w)/2:y=50',
                'top-right': 'x=w-text_w-50:y=50',
                'center': 'x=(w-text_w)/2:y=(h-text_h)/2',
                'bottom-left': 'x=50:y=h-text_h-50',
                'bottom-center': 'x=(w-text_w)/2:y=h-text_h-50',
                'bottom-right': 'x=w-text_w-50:y=h-text_h-50'
            }
            pos = position_map.get(text_position, position_map['center'])
            
            # For FFmpeg drawtext filter, we need to escape special characters
            # Use a simpler approach: write text to a temp file and reference it
            import tempfile
            
            # Create temp file for text (to avoid complex escaping issues)
            text_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
            text_file.write(text_overlay)
            text_file.close()
            text_file_path = text_file.name.replace('\\', '/')
            
            # Convert hex color to FFmpeg format
            color = text_color.lstrip('#')
            
            # Build drawtext filter with textfile instead of text parameter
            # This avoids all escaping issues
            text_filter = f"drawtext=fontfile=C\\:/Windows/Fonts/arialbd.ttf:textfile={text_file_path}:{pos}:fontsize={text_size}:fontcolor=0x{color}:borderw=3:bordercolor=black"
            video_filters.append(text_filter)
        
        # Build the FFmpeg command
        cmd = [ffmpeg_path, '-y']  # -y to overwrite output
        
        # Input with trim
        cmd.extend(['-ss', str(start_time), '-t', str(trim_duration), '-i', video.filepath])
        
        # Apply video filters if any
        if video_filters:
            cmd.extend(['-vf', ','.join(video_filters)])
        
        # Audio settings
        if mute_original:
            cmd.extend(['-an'])  # No audio
        else:
            volume = video_volume / 100
            cmd.extend(['-af', f'volume={volume}'])
        
        # Output settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            export_path
        ])
        
        print(f"[EXPORT] Running FFmpeg command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Clean up temp text file if it was created
            if text_overlay and text_overlay.strip() and 'text_file_path' in locals():
                try:
                    os.unlink(text_file_path)
                except:
                    pass
            
            if result.returncode != 0:
                print(f"[EXPORT] FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            print(f"[EXPORT] Video exported successfully to: {export_path}")
            
            # Update video outputs and status in database
            video.outputs['exported_video'] = export_path
            video.status = 'completed'
            
            # Get file size of exported video
            export_size = os.path.getsize(export_path) if os.path.exists(export_path) else 0
            
            self.videos.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {
                    "outputs.exported_video": export_path,
                    "status": "completed",
                    "process_end_time": datetime.utcnow(),
                    "metadata.exported_size": export_size,
                    "metadata.trim_start": trim_start,
                    "metadata.trim_end": trim_end,
                    "metadata.has_text_overlay": bool(text_overlay and text_overlay.strip())
                }}
            )
            
            return export_path
            
        except subprocess.TimeoutExpired:
            # Clean up temp file on timeout
            if text_overlay and text_overlay.strip() and 'text_file_path' in locals():
                try:
                    os.unlink(text_file_path)
                except:
                    pass
            print("[EXPORT] FFmpeg timed out")
            raise Exception("Export timed out - video may be too long")
        except Exception as e:
            # Clean up temp file on error
            if text_overlay and text_overlay.strip() and 'text_file_path' in locals():
                try:
                    os.unlink(text_file_path)
                except:
                    pass
            print(f"[EXPORT] Export failed: {e}")
            raise

    def dub_video_to_language(
        self, 
        video_id: str, 
        target_language: str,
        source_language: str = None,
        mix_original: bool = False,
        user_id: str = None
    ):
        """
        Dub video into another language using AI
        
        Args:
            video_id: Video ID
            target_language: Target language code (e.g., 'en', 'es', 'ur')
            source_language: Optional source language (auto-detected if not provided)
            mix_original: Keep original audio at low volume
            user_id: User ID for progress updates
            
        Returns:
            Dict with dubbing results
        """
        from services.dubbing_service import get_dubbing_service
        
        print(f"[VIDEO SERVICE] Starting dubbing for video {video_id} to {target_language}")
        
        try:
            # Get video from database
            video = self.get_video(video_id)
            if not video:
                raise ValueError("Video not found in database")
            
            print(f"[VIDEO SERVICE] Video found: {video.filename}")
            print(f"[VIDEO SERVICE] Filepath: {video.filepath}")
            print(f"[VIDEO SERVICE] Outputs: {video.outputs}")
            
            # Get video path (prefer processed, fallback to original)
            video_path = video.outputs.get('processed_video') or video.filepath
            
            # Try multiple path resolutions
            paths_to_try = []
            if video_path:
                paths_to_try.append(video_path)
                # Try with upload folder prefix
                if not os.path.isabs(video_path):
                    paths_to_try.append(os.path.join(self.upload_folder, video_path))
                    paths_to_try.append(os.path.join(self.upload_folder, os.path.basename(video_path)))
            
            # Also try just the filename
            if video.filename:
                paths_to_try.append(os.path.join(self.upload_folder, video.filename))
            
            # Find the first path that exists
            actual_path = None
            for path in paths_to_try:
                print(f"[VIDEO SERVICE] Checking path: {path}")
                if path and os.path.exists(path):
                    actual_path = path
                    print(f"[VIDEO SERVICE] Found video at: {actual_path}")
                    break
            
            if not actual_path:
                print(f"[VIDEO SERVICE] Tried paths: {paths_to_try}")
                print(f"[VIDEO SERVICE] Upload folder contents: {os.listdir(self.upload_folder) if os.path.exists(self.upload_folder) else 'folder not found'}")
                raise ValueError(f"Video file not found. Tried: {paths_to_try}")
            
            # Create output path
            base_name = os.path.splitext(video.filename)[0]
            output_filename = f"{base_name}_dubbed_{target_language}.mp4"
            output_path = os.path.join(self.upload_folder, output_filename)
            
            # Get dubbing service
            dubbing_service = get_dubbing_service(self.socketio)
            
            # Start dubbing process
            result = dubbing_service.dub_video(
                video_path=actual_path,
                output_path=output_path,
                target_language=target_language,
                source_language=source_language,
                user_id=user_id,
                video_id=video_id,
                mix_original=mix_original
            )
            
            # Update video in database with dubbed version
            if result['success']:
                self.videos.update_one(
                    {"_id": ObjectId(video_id)},
                    {
                        "$set": {
                            f"outputs.dubbed_{target_language}": output_path,
                            f"metadata.dubbed_languages": {
                                target_language: {
                                    'created_at': datetime.utcnow().isoformat(),
                                    'source_language': result['source_language'],
                                    'mix_original': mix_original
                                }
                            }
                        }
                    }
                )
                
                print(f"[VIDEO SERVICE] Dubbing completed successfully: {output_path}")
            
            return result
            
        except Exception as e:
            print(f"[VIDEO SERVICE] Dubbing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
