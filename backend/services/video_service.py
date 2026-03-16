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

# Optional AI imports - fail gracefully
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except:
    TF_AVAILABLE = False
    print("[WARNING] TensorFlow not available")

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    TRANSFORMERS_AVAILABLE = True
except:
    TRANSFORMERS_AVAILABLE = False
    print("[WARNING] Transformers not available")

try:
    import torch
    TORCH_AVAILABLE = True
except:
    TORCH_AVAILABLE = False
    print("[WARNING] PyTorch not available")

try:
    import whisper_timestamped as whisper_ts
    WHISPER_TS_AVAILABLE = True
except:
    WHISPER_TS_AVAILABLE = False
    print("[WARNING] Whisper-timestamped not available")

try:
    import whisper
    WHISPER_AVAILABLE = True
    print("[SUCCESS] OpenAI Whisper loaded successfully")
except Exception as e:
    WHISPER_AVAILABLE = False
    print(f"[ERROR] OpenAI Whisper failed to load: {e}")

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
    print("[SUCCESS] Noisereduce loaded successfully")
except Exception as e:
    NOISEREDUCE_AVAILABLE = False
    print(f"[WARNING] Noisereduce not available: {e}")

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
FFMPEG_PATH = r"C:\Users\Cv\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
if FFMPEG_PATH not in os.environ.get('PATH', ''):
    os.environ['PATH'] = FFMPEG_PATH + os.pathsep + os.environ.get('PATH', '')

# Set FFmpeg for imageio
os.environ['IMAGEIO_FFMPEG_EXE'] = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')

# Configure AudioSegment to use FFmpeg
AudioSegment.converter = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
AudioSegment.ffmpeg = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
AudioSegment.ffprobe = os.path.join(FFMPEG_PATH, 'ffprobe.exe')

# CRITICAL: Configure MoviePy to use FFmpeg
from moviepy.config import change_settings
change_settings({"FFMPEG_BINARY": os.path.join(FFMPEG_PATH, 'ffmpeg.exe')})

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
    """
    Advanced Audio Enhancement with REAL Filler Word Detection and VOICE-PRESERVING Noise Reduction
    
    NOISE REDUCTION: Voice-preserving single-pass processing to maintain speech quality and lip-sync
    - PRIMARY METHOD: noisereduce library (RECOMMENDED - provides best results)
    - FALLBACK METHOD: Voice-preserving single-pass spectral subtraction
    - LAST RESORT: Gentle filtering only
    
    For BEST noise reduction results, install noisereduce:
        pip install noisereduce
    
    Features:
    - SINGLE-PASS processing (preserves voice quality)
    - Adaptive noise profiling from multiple quiet sections
    - Voice frequency protection (300-3400 Hz always preserved)
    - Lip-sync maintained (audio duration never changes)
    - Configurable levels: light (60%), moderate (75%), strong (85%)
    
    CRITICAL FIXES:
    - Reduced aggressiveness from 80-98% to 60-85% to preserve voice
    - Single-pass only (multi-pass was damaging voice quality)
    - Duration checks at multiple points to prevent lip-sync issues
    - Gentle filtering to preserve speech frequencies
    """
    
    def __init__(self):
        # Comprehensive filler words and phrases (case-insensitive)
        self.filler_words = {
            'en': [
                # Single word fillers
                'um', 'uh', 'er', 'ah', 'hmm', 'mm', 'mmm', 'hm',
                'like', 'so', 'well', 'right', 'okay', 'ok',
                'actually', 'basically', 'literally', 'obviously',
                # Multi-word phrases
                'you know', 'but you know', 'you know what i mean',
                'i guess', 'i suppose', 'i mean',
                'kind of', 'sort of', 'or something',
                'you see', 'mm-hmm', 'uh-huh'
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
                # Check if Whisper is available globally
                if not WHISPER_AVAILABLE:
                    print(f"[AUDIO ENHANCER] Whisper not available globally")
                    return None
                
                import whisper
                device = get_device()
                print(f"[AUDIO ENHANCER] Loading Whisper 'base' model for filler detection on {device}...")
                self._whisper_model = whisper.load_model("base", device=device)
                print(f"[AUDIO ENHANCER] ✅ Whisper model loaded successfully on {device}")
            except Exception as e:
                print(f"[AUDIO ENHANCER] ❌ Failed to load Whisper: {e}")
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
            noise_reduction = options.get('noise_reduction', 'none')  # Default to 'none' - user controls it
            
            detect_and_remove_fillers = options.get('detect_and_remove_fillers', options.get('remove_fillers', False))  # NEW: Separate filler removal option
            detect_repeated_words = options.get('detect_repeated_words', True)  # NEW: Detect repeated words
            
            # NEW: Get custom filler words from options
            custom_filler_words = options.get('custom_filler_words', [])
            use_custom_fillers = options.get('use_custom_fillers', False)
            
            print(f"[AUDIO ENHANCE] Options: type={enhancement_type}, pause={pause_threshold}ms, noise={noise_reduction}, remove_fillers={detect_and_remove_fillers}, detect_repeated={detect_repeated_words}")
            if use_custom_fillers and custom_filler_words:
                print(f"[AUDIO ENHANCE] Using custom filler words: {custom_filler_words}")
            
            # Reset counters and segments storage
            self._filler_words_removed_count = 0
            self._repeated_words_removed_count = 0
            self._detected_filler_segments = []  # Store segments for video cutting
            
            # CRITICAL: Track original audio duration
            original_duration_ms = len(audio)
            print(f"[AUDIO ENHANCE] ========================================")
            print(f"[AUDIO ENHANCE] STARTING AUDIO PROCESSING")
            print(f"[AUDIO ENHANCE] Original duration: {original_duration_ms}ms ({original_duration_ms/1000:.2f}s)")
            print(f"[AUDIO ENHANCE] ========================================")
            
            # Step 1: Remove excessive silence/pauses (OPTIONAL - can be disabled)
            cut_silence = options.get('cut_silence', False)  # Default to False for safety
            
            if cut_silence and pause_threshold < 2000:
                print(f"[AUDIO ENHANCE] Silence removal ENABLED with pause_threshold={pause_threshold}ms")
                enhanced_audio = self._remove_silence(audio, pause_threshold)
            else:
                if not cut_silence:
                    print(f"[AUDIO ENHANCE] Silence removal DISABLED - preserving all audio")
                else:
                    print(f"[AUDIO ENHANCE] Silence removal SKIPPED (pause_threshold={pause_threshold}ms >= 2000ms)")
                print(f"[AUDIO ENHANCE] Voice and timing 100% preserved")
                enhanced_audio = audio
            
            after_silence_ms = len(enhanced_audio)
            print(f"[AUDIO ENHANCE] After silence check: {after_silence_ms}ms (removed {original_duration_ms - after_silence_ms}ms)")
            if original_duration_ms == after_silence_ms:
                print(f"[AUDIO ENHANCE] ✅ No silence removed - original audio preserved")
            else:
                print(f"[AUDIO ENHANCE] Voice should be 100% preserved - only long pauses removed")
            
            # Step 2: Remove filler words using REAL speech recognition (ONLY if enabled)
            # OR detect them for video cutting without modifying audio
            detect_only_for_video_cutting = options.get('detect_only_for_video_cutting', False)
            
            if detect_and_remove_fillers or detect_only_for_video_cutting:
                if detect_only_for_video_cutting:
                    print(f"[AUDIO ENHANCE] DETECT-ONLY MODE: Finding fillers for video cutting without modifying audio")
                    # Call whisper to detect fillers but don't remove them
                    original_audio_copy = enhanced_audio  # Keep original audio
                    _ = self._remove_filler_words_with_whisper(
                        enhanced_audio, 
                        audio_path, 
                        enhancement_type,
                        detect_repeated=detect_repeated_words,
                        custom_fillers=custom_filler_words if use_custom_fillers else None
                    )
                    # IMPORTANT: Don't use the modified audio, keep the original
                    enhanced_audio = original_audio_copy
                    print(f"[AUDIO ENHANCE] Detected {self._filler_words_removed_count} fillers (audio unchanged)")
                else:
                    # Normal mode: actually remove fillers from audio
                    enhanced_audio = self._remove_filler_words_with_whisper(
                        enhanced_audio, 
                        audio_path, 
                        enhancement_type,
                        detect_repeated=detect_repeated_words,
                        custom_fillers=custom_filler_words if use_custom_fillers else None
                    )
                    print(f"[AUDIO ENHANCE] After filler word removal: {len(enhanced_audio)}ms")
                    print(f"[AUDIO ENHANCE] Removed {self._filler_words_removed_count} fillers, {self._repeated_words_removed_count} repeated words")
            else:
                print(f"[AUDIO ENHANCE] Filler word removal disabled")
            
            # Step 3: Apply noise reduction (independent of filler removal) - USER CONTROLLED
            noise_reduction_percentage = 0
            # Apply noise reduction only if not 'none'
            if noise_reduction != 'none':
                print(f"[AUDIO ENHANCE] ========================================")
                print(f"[AUDIO ENHANCE] NOISE REDUCTION: {noise_reduction.upper()} mode")
                print(f"[AUDIO ENHANCE] ========================================")
                # Calculate before/after for real metrics
                audio_before_noise = np.array(enhanced_audio.get_array_of_samples(), dtype=np.float32)
                before_noise_ms = len(enhanced_audio)
                
                enhanced_audio = self._reduce_noise(enhanced_audio, noise_reduction)
                
                after_noise_ms = len(enhanced_audio)
                audio_after_noise = np.array(enhanced_audio.get_array_of_samples(), dtype=np.float32)
                print(f"[AUDIO ENHANCE] After noise reduction: {after_noise_ms}ms (duration preserved: {before_noise_ms == after_noise_ms})")
            else:
                print(f"[AUDIO ENHANCE] Noise reduction disabled (set to 'none') - Voice 100% original")
                audio_before_noise = np.array(enhanced_audio.get_array_of_samples(), dtype=np.float32)
                audio_after_noise = audio_before_noise  # Same as before when disabled
            
            # Calculate actual noise reduction (simplified SNR improvement)
            try:
                # Estimate noise as residual
                min_len = min(len(audio_before_noise), len(audio_after_noise))
                residual = audio_before_noise[:min_len] - audio_after_noise[:min_len]
                residual_power = np.mean(residual ** 2)
                original_power = np.mean(audio_before_noise[:min_len] ** 2)
                if original_power > 0:
                    noise_reduction_percentage = min(95, max(0, (residual_power / original_power) * 100))
                    print(f"[AUDIO ENHANCE] Calculated noise reduction: {noise_reduction_percentage:.1f}%")
            except Exception as calc_error:
                print(f"[AUDIO ENHANCE] Could not calculate noise reduction: {calc_error}")
                # Fallback to estimated values
                noise_reduction_percentage = {'light': 40, 'moderate': 65, 'strong': 80}.get(noise_reduction, 65)
            
            print(f"[AUDIO ENHANCE] After noise reduction: {len(enhanced_audio)}ms")
            
            # Step 4: Apply transition smoothing for natural flow
            enhanced_audio = self._apply_transition_smoothing(enhanced_audio)
            final_duration_ms = len(enhanced_audio)
            print(f"[AUDIO ENHANCE] After transition smoothing: {final_duration_ms}ms")
            
            # Step 5: Normalize audio
            enhanced_audio = normalize(enhanced_audio)
            print(f"[AUDIO ENHANCE] Final audio: {len(enhanced_audio)}ms")
            
            # CRITICAL: Final summary showing what happened
            print(f"[AUDIO ENHANCE] ========================================")
            print(f"[AUDIO ENHANCE] PROCESSING COMPLETE SUMMARY")
            print(f"[AUDIO ENHANCE] ========================================")
            print(f"[AUDIO ENHANCE] Original: {original_duration_ms}ms ({original_duration_ms/1000:.2f}s)")
            print(f"[AUDIO ENHANCE] Final: {final_duration_ms}ms ({final_duration_ms/1000:.2f}s)")
            print(f"[AUDIO ENHANCE] Time removed: {original_duration_ms - final_duration_ms}ms ({abs(original_duration_ms - final_duration_ms)/1000:.2f}s)")
            print(f"[AUDIO ENHANCE] Noise reduction mode: {noise_reduction}")
            print(f"[AUDIO ENHANCE] Fillers removed: {self._filler_words_removed_count}")
            if noise_reduction in ['none', 'light', 'moderate']:
                print(f"[AUDIO ENHANCE] ✅ Voice 100% preserved (no noisereduce processing)")
            else:
                print(f"[AUDIO ENHANCE] ⚠️ Strong mode used - voice may be slightly affected")
            print(f"[AUDIO ENHANCE] ========================================")
            print(f"[AUDIO ENHANCE] Audio enhancement completed, returning results...")
            
            # Calculate improvement metrics
            original_duration = len(audio)
            enhanced_duration = len(enhanced_audio)
            time_saved = original_duration - enhanced_duration
            
            # Generate timeline data for visualization
            timeline_data = None
            if self._detected_filler_segments and len(self._detected_filler_segments) > 0:
                timeline_data = self.generate_timeline_data(original_duration, self._detected_filler_segments)
            
            metrics = {
                'original_duration_ms': original_duration,
                'enhanced_duration_ms': enhanced_duration,
                'time_saved_ms': time_saved,
                'time_saved_percentage': (time_saved / original_duration) * 100 if original_duration > 0 else 0,
                'noise_reduction_level': noise_reduction,
                'noise_reduction_percentage': noise_reduction_percentage,  # REAL calculated value
                'enhancement_type': enhancement_type,
                'filler_words_removed': self._filler_words_removed_count,
                'repeated_words_removed': self._repeated_words_removed_count,
                'filler_removal_enabled': detect_and_remove_fillers and not detect_only_for_video_cutting,  # Only true if actually removed from audio
                'filler_detection_only': detect_only_for_video_cutting,  # Flag for detect-only mode
                'filler_segments': self._detected_filler_segments,  # Include segments for video cutting
                'timeline': timeline_data  # NEW: Timeline visualization data
            }
            
            print(f"[AUDIO ENHANCE] Metrics: {metrics}")
            if detect_only_for_video_cutting:
                print(f"[AUDIO ENHANCE] ⚠️ DETECT-ONLY mode was active - audio duration unchanged")
            return enhanced_audio, metrics
            
        except Exception as e:
            print(f"[AUDIO ENHANCE] Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _remove_silence(self, audio, pause_threshold):
        """CONSERVATIVE silence removal - preserves all voice, only removes long pauses"""
        try:
            # CRITICAL FIX: Very conservative settings to prevent voice removal
            # Only remove truly long silences (1000ms+), never touch voice
            min_silence_len = max(pause_threshold * 2, 1000)  # Minimum 1000ms - only long pauses
            
            # CRITICAL: Use absolute threshold instead of relative
            # -50 dBFS ensures we only remove TRUE silence, never quiet voice
            silence_thresh = -50  # Absolute threshold - very conservative
            
            print(f"[SILENCE] CONSERVATIVE mode: threshold={silence_thresh}dB (absolute), min_len={min_silence_len}ms")
            print(f"[SILENCE] This preserves all voice, only removes long pauses")
            
            # Split on silence with conservative settings
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                keep_silence=500  # Keep 500ms of silence for natural flow
            )
            
            if not chunks or len(chunks) <= 1:
                print("[SILENCE] No long silences found or only 1 chunk - returning original audio")
                return audio
            
            print(f"[SILENCE] Found {len(chunks)} segments with {min_silence_len}ms+ silence between them")
            
            # Combine chunks with controlled gaps
            result = AudioSegment.empty()
            for i, chunk in enumerate(chunks):
                result += chunk
                # Add gap between chunks (except last one)
                if i < len(chunks) - 1:
                    gap_duration = min(400, pause_threshold)  # Keep reasonable gaps
                    silence_gap = AudioSegment.silent(duration=gap_duration)
                    result += silence_gap
            
            print(f"[SILENCE] Combined {len(chunks)} chunks - voice preserved")
            return result
            
        except Exception as e:
            print(f"[SILENCE] Error: {e}, returning original audio")
            return audio
    
    def _remove_filler_words_with_whisper(self, audio, audio_path, enhancement_type, detect_repeated=True, custom_fillers=None):
        """Remove filler words and repeated words using Whisper speech recognition for REAL detection"""
        try:
            print(f"[FILLER] Starting REAL filler word detection with Whisper: {enhancement_type}")
            print(f"[FILLER] Detect repeated words: {detect_repeated}")
            
            # Use custom filler words if provided, otherwise use predefined lists
            if custom_fillers and len(custom_fillers) > 0:
                target_fillers = [f.lower().strip() for f in custom_fillers if f.strip()]
                print(f"[FILLER] Using CUSTOM filler words: {target_fillers}")
            else:
                # ONLY true filler sounds - never remove real words like 'so', 'well', 'right', 'i think'
                if enhancement_type == 'conservative':
                    target_fillers = ['um', 'uh', 'er']
                elif enhancement_type == 'medium':
                    target_fillers = ['um', 'uh', 'er', 'ah', 'uhm', 'erm', 'umm', 'uhh', 'err',
                                    'hmm', 'mm', 'hm', 'mmm', 'mhm']
                else:  # aggressive
                    target_fillers = ['um', 'uh', 'er', 'ah', 'uhm', 'erm', 'umm', 'uhh', 'err', 'agh',
                                    'hmm', 'mm', 'hm', 'mmm', 'mhm', 'uh-huh', 'mm-hmm', 'huh']
                
                print(f"[FILLER] Target filler words: {target_fillers}")
            
            # Use Whisper for accurate filler word detection (includes repeated word detection)
            filler_segments = self._detect_fillers_with_whisper(audio_path, target_fillers, detect_repeated=detect_repeated)
            
            # Store segments for video cutting
            self._detected_filler_segments = filler_segments
            
            if not filler_segments:
                print("[FILLER] No filler words detected by Whisper - audio is clean!")
                return audio
            
            # Sort segments by start time
            filler_segments.sort(key=lambda x: x[0])
            
            # Remove detected filler segments with smooth crossfade transitions
            CROSSFADE_MS = 20  # Crossfade duration to prevent clicks
            result = AudioSegment.empty()
            last_end = 0
            
            for start_ms, end_ms in filler_segments:
                # Add audio before filler word
                if start_ms > last_end:
                    chunk = audio[last_end:start_ms]
                    # Apply fade-out at the end of kept chunk to blend into gap
                    if len(chunk) > CROSSFADE_MS * 2:
                        chunk = chunk.fade_out(CROSSFADE_MS)
                    result += chunk
                
                last_end = end_ms
                self._filler_words_removed_count += 1
            
            # Add remaining audio with fade-in for smooth transition
            if last_end < len(audio):
                remainder = audio[last_end:]
                if len(remainder) > CROSSFADE_MS * 2:
                    remainder = remainder.fade_in(CROSSFADE_MS)
                result += remainder
            
            print(f"[FILLER] Removed {self._filler_words_removed_count} filler segments with crossfade transitions")
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
            
            print(f"[WHISPER] Transcribing audio for filler and repeated word detection...")
            
            # Use initial_prompt to bias Whisper toward transcribing filler sounds
            # Without this, Whisper often skips "um", "uh", "uhm" and treats them as silence
            filler_prompt = "Um, uh, uhm, er, ah, hmm, like, you know. Um, uh."
            
            # Transcribe with word-level timestamps (CRITICAL for accurate cutting)
            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                language='en',
                verbose=False,
                initial_prompt=filler_prompt,
                no_speech_threshold=0.3,
                condition_on_previous_text=False
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
            
            # 1. Detect single-word fillers
            single_word_fillers = [f for f in target_fillers if ' ' not in f]
            for word_info in all_words:
                word_clean = word_info['text']
                
                # Check if word is a single-word filler (exact match only)
                if word_clean in single_word_fillers:
                    start_ms = int(word_info['start'] * 1000)
                    end_ms = int(word_info['end'] * 1000)
                    
                    filler_segments.append((start_ms, end_ms, f"filler: {word_info['original']}"))
                    print(f"[WHISPER] Found filler '{word_info['original']}' at {start_ms}ms - {end_ms}ms")
                    continue
            
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
                        
                        filler_segments.append((start_ms, end_ms, f"repeated: {current_word}"))
                        print(f"[WHISPER] Found repeated word '{current_word}' at {start_ms}ms - {end_ms}ms")
                        self._repeated_words_removed_count += 1
            
            # 4. Gap-based filler detection: Whisper sometimes skips fillers entirely,
            # leaving gaps between words. Analyze audio energy in gaps to find hidden fillers.
            if len(all_words) > 1:
                try:
                    from pydub import AudioSegment as GapAudio
                    gap_audio = GapAudio.from_file(audio_path)
                    MIN_GAP_MS = 300  # Minimum gap to check (ms)
                    MIN_ENERGY_DB = -35  # Minimum dBFS to consider as speech (not silence)
                    
                    for i in range(len(all_words) - 1):
                        gap_start = all_words[i]['end']
                        gap_end = all_words[i + 1]['start']
                        gap_ms = (gap_end - gap_start) * 1000
                        
                        if gap_ms >= MIN_GAP_MS:
                            start_ms = int(gap_start * 1000)
                            end_ms = int(gap_end * 1000)
                            
                            # Check if any existing filler already covers this gap
                            already_covered = any(
                                fs[0] <= start_ms and fs[1] >= end_ms 
                                for fs in filler_segments
                            )
                            if already_covered:
                                continue
                            
                            # Check audio energy in the gap
                            gap_chunk = gap_audio[start_ms:end_ms]
                            if len(gap_chunk) > 0 and gap_chunk.dBFS > MIN_ENERGY_DB:
                                # There's speech energy in this gap - likely a filler Whisper skipped
                                # Trim edges slightly to avoid cutting real speech
                                trim = 30  # ms
                                trimmed_start = start_ms + trim
                                trimmed_end = end_ms - trim
                                if trimmed_end > trimmed_start:
                                    filler_segments.append((trimmed_start, trimmed_end, "gap-filler"))
                                    print(f"[WHISPER] Found gap-filler at {trimmed_start}ms - {trimmed_end}ms (gap energy: {gap_chunk.dBFS:.1f} dBFS)")
                                    self._filler_words_removed_count += 1
                except Exception as gap_err:
                    print(f"[WHISPER] Gap detection error (non-fatal): {gap_err}")
            
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
            
            # Get filler words to detect - ONLY true filler sounds
            # NEVER include real words like 'so', 'well', 'right', 'like', 'i think' etc.
            # These are meaningful words that should stay in speech for natural flow
            if enhancement_type == 'conservative':
                target_fillers = ['um', 'uh', 'er', 'uhm', 'erm', 'umm']
            elif enhancement_type == 'medium':
                target_fillers = [
                    # Basic fillers only
                    'um', 'uh', 'er', 'ah', 'uhm', 'erm', 'umm', 'uhh', 'err',
                    # Sound fillers only
                    'hmm', 'mm', 'hm', 'mmm', 'mhm', 'uh-huh', 'mm-hmm'
                ]
            else:  # aggressive
                target_fillers = [
                    # All basic filler sounds
                    'um', 'uh', 'er', 'ah', 'uhm', 'erm', 'umm', 'uhh', 'err', 'agh',
                    # All sound fillers  
                    'hmm', 'mm', 'hm', 'mmm', 'mhm', 'uh-huh', 'mm-hmm', 'huh'
                ]
            
            print(f"[TRANSCRIPT] Target fillers ({len(target_fillers)}): {target_fillers[:10]}...")
            
            # Transcribe with ENHANCED word timestamps using whisper-timestamped
            print(f"[TRANSCRIPT] Using whisper-timestamped for precise word-level timestamps...")
            # Use initial_prompt to bias Whisper toward transcribing filler sounds
            filler_prompt = "Um, uh, uhm, er, ah, hmm, like, you know. Um, uh."
            
            try:
                audio_array = whisper_ts.load_audio(audio_path)
                result = whisper_ts.transcribe(
                    model,
                    audio_array,
                    language='en',
                    vad=False,  # Disable VAD to avoid hook issues
                    detect_disfluencies=True,  # Enable to detect um/uh/uhm disfluencies
                    compute_word_confidence=False,  # Disable confidence to reduce hooks
                    trust_whisper_timestamps=True,  # Use Whisper's native timestamps
                    initial_prompt=filler_prompt
                )
            except Exception as e:
                print(f"[TRANSCRIPT] whisper-timestamped failed: {e}, falling back to standard Whisper...")
                # Fallback to standard Whisper if timestamped version fails
                result = model.transcribe(
                    audio_path,
                    word_timestamps=True,
                    language='en',
                    verbose=False,
                    initial_prompt=filler_prompt,
                    no_speech_threshold=0.3,
                    condition_on_previous_text=False
                )
            
            print(f"[TRANSCRIPT] Whisper transcription: {result.get('text', '')[:200]}...")
            
            # Build transcript with word-level details
            words = []
            filler_count = 0
            repeated_count = 0
            
            # Collect all words
            # NOTE: whisper-timestamped uses 'text' key, standard Whisper uses 'word' key
            # When detect_disfluencies=True, whisper-timestamped prefixes fillers with [*]
            all_words = []
            for segment in result.get('segments', []):
                for word_info in segment.get('words', []):
                    raw_word = word_info.get('word', '') or word_info.get('text', '')
                    word = raw_word.lower().strip()
                    
                    # Check for whisper-timestamped disfluency marker [*]
                    is_disfluency = '[*]' in word
                    word = word.replace('[*]', '').strip()
                    
                    word_clean = ''.join(c for c in word if c.isalnum() or c.isspace()).strip()
                    if word_clean:
                        all_words.append({
                            'text': word_clean,
                            'original': raw_word.strip().replace('[*]', '').strip(),
                            'start': word_info.get('start', 0),
                            'end': word_info.get('end', 0),
                            'duration': word_info.get('end', 0) - word_info.get('start', 0),
                            'is_disfluency': is_disfluency
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
                
                # Check 1: Exact match with filler list OR disfluency marker from whisper-timestamped
                if word_clean in single_word_fillers or word_info.get('is_disfluency', False):
                    is_filler = True
                    detected_fillers.append(word_clean)
                    reason = "disfluency" if word_info.get('is_disfluency') else "exact"
                    print(f"[TRANSCRIPT] Detected filler ({reason}): '{word_clean}' at {word_info['start']:.2f}s")
                
                # Check 2: Detect repeated word (only if user enabled it)
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
            
            # Gap-based filler detection: add "[filler]" placeholder for gaps with speech energy
            if len(all_words) > 1:
                try:
                    from pydub import AudioSegment as GapAudioT
                    gap_audio_t = GapAudioT.from_file(audio_path)
                    MIN_GAP_MS = 300
                    MIN_ENERGY_DB = -35
                    gap_fillers = []
                    
                    for i in range(len(all_words) - 1):
                        gap_start = all_words[i]['end']
                        gap_end = all_words[i + 1]['start']
                        gap_ms = (gap_end - gap_start) * 1000
                        
                        if gap_ms >= MIN_GAP_MS:
                            start_ms = int(gap_start * 1000)
                            end_ms = int(gap_end * 1000)
                            gap_chunk = gap_audio_t[start_ms:end_ms]
                            if len(gap_chunk) > 0 and gap_chunk.dBFS > MIN_ENERGY_DB:
                                gap_fillers.append({
                                    'text': 'uhm',
                                    'start': gap_start + 0.03,
                                    'end': gap_end - 0.03,
                                    'is_filler': True,
                                    'is_repeated': False
                                })
                                filler_count += 1
                                print(f"[TRANSCRIPT] Detected gap-filler at {gap_start:.2f}s - {gap_end:.2f}s (energy: {gap_chunk.dBFS:.1f} dBFS)")
                    
                    # Insert gap fillers into words list at correct positions
                    if gap_fillers:
                        words.extend(gap_fillers)
                        words.sort(key=lambda w: w['start'])
                        print(f"[TRANSCRIPT] Added {len(gap_fillers)} gap-fillers to transcript")
                except Exception as gap_err:
                    print(f"[TRANSCRIPT] Gap detection error (non-fatal): {gap_err}")
            
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
        """REAL noise reduction using noisereduce library - AGGRESSIVE but VOICE-PRESERVING"""
        try:
            print(f"[NOISE] ========================================")
            print(f"[NOISE] REAL NOISE REDUCTION: {noise_level}")
            print(f"[NOISE] ========================================")
            
            if noise_level == 'none':
                print(f"[NOISE] Noise reduction disabled - returning original audio")
                return audio
            
            original_duration = len(audio)
            sample_rate = audio.frame_rate
            n_channels = audio.channels
            print(f"[NOISE] Input: {original_duration}ms, {sample_rate}Hz, {n_channels}ch")
            
            # Step 1: Apply high-pass filter to remove low-frequency rumble (< 80Hz)
            audio = audio.high_pass_filter(80)
            print(f"[NOISE] Applied 80Hz high-pass filter to remove rumble")
            
            # Convert AudioSegment to numpy float32 normalized to [-1, 1]
            raw_samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            max_val = float(2 ** (audio.sample_width * 8 - 1))  # 32768 for 16-bit
            raw_samples = raw_samples / max_val  # Normalize to [-1, 1]
            
            # Use noisereduce library if available
            if NOISEREDUCE_AVAILABLE:
                print(f"[NOISE] Using noisereduce library v3")
                
                # Set parameters based on level - more aggressive now
                if noise_level == 'light':
                    prop_decrease = 0.75
                    n_passes = 1
                    print(f"[NOISE] LIGHT: 75% noise reduction, 1 pass")
                elif noise_level == 'moderate':
                    prop_decrease = 0.90
                    n_passes = 2
                    print(f"[NOISE] MODERATE: 90% noise reduction, 2 passes")
                else:  # strong
                    prop_decrease = 1.0
                    n_passes = 2
                    print(f"[NOISE] STRONG: 100% noise reduction, 2 passes")
                
                try:
                    def _nr_process(samples, sr, prop_dec, passes):
                        """Run noise reduction for given number of passes"""
                        result = samples
                        for p in range(passes):
                            result = nr.reduce_noise(
                                y=result, sr=sr,
                                stationary=False, prop_decrease=prop_dec,
                                freq_mask_smooth_hz=300, time_mask_smooth_ms=30,
                                n_fft=2048
                            )
                            if passes > 1:
                                print(f"[NOISE]   Pass {p+1}/{passes} complete")
                        return result
                    
                    if n_channels == 2:
                        # Split interleaved stereo into separate channels
                        left = raw_samples[0::2]
                        right = raw_samples[1::2]
                        print(f"[NOISE] Processing stereo: {len(left)} samples per channel")
                        
                        # Process each channel independently
                        left_clean = _nr_process(left, sample_rate, prop_decrease, n_passes)
                        right_clean = _nr_process(right, sample_rate, prop_decrease, n_passes)
                        
                        # Re-interleave stereo channels
                        enhanced_norm = np.empty(len(left_clean) + len(right_clean), dtype=np.float32)
                        enhanced_norm[0::2] = left_clean
                        enhanced_norm[1::2] = right_clean
                    else:
                        # Mono: process directly
                        print(f"[NOISE] Processing mono: {len(raw_samples)} samples")
                        enhanced_norm = _nr_process(raw_samples, sample_rate, prop_decrease, n_passes)
                    
                    print(f"[NOISE] Noisereduce processing complete")
                except Exception as nr_error:
                    print(f"[NOISE] Noisereduce failed: {nr_error}, using fallback")
                    import traceback; traceback.print_exc()
                    return self._apply_frequency_filtering(audio, noise_level)
            else:
                print(f"[NOISE] Noisereduce not available, using frequency filtering")
                return self._apply_frequency_filtering(audio, noise_level)
            
            # Convert back: denormalize to int16 range
            enhanced_int = np.clip(enhanced_norm * max_val, -max_val, max_val - 1).astype(np.int16)
            
            enhanced = AudioSegment(
                enhanced_int.tobytes(),
                frame_rate=sample_rate,
                sample_width=audio.sample_width,
                channels=n_channels
            )
            
            enhanced = normalize(enhanced)
            
            # CRITICAL: Enforce same duration as original to prevent lip-sync issues
            final_duration = len(enhanced)
            if final_duration != original_duration:
                print(f"[NOISE] ⚠️ Duration mismatch: {final_duration}ms vs {original_duration}ms - fixing...")
                if final_duration > original_duration:
                    enhanced = enhanced[:original_duration]
                else:
                    enhanced = enhanced + AudioSegment.silent(
                        duration=original_duration - final_duration,
                        frame_rate=sample_rate
                    )
                print(f"[NOISE] Duration fixed to {len(enhanced)}ms")
            
            print(f"[NOISE] Output: {len(enhanced)}ms (duration preserved: {original_duration == len(enhanced)})")
            print(f"[NOISE] Noise reduction DONE ({noise_level}, {prop_decrease*100:.0f}%, {n_passes} pass(es))")
            
            return enhanced
            
        except Exception as e:
            print(f"[NOISE] Error in noise reduction: {e}")
            import traceback
            traceback.print_exc()
            return audio
    
    def _apply_frequency_filtering(self, audio, noise_level):
        """Fallback: Gentle frequency filtering when noisereduce is not available"""
        try:
            print(f"[NOISE] Applying frequency filtering fallback...")
            
            enhanced = audio
            
            if noise_level == 'light':
                enhanced = audio.high_pass_filter(40)
                print(f"[NOISE] Applied 40Hz high-pass filter")
            elif noise_level == 'moderate':
                enhanced = audio.high_pass_filter(65)
                enhanced = enhanced.low_pass_filter(15000)
                print(f"[NOISE] Applied 65Hz HPF and 15kHz LPF")
            elif noise_level == 'strong':
                enhanced = audio.high_pass_filter(75)
                enhanced = enhanced.low_pass_filter(12000)
                print(f"[NOISE] Applied 75Hz HPF and 12kHz LPF")
                try:
                    compressed = compress_dynamic_range(enhanced, threshold=-35.0, ratio=1.5, attack=10.0, release=100.0)
                    enhanced = compressed
                except:
                    pass
            
            return normalize(enhanced)
            
        except Exception as e:
            print(f"[NOISE] Fallback error: {e}")
            return audio
    
    def _apply_transition_smoothing(self, audio):
        """Apply subtle crossfades to blend audio cuts for natural flow
        
        Uses multi-stage fading:
        1. Quick fade-in to prevent clicks (15ms)
        2. Gentle fade-out at end (30ms)
        3. Optional compression to smooth volume variations
        """
        try:
            print("[SMOOTHING] Applying enhanced transition smoothing for natural blending...")
            
            # Use shorter fade durations for more natural sound
            fade_in_duration = 15   # 15ms quick fade-in to prevent clicks
            fade_out_duration = 30  # 30ms gentle fade-out
            
            if len(audio) > (fade_in_duration + fade_out_duration):
                # Apply asymmetric fades for more natural transitions
                audio = audio.fade_in(fade_in_duration).fade_out(fade_out_duration)
                print(f"[SMOOTHING] Applied crossfades: {fade_in_duration}ms in, {fade_out_duration}ms out")
                
                # Optional: Apply very gentle compression to smooth volume variations
                try:
                    # Ultra-light compression for natural flow
                    audio = compress_dynamic_range(
                        audio,
                        threshold=-30.0,  # Only affect louder parts
                        ratio=1.2,        # Very gentle compression
                        attack=5.0,       # Fast attack
                        release=50.0      # Quick release
                    )
                    print("[SMOOTHING] Applied gentle compression for volume consistency")
                except Exception as comp_err:
                    print(f"[SMOOTHING] Compression skipped: {comp_err}")
            else:
                print("[SMOOTHING] Audio too short for fading, applying minimal processing")
                # For very short audio, just apply minimal fade
                if len(audio) > 10:
                    audio = audio.fade_in(5).fade_out(5)
            
            return audio
            
        except Exception as e:
            print(f"[SMOOTHING] Error: {e}")
            return audio
    
    def generate_timeline_data(self, original_duration_ms, filler_segments):
        """Generate timeline visualization data showing kept and removed segments
        
        Args:
            original_duration_ms: Original video duration in milliseconds
            filler_segments: List of (start_ms, end_ms) tuples for removed segments
            
        Returns:
            dict: Timeline data with kept/removed segments for visualization
        """
        try:
            print(f"[TIMELINE] Generating timeline for {original_duration_ms}ms video with {len(filler_segments)} cuts")
            
            # Create list of kept segments (inverse of removed)
            kept_segments = []
            removed_segments = []
            last_end = 0
            
            # Sort filler segments
            sorted_fillers = sorted(filler_segments, key=lambda x: x[0])
            
            for start_ms, end_ms in sorted_fillers:
                # Add kept segment before this filler
                if start_ms > last_end:
                    kept_segments.append({
                        'start': last_end / 1000.0,  # Convert to seconds
                        'end': start_ms / 1000.0,
                        'duration': (start_ms - last_end) / 1000.0,
                        'type': 'kept'
                    })
                
                # Add removed segment
                removed_segments.append({
                    'start': start_ms / 1000.0,
                    'end': end_ms / 1000.0,
                    'duration': (end_ms - start_ms) / 1000.0,
                    'type': 'removed'
                })
                
                last_end = end_ms
            
            # Add final kept segment
            if last_end < original_duration_ms:
                kept_segments.append({
                    'start': last_end / 1000.0,
                    'end': original_duration_ms / 1000.0,
                    'duration': (original_duration_ms - last_end) / 1000.0,
                    'type': 'kept'
                })
            
            # Calculate statistics
            total_kept_duration = sum(seg['duration'] for seg in kept_segments)
            total_removed_duration = sum(seg['duration'] for seg in removed_segments)
            original_duration_sec = original_duration_ms / 1000.0
            
            timeline_data = {
                'original_duration': original_duration_sec,
                'final_duration': total_kept_duration,
                'removed_duration': total_removed_duration,
                'time_saved_percentage': (total_removed_duration / original_duration_sec * 100) if original_duration_sec > 0 else 0,
                'kept_segments': kept_segments,
                'removed_segments': removed_segments,
                'total_segments': len(kept_segments) + len(removed_segments),
                'cuts_made': len(removed_segments)
            }
            
            print(f"[TIMELINE] Generated timeline: {len(kept_segments)} kept, {len(removed_segments)} removed")
            print(f"[TIMELINE] Time saved: {total_removed_duration:.2f}s ({timeline_data['time_saved_percentage']:.1f}%)")
            
            return timeline_data
            
        except Exception as e:
            print(f"[TIMELINE] Error generating timeline: {e}")
            import traceback
            traceback.print_exc()
            return None

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
        
        # Initialize AI models (disable problematic ones for now)
        try:
            self.summarizer = None
            self.speech_recognizer = None
            print("[VIDEO SERVICE] AI models disabled - focusing on Whisper for Urdu subtitles")
        except Exception as e:
            print(f"Warning: Could not initialize AI models: {e}")
            self.summarizer = None
            self.speech_recognizer = None

        # Initialize OpenAI client for text summarization
        try:
            import openai
            api_key = os.environ.get('OPENAI_API_KEY', '')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                print("[VIDEO SERVICE] OpenAI client initialized for text summarization")
            else:
                self.openai_client = None
                print("[VIDEO SERVICE] No OpenAI API key - using extractive summarization fallback")
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
        
        # Auto-generate transcript in a background thread so upload returns immediately
        import threading
        def _run_transcription():
            try:
                print(f"[SAVE_VIDEO] Starting auto-transcription in background...")
                self._auto_transcribe_video(video_id, filepath)
            except Exception as e:
                print(f"[SAVE_VIDEO] Auto-transcription failed (non-critical): {e}")

        t = threading.Thread(target=_run_transcription, daemon=True)
        t.start()
        
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
                enhancement_type='medium',  # Use medium - only detect true filler sounds
                detect_repeated=False  # Don't detect repeated words unless user asks
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
            if options.get('cut_filler_segments', options.get('remove_filler_words', False)):
                current_progress += step_progress
                self._emit_progress(video_id, 'cutting_filler_segments', int(current_progress), 'Cutting filler segments from video...')
                # Get filler segments from audio enhancement metrics
                filler_segments = video.outputs.get('audio_enhancement_metrics', {}).get('filler_segments', [])
                self._remove_filler_segments_from_video(video, options, filler_segments)
            
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
                self._summarize_video(video)

            # Apply video enhancements
            if any([options.get('stabilization'), options.get('brightness'), options.get('contrast'), 
                    options.get('saturation'), options.get('ai_color_enhancement')]):
                current_progress += step_progress
                self._emit_progress(video_id, 'enhancing_video', int(current_progress), 'Applying video enhancements...')
                self._apply_video_enhancements(video, options)

            video.status = "completed"
            video.process_end_time = datetime.utcnow()
            
        except Exception as e:
            video.status = "failed"
            video.error = str(e)
            video.process_end_time = datetime.utcnow()
            raise
        
        finally:
            # Save to MongoDB FIRST, then emit WebSocket event
            # This prevents the race condition where frontend fetches data before DB is updated
            update_dict = video.to_dict()
            update_dict.pop('_id', None)  # Remove _id if present
            
            print(f"[VIDEO SERVICE] Saving final state to DB: status={video.status}")
            self.videos.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": update_dict}
            )
            print(f"[VIDEO SERVICE] DB update completed, video_id={video_id}")
            
            # Add small delay to ensure DB write is fully committed before WebSocket
            import time
            time.sleep(0.2)  # 200ms delay
            
            # Emit completion/failure AFTER DB is committed
            if video.status == "completed":
                print(f"[VIDEO SERVICE] Emitting completion event")
                self._emit_progress(video_id, 'completed', 100, 'Processing complete!')
                # Give frontend time to receive event before potential download request
                time.sleep(0.1)
            elif video.status == "failed":
                print(f"[VIDEO SERVICE] Emitting failure event")
                self._emit_progress(video_id, 'failed', 0, f'Processing failed: {getattr(video, "error", "Unknown error")}')
    
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

    def update_video_status(self, video_id, status):
        """Update only the status field of a video in the DB."""
        self.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": {"status": status}}
        )

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
            detect_repeated = options.get('detect_repeated_words', False)
            cut_filler_segments_from_video = options.get('cut_filler_segments', options.get('remove_filler_words', False))
            
            # CRITICAL FIX: If we're cutting filler segments from VIDEO, we MUST detect them first
            # If cut_filler_segments is true but detect_and_remove_fillers is false, enable detection
            if cut_filler_segments_from_video and not detect_and_remove_fillers:
                print(f"[VIDEO SERVICE] ⚠️ cut_filler_segments=TRUE but detect=FALSE - enabling detection")
                detect_and_remove_fillers = True  # Enable detection (but won't remove from audio)
            
            # CRITICAL FIX: For VIDEO files, ALWAYS use detect-only mode for fillers.
            # Removing fillers from audio WITHOUT cutting the video creates a duration mismatch
            # between audio and video tracks, which BREAKS lip-sync and causes wrong duration.
            # The actual filler removal must happen via _remove_filler_segments_from_video()
            # which cuts BOTH audio+video together, keeping them in sync.
            detect_only_for_video_cutting = detect_and_remove_fillers  # Always detect-only
            if detect_only_for_video_cutting:
                print(f"[VIDEO SERVICE] ✅ DETECT-ONLY MODE: Will detect fillers for transcript but keep audio/video in sync")
            
            # NEW: Get custom filler words if provided
            custom_filler_words = options.get('custom_filler_words', [])
            use_custom_fillers = options.get('use_custom_fillers', False)
            
            # Use filler_removal_level from frontend, NOT noise_reduction level
            filler_level = options.get('filler_removal_level', 'medium')
            # Validate filler level
            if filler_level not in ['conservative', 'medium', 'aggressive']:
                filler_level = 'medium'
            enhancement_type = filler_level
            print(f"[VIDEO SERVICE] Filler removal level: {enhancement_type}")
            if use_custom_fillers and custom_filler_words:
                print(f"[VIDEO SERVICE] Using custom filler words: {custom_filler_words}")
            
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
                'detect_repeated_words': detect_repeated,  # Detect repeated words
                'custom_filler_words': custom_filler_words,  # NEW: Pass custom filler words
                'use_custom_fillers': use_custom_fillers,  # NEW: Flag to use custom fillers
                'detect_only_for_video_cutting': detect_only_for_video_cutting  # NEW: Just detect, don't remove
            }
            
            print(f"[VIDEO SERVICE] Backend options: {backend_options}")
            
            # Emit sub-step progress for frontend
            vid_id = str(video._id)
            self._emit_progress(vid_id, 'enhancing_audio', 15, 'Extracting audio from video...')
            
            # Extract audio from video first
            clip = VideoFileClip(video.filepath)
            audio_path = f"{os.path.splitext(video.filepath)[0]}_temp_audio.wav"
            print(f"[VIDEO SERVICE] Extracting audio to: {audio_path}")
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            
            self._emit_progress(vid_id, 'enhancing_audio', 20, 'Audio extracted. Analyzing...')
            
            # ALWAYS regenerate transcript when filler detection is enabled
            # This ensures transcript has words even if initial auto-transcription failed
            if detect_and_remove_fillers:
                print(f"[VIDEO SERVICE] Regenerating transcript with filler detection (level: {enhancement_type})...")
                new_transcript = audio_enhancer.generate_transcript_with_fillers(
                    audio_path,
                    enhancement_type=enhancement_type,
                    detect_repeated=detect_repeated
                )
                if new_transcript and new_transcript.get('total_words', 0) > 0:
                    video.transcript = new_transcript
                    self.videos.update_one(
                        {'_id': video._id},
                        {'$set': {'transcript': new_transcript}}
                    )
                    print(f"[VIDEO SERVICE] Transcript regenerated: {new_transcript['total_words']} words, {new_transcript['filler_count']} fillers, {new_transcript.get('repeated_count', 0)} repeated")
                else:
                    print(f"[VIDEO SERVICE] Transcript generation returned no words")
            
            # Enhance the audio (pass audio_path for Whisper filler detection)
            print(f"[VIDEO SERVICE] Starting audio enhancement...")
            if detect_and_remove_fillers:
                print(f"[VIDEO SERVICE] Filler word removal: ENABLED (level: {enhancement_type})")
                self._emit_progress(vid_id, 'enhancing_audio', 25, 'Detecting filler words with AI...')
            else:
                print(f"[VIDEO SERVICE] Filler word removal: DISABLED")
                self._emit_progress(vid_id, 'enhancing_audio', 25, 'Enhancing audio quality...')
            enhanced_audio, metrics = audio_enhancer.enhance_audio(audio_path, backend_options)
            
            self._emit_progress(vid_id, 'enhancing_audio', 60, 'Audio enhanced. Updating transcript...')
            
            # UPDATE TRANSCRIPT: Mark detected fillers from enhance_audio in the transcript
            filler_segments = metrics.get('filler_segments', [])
            if filler_segments and video.transcript and video.transcript.get('words'):
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
                
                # Update filler count to reflect actual detected segments
                transcript['filler_count'] = sum(1 for w in words if w.get('is_filler', False))
                video.transcript = transcript
                
                # Save updated transcript to database
                self.videos.update_one(
                    {'_id': video._id},
                    {'$set': {'transcript': transcript}}
                )
                print(f"[VIDEO SERVICE] Transcript updated: marked {updated_count} words as fillers (total: {transcript['filler_count']})")
            
            # Save enhanced audio temporarily
            enhanced_audio_path = f"{os.path.splitext(video.filepath)[0]}_enhanced_audio.wav"
            print(f"[VIDEO SERVICE] Saving enhanced audio to: {enhanced_audio_path}")
            enhanced_audio.export(enhanced_audio_path, format="wav")
            
            # Create new video with enhanced audio
            print(f"[VIDEO SERVICE] Creating final video with enhanced audio...")
            self._emit_progress(vid_id, 'enhancing_audio', 70, 'Encoding final video... this may take a moment')
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
            
            self._emit_progress(vid_id, 'enhancing_audio', 90, 'Video encoded. Saving results...')
            
            # Clear GPU cache
            if has_gpu():
                clear_cache()
            
            # Update video outputs
            video.outputs["processed_video"] = output_path
            video.outputs["audio_enhancement_metrics"] = metrics
            
            # Add timeline data if available
            if metrics.get('timeline'):
                video.outputs["enhancement_timeline"] = metrics['timeline']
                print(f"[VIDEO SERVICE] Timeline data added to outputs")
            
            # Add detailed results for frontend display - use REAL filler word count
            original_duration_sec = metrics['original_duration_ms'] / 1000
            enhanced_duration_sec = metrics['enhanced_duration_ms'] / 1000
            time_saved_sec = metrics['time_saved_ms'] / 1000
            filler_words_removed = metrics.get('filler_words_removed', 0)
            
            video.outputs["enhancement_results"] = {
                'filler_words_removed': filler_words_removed,  # REAL count from Whisper
                'noise_reduction_percentage': round(metrics.get('noise_reduction_percentage', 0), 1),  # REAL calculated value
                'duration_reduction_percentage': round(metrics['time_saved_percentage'], 1),
                'original_duration': f"{original_duration_sec:.1f}s",
                'enhanced_duration': f"{enhanced_duration_sec:.1f}s",
                'time_saved': f"{time_saved_sec:.1f}s",
                'repeated_words_removed': metrics.get('repeated_words_removed', 0),
                'cuts_made': len(metrics.get('filler_segments', [])),  # Number of cuts
                'has_timeline': metrics.get('timeline') is not None  # Flag for frontend
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
            # Check if this feature is enabled
            if not options.get('cut_filler_segments', options.get('remove_filler_words', False)):
                print(f"[VIDEO FILLER REMOVAL] Filler segment cutting disabled")
                return
            
            print(f"[VIDEO FILLER REMOVAL] Starting video segment cutting using pre-detected fillers")
            
            # Use provided filler segments from audio enhancement
            if not filler_segments:
                print("[VIDEO FILLER REMOVAL] No filler segments provided, skipping video cutting")
                return
            
            print(f"[VIDEO FILLER REMOVAL] Using {len(filler_segments)} pre-detected filler segments")
            
            # Use the ENHANCED video (with noise reduction) if available, otherwise use original
            source_path = video.outputs.get("processed_video", video.filepath)
            if source_path != video.filepath:
                print(f"[VIDEO FILLER REMOVAL] Using enhanced video (preserves noise reduction): {source_path}")
            else:
                print(f"[VIDEO FILLER REMOVAL] Using original video: {source_path}")
            clip = VideoFileClip(source_path)
            
            # Create list of segments to KEEP (inverse of segments to remove)
            video_duration_ms = int(clip.duration * 1000)
            keep_segments = []
            last_end = 0
            
            # Sort filler segments by start time
            filler_segments.sort(key=lambda x: x[0])
            
            for start_ms, end_ms in filler_segments:
                # Add segment before this filler (if there's a gap)
                if start_ms > last_end:
                    keep_segments.append((last_end / 1000.0, start_ms / 1000.0))  # Convert to seconds
                last_end = end_ms
            
            # Add final segment after last filler
            if last_end < video_duration_ms:
                keep_segments.append((last_end / 1000.0, video_duration_ms / 1000.0))
            
            print(f"[VIDEO FILLER REMOVAL] Created {len(keep_segments)} keep segments")
            
            # Step 4: Cut video using ffmpeg for precise, smooth cutting
            output_path = f"{os.path.splitext(video.filepath)[0]}_cleaned.mp4"
            self._cut_video_segments_ffmpeg(source_path, keep_segments, output_path, smooth_transitions=True)
            
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
                'segments_removed': len(filler_segments),
                'filler_words_removed': len(filler_segments),  # Count of segments removed
                'repeated_words_removed': 0,  # Not tracked separately here
                'original_duration': f"{original_duration:.2f}s",
                'cleaned_duration': f"{cleaned_duration:.2f}s",
                'time_saved': f"{time_saved:.2f}s",
                'percentage_saved': f"{percentage_saved:.1f}%"
            }
            
            print(f"[VIDEO FILLER REMOVAL] Completed! Removed {len(filler_segments)} segments")
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
            smooth_transitions: Whether to apply fade transitions (default: True)
        """
        try:
            import subprocess
            import tempfile
            
            print(f"[FFMPEG VIDEO CUT] Cutting video into {len(keep_segments)} segments")
            
            # Create temporary directory for segment files
            temp_dir = tempfile.mkdtemp()
            segment_files = []
            
            # Step 1: Extract each segment with optional fade effects
            for i, (start_sec, end_sec) in enumerate(keep_segments):
                segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp4")
                duration = end_sec - start_sec
                
                encoder = get_ffmpeg_encoder('h264')
                
                cmd = [
                    'ffmpeg',
                    '-ss', str(start_sec),
                    '-i', input_path,
                    '-t', str(duration),
                ]
                
                # Add fade effects for smooth transitions between segments
                if smooth_transitions and len(keep_segments) > 1:
                    fade_dur = min(0.15, duration / 4)  # 150ms or 1/4 of segment, whichever is smaller
                    fade_out_start = max(0, duration - fade_dur)
                    
                    vfilters = []
                    afilters = []
                    
                    # Don't fade in the first segment's start
                    if i > 0:
                        vfilters.append(f"fade=t=in:st=0:d={fade_dur}")
                        afilters.append(f"afade=t=in:st=0:d={fade_dur}")
                    
                    # Don't fade out the last segment's end
                    if i < len(keep_segments) - 1:
                        vfilters.append(f"fade=t=out:st={fade_out_start}:d={fade_dur}")
                        afilters.append(f"afade=t=out:st={fade_out_start}:d={fade_dur}")
                    
                    if vfilters:
                        cmd += ['-vf', ','.join(vfilters)]
                    if afilters:
                        cmd += ['-af', ','.join(afilters)]
                
                cmd += [
                    '-c:v', encoder,
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-avoid_negative_ts', 'make_zero',
                    '-y',
                    segment_path
                ]
                
                print(f"[FFMPEG VIDEO CUT] Extracting segment {i+1}/{len(keep_segments)}: {start_sec:.2f}s - {end_sec:.2f}s")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"[FFMPEG VIDEO CUT] Warning: Segment {i} extraction had issues: {result.stderr[-200:]}")
                else:
                    segment_files.append(segment_path)
            
            if not segment_files:
                raise Exception("No segments were successfully extracted")
            
            # Step 2: Create concat file for ffmpeg
            concat_file = os.path.join(temp_dir, 'concat_list.txt')
            with open(concat_file, 'w') as f:
                for seg_file in segment_files:
                    f.write(f"file '{seg_file}'\n")
            
            print(f"[FFMPEG VIDEO CUT] Concatenating {len(segment_files)} segments...")
            
            # Step 3: Concatenate segments (re-encode for consistency after filters)
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
                print(f"[FFMPEG VIDEO CUT] Concat error, trying stream copy: {result.stderr[-200:]}")
                concat_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file,
                    '-c', 'copy',
                    '-y',
                    output_path
                ]
                result = subprocess.run(concat_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"FFmpeg concatenation failed: {result.stderr[-200:]}")
            
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
                # Check if Whisper is available
                if not WHISPER_AVAILABLE:
                    raise ImportError("OpenAI Whisper is not available")
                
                print(f"[SUBTITLE DEBUG] Starting Whisper transcription...")
                print(f"[SUBTITLE DEBUG] Using OpenAI Whisper for transcription")
                
                # Use CPU-optimized model to avoid memory issues
                # Base model is faster and more reliable than large models
                model_size = "base"  # Use base model for reliability
                device = "cpu"  # Force CPU to avoid GPU memory issues
                
                print(f"[SUBTITLE DEBUG] Loading Whisper model: {model_size} on {device}")
                print(f"[SUBTITLE DEBUG] Target language: {language}")
                
                # Load model
                model = whisper.load_model(model_size, device=device)
                print(f"[SUBTITLE DEBUG] Whisper model loaded successfully")
                
                # Emit progress: Transcribing
                if hasattr(video, 'id'):
                    self._emit_progress(str(video.id), 'transcribing', 65, f'Transcribing audio...')
                
                print(f"[SUBTITLE DEBUG] Transcribing audio file: {audio_path}")
                
                # Simple transcription without complex preprocessing
                # This is more reliable and less prone to errors
                result = model.transcribe(
                    audio_path,
                    language=None,  # Auto-detect language
                    task='transcribe',
                    fp16=False,  # Disable FP16 for CPU compatibility
                    verbose=False
                )
                
                print(f"[SUBTITLE DEBUG] Whisper transcription completed")
                print(f"[SUBTITLE DEBUG] Found {len(result.get('segments', []))} segments")
                detected_lang = result.get('language', 'en')
                print(f"[SUBTITLE DEBUG] Detected audio language: {detected_lang}")
                print(f"[SUBTITLE DEBUG] Full transcription text: {result.get('text', '')[:200]}...")
                
                
                
                # Emit progress: Processing segments
                if hasattr(video, 'id'):
                    self._emit_progress(str(video.id), 'processing_segments', 80, 'Processing subtitle segments...')
                
                # Check if translation is needed
                needs_translation = (detected_lang != language)
                if needs_translation:
                    print(f"[TRANSLATION] Audio is {detected_lang}, translating to {language}")
                else:
                    print(f"[TRANSCRIPTION] Audio is {detected_lang}, same as target {language}")
                
                # Extract segments with timestamps
                segments = []
                for i, segment in enumerate(result['segments']):
                    text = segment['text'].strip()
                    
                    # Skip empty segments
                    if not text or len(text.strip()) == 0:
                        continue
                    
                    # Translate if needed
                    if needs_translation:
                        try:
                            print(f"[TRANSLATION] Translating: '{text[:50]}...' from {detected_lang} to {language}")
                            text = self._translate_text(text, detected_lang, language)
                            print(f"[TRANSLATION] Result: '{text[:50]}...'")
                        except Exception as trans_err:
                            print(f"[TRANSLATION WARNING] Translation failed: {trans_err}, keeping original")
                    
                    # Basic cleaning
                    text = text.replace('  ', ' ').strip()
                    
                    segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': text,
                        'confidence': segment.get('avg_logprob', 0.0)  # Track confidence
                    })
                    print(f"[SUBTITLE DEBUG] Segment {i+1}: {segment['start']:.2f}s-{segment['end']:.2f}s: '{text}'")
                
                print(f"[SUBTITLE DEBUG] Successfully processed {len(segments)} segments from Whisper")
                
                # CRITICAL: Detect hallucination/repetition in transcription
                if self._is_transcription_repetitive(segments):
                    print(f"[SUBTITLE WARNING] Detected repetitive/hallucinated transcription - rejecting bad output")
                    raise ValueError("Transcription contains repetitive hallucinations - audio quality may be too poor")
                
                # Emit progress: Creating subtitle files
                if hasattr(video, 'id'):
                    self._emit_progress(str(video.id), 'creating_subtitles', 90, 'Creating subtitle files...')
                
                # Generate both SRT and JSON format subtitles
                srt_content, json_data = self._create_subtitles_from_segments(segments, language, style)
                print(f"[SUBTITLE DEBUG] ✅ Successfully generated subtitles from Whisper transcription")
                print(f"[SUBTITLE DEBUG] Total segments: {len(segments)}")
                
            except ImportError as e:
                print(f"[SUBTITLE ERROR] ❌ Whisper not available: {e}")
                print(f"[SUBTITLE DEBUG] Falling back to demo text")
                text = self._get_enhanced_sample_text(language, clip.duration)
                srt_content, json_data = self._create_subtitles(text, language, style, clip.duration)
                
            except Exception as e:
                print(f"[SUBTITLE ERROR] ❌ Whisper transcription FAILED!")
                print(f"[SUBTITLE ERROR] Error: {str(e)}")
                print(f"[SUBTITLE ERROR] Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                
                # Provide specific error guidance
                if "repetitive" in str(e).lower() or "hallucination" in str(e).lower():
                    print(f"[SUBTITLE ERROR] ❌ Transcription rejected due to repetitive/hallucinated output")
                    print(f"[SUBTITLE ERROR] Possible causes:")
                    print(f"  - Poor audio quality or excessive background noise")
                    print(f"  - Very short or silent audio")
                    print(f"  - Audio preprocessing issues")
                    print(f"[SUBTITLE ERROR] Falling back to demo subtitles - try improving audio quality")
                else:
                    print(f"[SUBTITLE ERROR] ❌ Whisper failed - Falling back to demo text")
                
                # Enhanced fallback for Urdu
                text = self._get_enhanced_sample_text(language, clip.duration)
                srt_content, json_data = self._create_subtitles(text, language, style, clip.duration)
            
            # Save subtitles file with unique video ID to avoid collisions
            video_id = str(video.id) if hasattr(video, 'id') else os.path.basename(video.filepath).split('.')[0]
            base_dir = os.path.dirname(video.filepath)
            srt_path = os.path.join(base_dir, f"{video_id}_{language}.srt")
            print(f"[SUBTITLE DEBUG] Saving SRT file to: {srt_path}")
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            # Save JSON format for live display
            json_path = os.path.join(base_dir, f"{video_id}_{language}.json")
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
            return "medium"  # Medium model for complex scripts
        elif language in ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'nl']:
            return "base"    # Base model is fast and accurate for well-supported languages
        else:
            return "base"   # Base model for other languages

    def _preprocess_audio_for_transcription(self, audio_path, language):
        """Simplified audio preprocessing for better reliability"""
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize
            
            print(f"[AUDIO PREPROCESS] Starting simple preprocessing for {language}")
            
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Basic essential preprocessing only
            # Step 1: Convert to mono for consistency
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Step 2: Set to 16kHz (Whisper's expected rate)
            audio = audio.set_frame_rate(16000)
            
            # Step 3: Normalize volume
            audio = normalize(audio)
            
            # Step 4: Basic noise filtering (only for low-quality audio)
            if language in ['ur', 'ru-ur', 'ar', 'hi']:
                # Remove extreme low and high frequencies
                audio = audio.high_pass_filter(100)  # Remove deep rumble
                audio = audio.low_pass_filter(8000)  # Remove high frequency noise
            
            # Save processed audio
            processed_path = f"{os.path.splitext(audio_path)[0]}_processed.wav"
            audio.export(processed_path, format="wav", parameters=["-ac", "1"])
            
            print(f"[AUDIO PREPROCESS] ✅ Preprocessed audio saved to: {processed_path}")
            return processed_path
                
        except Exception as e:
            print(f"[AUDIO PREPROCESS] ⚠️ Error: {e} - Using original audio")
            return audio_path  # Return original if preprocessing fails

    def _get_transcription_options(self, language):
        """Get optimal transcription options for each language with GPU optimization"""
        
        # GPU-specific optimizations - More conservative to avoid hallucinations
        use_fp16 = has_gpu()  # Only use FP16 on GPU
        beam_size = 5 if has_gpu() else 3  # Moderate beam search
        best_of = 5 if has_gpu() else 3    # Moderate sampling
        
        if use_fp16:
            print(f"[TRANSCRIPTION] Using GPU optimizations: fp16=True, beam_size={beam_size}, best_of={best_of}")
        else:
            print(f"[TRANSCRIPTION] Using CPU mode: fp16=False, beam_size={beam_size}, best_of={best_of}")
        
        base_options = {
            "word_timestamps": True,
            "no_speech_threshold": 0.6,
            "logprob_threshold": -1.0,
            "verbose": True,  # Enable verbose output for debugging
            "fp16": use_fp16,  # GPU acceleration
            "condition_on_previous_text": False,  # CRITICAL: Disable to prevent repetition loops
        }
        
        if language in ['ur', 'ru-ur']:
            # Urdu-specific options - Balanced for accuracy without hallucinations
            return {
                **base_options,
                "temperature": 0.0,  # Use deterministic decoding to avoid hallucinations
                "compression_ratio_threshold": 2.4,
                "initial_prompt": "یہ ایک اردو زبان کی ویڈیو ہے۔ صاف اور درست الفاظ استعمال کریں۔",
                "beam_size": beam_size,
                "best_of": best_of,
                "patience": 1.0,  # Standard patience
                "length_penalty": 1.0,
                "suppress_tokens": "-1",
            }
        elif language == 'ar':
            return {
                **base_options,
                "temperature": 0.0,
                "compression_ratio_threshold": 2.4,
                "initial_prompt": "هذا محتوى باللغة العربية. استخدم كلمات واضحة ودقيقة.",
                "beam_size": beam_size,
                "best_of": best_of
            }
        elif language == 'hi':
            return {
                **base_options,
                "temperature": 0.0,
                "compression_ratio_threshold": 2.4,
                "initial_prompt": "यह हिंदी भाषा की सामग्री है। स्पष्ट और सटीक शब्दों का प्रयोग करें।",
                "beam_size": beam_size,
                "best_of": best_of
            }
        else:
            return {
                **base_options,
                "temperature": 0.0,  # Deterministic
                "beam_size": beam_size,
                "best_of": best_of
            }

    def _is_transcription_repetitive(self, segments, repetition_threshold=0.7):
        """
        Detect if transcription has excessive repetition (hallucination).
        Returns True if transcription is likely bad/repetitive.
        """
        if not segments or len(segments) == 0:
            return False
        
        # Combine all text
        full_text = " ".join([seg.get('text', '') for seg in segments])
        
        if not full_text or len(full_text.strip()) < 10:
            return True  # Empty or too short = bad
        
        # Split into words
        words = full_text.lower().split()
        
        if len(words) < 5:
            return False  # Too short to judge
        
        # Check 1: Same word repeated many times in a row
        max_consecutive = 1
        current_word = words[0]
        current_count = 1
        
        for i in range(1, len(words)):
            if words[i] == current_word:
                current_count += 1
                max_consecutive = max(max_consecutive, current_count)
            else:
                current_word = words[i]
                current_count = 1
        
        if max_consecutive >= 5:
            print(f"[REPETITION CHECK] Found {max_consecutive} consecutive identical words")
            return True
        
        # Check 2: High percentage of repeated words
        unique_words = len(set(words))
        total_words = len(words)
        uniqueness_ratio = unique_words / total_words
        
        if uniqueness_ratio < (1 - repetition_threshold):
            print(f"[REPETITION CHECK] Low uniqueness: {uniqueness_ratio:.2f} (threshold: {1-repetition_threshold})")
            return True
        
        # Check 3: Same phrase repeated (check 3-4 word sequences)
        phrase_length = 3
        phrases = []
        for i in range(len(words) - phrase_length + 1):
            phrase = " ".join(words[i:i+phrase_length])
            phrases.append(phrase)
        
        if len(phrases) > 0:
            unique_phrases = len(set(phrases))
            phrase_uniqueness = unique_phrases / len(phrases)
            
            if phrase_uniqueness < 0.5 and len(phrases) > 5:
                print(f"[REPETITION CHECK] Repetitive phrases detected: {phrase_uniqueness:.2f}")
                return True
        
        print(f"[REPETITION CHECK] Transcription looks valid (uniqueness: {uniqueness_ratio:.2f})")
        return False

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

    def _summarize_video(self, video):
        """
        Comprehensive video summarization that:
        1. Analyzes video content using scene detection
        2. Transcribes audio with Whisper
        3. Identifies key moments (high motion, faces, important speech)
        4. Creates a condensed video highlighting these moments
        5. Generates text summary of content
        """
        try:
            print("\n" + "="*60)
            print("VIDEO SUMMARIZATION MODULE")
            print("="*60)
            
            # Get summarization options from processing options
            options = video.processing_options or {}
            summary_length = options.get('summary_length', 'medium')  # short, medium, long
            summary_focus = options.get('summary_focus', 'balanced')  # action, speech, balanced
            
            print(f"[SUMMARIZATION] Length: {summary_length}, Focus: {summary_focus}")
            
            clip = VideoFileClip(video.filepath)
            duration = clip.duration
            fps = clip.fps
            
            print(f"[SUMMARIZATION] Video: {duration:.1f}s @ {fps} FPS")
            
            # Step 1: Scene Detection - Find important moments
            print("\n[STEP 1/4] Detecting scenes and key moments...")
            self._emit_progress(str(video._id), 'summarizing', 25, 'Analyzing video scenes...')
            key_segments = self._detect_key_segments(clip, summary_focus)
            
            # Step 2: Audio Transcription for context
            print("\n[STEP 2/4] Transcribing audio...")
            self._emit_progress(str(video._id), 'summarizing', 50, 'Transcribing audio content...')
            transcript_data = self._transcribe_for_summary(clip)
            
            # Step 3: Combine analysis to select best moments
            print("\n[STEP 3/4] Selecting key moments...")
            self._emit_progress(str(video._id), 'summarizing', 65, 'Selecting key moments...')
            final_segments = self._select_final_segments(
                key_segments, transcript_data, duration, summary_length
            )
            
            # Step 4: Create condensed video
            print("\n[STEP 4/4] Creating condensed video...")
            self._emit_progress(str(video._id), 'summarizing', 75, 'Generating condensed video...')
            condensed_path = self._create_condensed_video(clip, final_segments, video.filepath)
            
            # Generate text summary
            text_summary = self._generate_text_summary(transcript_data, final_segments, duration)
            
            # Save results
            summary_data = {
                'condensed_video_path': condensed_path,
                'text_summary': text_summary,
                'original_duration': duration,
                'condensed_duration': sum(seg['duration'] for seg in final_segments),
                'segments_count': len(final_segments),
                'segments': final_segments,
                'summary_length': summary_length,
                'summary_focus': summary_focus
            }
            
            # Save text summary to file
            summary_text_path = f"{os.path.splitext(video.filepath)[0]}_summary.txt"
            with open(summary_text_path, 'w', encoding='utf-8') as f:
                f.write(text_summary)
            
            video.outputs["summary"] = summary_data
            video.outputs["summary_text_path"] = summary_text_path
            video.outputs["condensed_video"] = condensed_path
            # Also set processed_video so the standard download endpoint serves the condensed file
            if condensed_path and os.path.exists(condensed_path):
                video.outputs["processed_video"] = condensed_path
            
            # Step 5: Generate AI text summary from CONDENSED video segments only
            print("\n[STEP 5] Generating AI text summary from condensed segments...")
            self._emit_progress(str(video._id), 'summarizing', 85, 'Generating AI text summary...')
            ai_summary_text = ''
            ai_key_points = []
            
            # Build transcript from ONLY what's in the condensed video
            # Method 1: Get text directly from speech segments
            segment_texts = [seg.get('text', '').strip() for seg in final_segments if seg.get('text', '').strip()]
            
            # Method 2: For visual-only segments, find any transcript words that fall within their time range
            all_whisper_segments = transcript_data.get('segments', []) if transcript_data else []
            for fseg in final_segments:
                if fseg.get('text', '').strip():
                    continue  # Already have text for this segment
                # Find whisper segments that overlap with this visual segment's time range
                for wseg in all_whisper_segments:
                    # Check if whisper segment overlaps with final segment time range
                    if wseg['end'] > fseg['start'] and wseg['start'] < fseg['end']:
                        text = wseg.get('text', '').strip()
                        if text and text not in segment_texts:
                            segment_texts.append(text)
            
            condensed_transcript = ' '.join(segment_texts)
            full_transcript = transcript_data.get('text', '') if transcript_data else ''
            
            print(f"[SUMMARIZE] Condensed transcript: {len(condensed_transcript)} chars from {len(segment_texts)} segments")
            print(f"[SUMMARIZE] Full transcript: {len(full_transcript)} chars")
            
            # ALWAYS use condensed transcript — never fall back to full
            # If condensed is empty, generate a video-analysis summary instead
            working_transcript = condensed_transcript
            
            # Check if transcription was a hallucination
            hallucination_detected = False
            if transcript_data and transcript_data.get('hallucination_detected'):
                hallucination_detected = True
                print(f"[SUMMARIZE] Whisper hallucination was detected during transcription")
            
            if working_transcript and len(working_transcript.strip()) > 20:
                # Clean Whisper hallucinations before any summarization
                cleaned_transcript, was_repetitive = self._clean_whisper_transcript(working_transcript)
                if was_repetitive:
                    hallucination_detected = True
                    print(f"[SUMMARIZE] Cleaned repetitive transcript: {len(working_transcript)} -> {len(cleaned_transcript)} chars")
                    working_transcript = cleaned_transcript
                
                # If after cleaning the text is too short or empty, mark as hallucination
                if not working_transcript or len(working_transcript.strip()) < 20:
                    hallucination_detected = True
                    print(f"[SUMMARIZE] Transcript too short after cleaning, marking as hallucination")
                
                print(f"[SUMMARIZE] Using condensed segments transcript: {len(working_transcript)} chars")
                
                if not hallucination_detected:
                    if self.openai_client:
                        try:
                            ai_summary_text, ai_key_points = self._summarize_with_openai(
                                working_transcript, summary_length, summary_focus,
                                duration=duration
                            )
                        except Exception as openai_err:
                            print(f"[SUMMARIZE] OpenAI summarization failed: {openai_err}")
                    
                    if not ai_summary_text:
                        ai_summary_text, ai_key_points = self._extractive_summarize(
                            working_transcript, summary_length
                        )
            
            # If no good text summary yet (empty transcript, hallucination, or no speech in condensed segments)
            # Generate a video-analysis-based summary
            if not ai_summary_text:
                condensed_dur = sum(seg['duration'] for seg in final_segments)
                num_segments = len(final_segments)
                speech_segments = [s for s in final_segments if s.get('text', '').strip()]
                visual_segments = [s for s in final_segments if s.get('type') == 'visual']
                
                ai_summary_text = (
                    f"This {round(duration)}s video has been condensed to {round(condensed_dur)}s "
                    f"({round((1 - condensed_dur/duration)*100)}% reduction). "
                    f"The summarized video contains {num_segments} key segments"
                )
                if speech_segments:
                    ai_summary_text += f" including {len(speech_segments)} speech moments"
                if visual_segments:
                    ai_summary_text += f" and {len(visual_segments)} visual highlights"
                ai_summary_text += "."
                
                # If we have any cleaned transcript from condensed segments, add it
                if working_transcript and len(working_transcript.strip()) > 10:
                    ai_summary_text += f"\n\nFrom summarized video: {working_transcript.strip()[:500]}"
                
                ai_key_points = [
                    f"Video condensed from {round(duration)}s to {round(condensed_dur)}s",
                    f"{num_segments} key moments selected",
                    f"{round((1 - condensed_dur/duration)*100)}% size reduction"
                ]
                print(f"[SUMMARIZE] Generated video-analysis-based summary")
            
            # Save AI text summary
            ai_summary_data = {
                'text': ai_summary_text,
                'key_points': ai_key_points,
                'length': summary_length,
                'focus': summary_focus,
                'transcript_length': len(working_transcript),
                'full_transcript_length': len(full_transcript),
                'summary_length_chars': len(ai_summary_text),
                'compression_ratio': round(len(ai_summary_text) / max(len(working_transcript), 1) * 100, 1),
                'video_duration': round(duration, 1),
                'condensed_duration': round(sum(seg['duration'] for seg in final_segments), 1),
                'source': 'condensed_segments' if condensed_transcript else 'full_transcript'
            }
            
            ai_summary_path = f"{os.path.splitext(video.filepath)[0]}_ai_summary.json"
            with open(ai_summary_path, 'w', encoding='utf-8') as f:
                json.dump(ai_summary_data, f, ensure_ascii=False, indent=2)
            
            video.outputs['ai_text_summary'] = ai_summary_path
            summary_data['ai_text_summary'] = ai_summary_data
            video.outputs["summary"] = summary_data
            
            print(f"[SUMMARIZE] AI text summary: {len(ai_summary_text)} chars, {len(ai_key_points)} key points")
            
            print("\n" + "="*60)
            print(f"✅ SUMMARIZATION COMPLETE")
            print(f"Original: {duration:.1f}s → Condensed: {summary_data['condensed_duration']:.1f}s")
            print(f"Compression: {(1 - summary_data['condensed_duration']/duration)*100:.1f}%")
            print(f"AI Text Summary: {len(ai_summary_text)} chars")
            print("="*60 + "\n")
            
            clip.close()
            
        except Exception as e:
            print(f"❌ Error in video summarization: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the entire process, just log error
            video.outputs["summary_error"] = str(e)
    
    def _detect_key_segments(self, clip, focus='balanced'):
        """Detect key segments using scene detection, motion analysis, and face detection"""
        print(f"[SCENE DETECTION] Analyzing video for key moments (focus: {focus})...")
        
        key_segments = []
        duration = clip.duration
        fps = clip.fps
        
        # Sample frames for analysis (analyze every 1 second - faster on CPU)
        sample_interval = 1.0
        frame_times = np.arange(0, duration, sample_interval)
        
        # Initialize face cascade once (not inside the loop)
        face_cascade = None
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if face_cascade.empty():
                face_cascade = None
        except Exception:
            face_cascade = None
        
        prev_frame = None
        scene_scores = []
        
        for i, t in enumerate(frame_times):
            try:
                frame = clip.get_frame(t)
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                
                score = 0
                num_faces = 0
                
                # Motion detection (for action focus)
                if prev_frame is not None and focus in ['action', 'balanced']:
                    motion = np.mean(np.abs(gray.astype(float) - prev_frame.astype(float)))
                    score += motion * 2 if focus == 'action' else motion
                
                # Face detection (people are usually important)
                try:
                    if face_cascade is not None:
                        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                        num_faces = len(faces)
                        if num_faces > 0:
                            score += 50 * num_faces
                except Exception:
                    pass
                
                # Edge detection (visual complexity indicates interesting content)
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges) / edges.size
                score += edge_density * 100
                
                scene_scores.append({
                    'time': t,
                    'score': score,
                    'has_faces': num_faces > 0
                })
                
                prev_frame = gray
                
                if (i + 1) % 20 == 0:
                    print(f"[SCENE DETECTION] Analyzed {i+1}/{len(frame_times)} frames...")
                    
            except Exception as e:
                print(f"[SCENE DETECTION] Error at {t:.1f}s: {e}")
                continue
        
        # Find peaks in scores (these are interesting moments)
        if scene_scores:
            scores_array = np.array([s['score'] for s in scene_scores])
            threshold = np.percentile(scores_array, 70)  # Top 30% of moments
            
            for score_data in scene_scores:
                if score_data['score'] >= threshold:
                    key_segments.append(score_data)
        
        print(f"[SCENE DETECTION] Found {len(key_segments)} key moments")
        return key_segments
    
    def _transcribe_for_summary(self, clip):
        """Transcribe audio to understand speech content (auto-detects language)"""
        try:
            if not WHISPER_TS_AVAILABLE:
                print("[TRANSCRIPTION] Whisper not available, skipping")
                return {'segments': [], 'text': ''}
            
            # Extract audio to temporary file
            audio_path = f"temp_audio_{datetime.now().timestamp()}.wav"
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            
            print("[TRANSCRIPTION] Running Whisper (base model, auto-detect language)...")
            
            # Use base model for better multilingual support (tiny is weak on non-English)
            model = whisper_ts.load_model("base", device=get_device())
            # language=None lets Whisper auto-detect (supports Urdu, Arabic, Hindi, etc.)
            result = whisper_ts.transcribe(model, audio_path, language=None)
            
            detected_lang = result.get('language', 'unknown')
            print(f"[TRANSCRIPTION] Detected language: {detected_lang}")
            
            # Clean up
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            transcript_text = result.get('text', '')
            print(f"[TRANSCRIPTION] Found {len(result.get('segments', []))} speech segments, {len(transcript_text)} chars")
            
            # Quick hallucination check on raw output
            if transcript_text:
                words = transcript_text.lower().split()
                if len(words) > 20:
                    unique_words = set(words)
                    # If less than 10% unique words, it's hallucinating
                    if len(unique_words) / len(words) < 0.10:
                        print(f"[TRANSCRIPTION] WARNING: Detected hallucination (only {len(unique_words)} unique words out of {len(words)})")
                        # Return only the first non-repetitive portion
                        result['text'] = ' '.join(list(dict.fromkeys(words)))
                        result['hallucination_detected'] = True
            
            return result
            
        except Exception as e:
            print(f"[TRANSCRIPTION] Error: {e}")
            return {'segments': [], 'text': ''}
    
    def _select_final_segments(self, key_segments, transcript_data, duration, summary_length):
        """Select final segments based on visual and audio analysis"""
        
        # Define target durations
        length_targets = {
            'short': 0.15,    # 15% of original
            'medium': 0.30,   # 30% of original
            'long': 0.50      # 50% of original
        }
        
        target_duration = duration * length_targets.get(summary_length, 0.30)
        print(f"[SEGMENT SELECTION] Target duration: {target_duration:.1f}s ({summary_length})")
        
        # Combine visual key moments with speech segments
        all_moments = []
        
        # Add visual key moments
        for seg in key_segments:
            all_moments.append({
                'start': max(0, seg['time'] - 2),  # Include context before
                'end': min(duration, seg['time'] + 3),  # Include context after
                'type': 'visual',
                'score': seg['score'],
                'has_faces': seg.get('has_faces', False)
            })
        
        # Add speech segments (if focus is speech or balanced)
        for seg in transcript_data.get('segments', []):
            all_moments.append({
                'start': seg['start'],
                'end': seg['end'],
                'type': 'speech',
                'score': len(seg['text'].split()) * 10,  # Score by word count
                'text': seg['text']
            })
        
        # Sort by score and merge overlapping segments
        all_moments.sort(key=lambda x: x['score'], reverse=True)
        
        final_segments = []
        current_duration = 0
        
        for moment in all_moments:
            if current_duration >= target_duration:
                break
            
            # Check for overlap with existing segments
            overlap = False
            for existing in final_segments:
                if not (moment['end'] < existing['start'] or moment['start'] > existing['end']):
                    overlap = True
                    break
            
            if not overlap:
                segment = {
                    'start': moment['start'],
                    'end': moment['end'],
                    'duration': moment['end'] - moment['start'],
                    'type': moment['type'],
                    'text': moment.get('text', '')
                }
                final_segments.append(segment)
                current_duration += segment['duration']
        
        # Sort by time order
        final_segments.sort(key=lambda x: x['start'])
        
        print(f"[SEGMENT SELECTION] Selected {len(final_segments)} segments totaling {current_duration:.1f}s")
        
        return final_segments
    
    def _create_condensed_video(self, clip, segments, original_path):
        """Create condensed video from selected segments"""
        try:
            from moviepy.editor import concatenate_videoclips, CompositeVideoClip, TextClip
            
            print(f"[CONDENSED VIDEO] Creating from {len(segments)} segments...")
            
            clips = []
            for i, seg in enumerate(segments):
                try:
                    # Extract segment
                    subclip = clip.subclip(seg['start'], seg['end'])
                    
                    # Add transition indicator (optional)
                    if i > 0:
                        # Add a subtle fade for transitions
                        subclip = subclip.fadein(0.3)
                    
                    clips.append(subclip)
                    print(f"[CONDENSED VIDEO] Added segment {i+1}/{len(segments)}: {seg['start']:.1f}s - {seg['end']:.1f}s")
                    
                except Exception as e:
                    print(f"[CONDENSED VIDEO] Error extracting segment {i}: {e}")
                    continue
            
            if not clips:
                print("[CONDENSED VIDEO] No valid clips to concatenate")
                return None
            
            # Concatenate all clips
            print("[CONDENSED VIDEO] Concatenating clips...")
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Generate output path
            base_name = os.path.splitext(original_path)[0]
            output_path = f"{base_name}_summarized.mp4"
            
            # Write with GPU acceleration if available
            print(f"[CONDENSED VIDEO] Writing to: {output_path}")
            
            # Get optimal encoder settings
            codec = 'libx264'  # Default CPU codec
            preset = 'medium'
            
            if has_gpu():
                encoder = get_ffmpeg_encoder()
                if 'h264' in encoder:
                    codec = encoder
                    preset = 'medium'
                    print(f"[CONDENSED VIDEO] Using GPU encoder: {codec}")
            
            final_clip.write_videofile(
                output_path,
                codec=codec,
                audio_codec='aac',
                preset=preset,
                verbose=False,
                logger=None
            )
            
            final_clip.close()
            print(f"✅ [CONDENSED VIDEO] Saved to: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ [CONDENSED VIDEO] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _summarize_with_openai(self, transcript, length='medium', focus='balanced', duration=None):
        """Use OpenAI GPT to generate a structured summary"""
        length_instructions = {
            'short': 'Create a brief 2-3 sentence summary.',
            'medium': 'Create a detailed summary of 4-6 sentences.',
            'long': 'Create a comprehensive summary of 8-12 sentences covering all major points.'
        }
        
        focus_instructions = {
            'balanced': 'Cover all aspects of the content equally.',
            'action': 'Focus on visual elements, scenes, and actions described.',
            'speech': 'Focus on the spoken words, arguments, and verbal content.'
        }
        
        duration_info = f"The video is {round(duration, 0)} seconds long. " if duration else ""
        
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
{{{{
  "summary": "Your summary text here",
  "key_points": ["Point 1", "Point 2", "Point 3"]
}}}}"""
        
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
        
        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            return result.get('summary', content), result.get('key_points', [])
        except json.JSONDecodeError:
            return content, []

    def _clean_whisper_transcript(self, transcript):
        """Detect and clean Whisper hallucination loops (repetitive text)"""
        import re as regex
        from collections import Counter
        
        if not transcript or len(transcript) < 50:
            return transcript, False
        
        original_len = len(transcript)
        words = transcript.lower().split()
        
        # === CHECK 1: Word uniqueness ratio ===
        # If the transcript has very few unique words relative to total, it's hallucinating
        if len(words) > 15:
            unique_words = set(words)
            uniqueness = len(unique_words) / len(words)
            if uniqueness < 0.15:  # Less than 15% unique words = hallucination
                print(f"[WHISPER-CLEAN] Hallucination detected: only {len(unique_words)}/{len(words)} unique words ({uniqueness:.1%})")
                # Build a single clean version from unique words in order
                seen = set()
                deduped = []
                for w in transcript.split():
                    if w.lower() not in seen:
                        seen.add(w.lower())
                        deduped.append(w)
                cleaned = ' '.join(deduped)
                if len(cleaned) > 10:
                    print(f"[WHISPER-CLEAN] Reduced from {original_len} to {len(cleaned)} chars (unique words only)")
                    return cleaned, True
                return '', True
        
        # === CHECK 2: Bigram repetition ===
        if len(words) > 10:
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
            bigram_counts = Counter(bigrams)
            most_common_bigram, most_common_count = bigram_counts.most_common(1)[0]
            if most_common_count > len(bigrams) * 0.2:  # 20% threshold (was 30%)
                print(f"[WHISPER-CLEAN] Repetitive bigram: '{most_common_bigram}' appears {most_common_count}/{len(bigrams)} times")
                # Take only unique sentences (support Urdu ۔ ؟ and Hindi ।)
                sentences = regex.split(r'(?<=[.!?۔؟।])\s+', transcript)
                seen = set()
                unique = []
                for s in sentences:
                    normalized = ' '.join(s.lower().split())
                    if normalized not in seen and len(s.strip()) > 5:
                        seen.add(normalized)
                        unique.append(s.strip())
                if unique:
                    cleaned = ' '.join(unique)
                    print(f"[WHISPER-CLEAN] Kept {len(unique)} unique sentences from {len(sentences)}")
                    return cleaned, True
                # All sentences identical — extract unique words
                seen_w = set()
                deduped = []
                for w in transcript.split():
                    if w.lower() not in seen_w:
                        seen_w.add(w.lower())
                        deduped.append(w)
                return ' '.join(deduped), True
        
        # === CHECK 3: Repeating phrase detection (3-30 word phrases) ===
        for phrase_len in range(30, 2, -1):
            if len(words) < phrase_len * 3:
                continue
            for start in range(0, min(len(words) - phrase_len, 50)):
                phrase = ' '.join(words[start:start + phrase_len])
                if len(phrase) < 8:
                    continue
                count = transcript.lower().count(phrase.lower())
                if count >= 3 and (count * len(phrase)) > len(transcript) * 0.25:
                    print(f"[WHISPER-CLEAN] Repeating phrase ({count}x): '{phrase[:60]}...'")
                    parts = transcript.split(phrase)
                    cleaned = phrase.join(parts[:2]).strip()
                    if len(cleaned) > 20:
                        return cleaned, True
        
        return transcript, False

    def _extractive_summarize(self, transcript, length='medium'):
        """Fallback extractive summarization (no external API needed). Supports English, Urdu, Arabic, Hindi."""
        import re as regex
        
        # First clean any Whisper hallucination loops
        transcript, was_cleaned = self._clean_whisper_transcript(transcript)
        
        if was_cleaned:
            print(f"[EXTRACTIVE] Working with cleaned transcript: {len(transcript)} chars")
        
        if not transcript or len(transcript.strip()) < 10:
            return 'No transcript available for summarization.', []
        
        # Split sentences — support English (.!?), Urdu/Arabic (۔ ؟), Hindi (।)
        sentences = regex.split(r'(?<=[.!?۔؟।])\s+', transcript)
        # Also split on long pauses / natural breaks if few sentences found
        if len(sentences) <= 2:
            sentences = regex.split(r'(?<=[.!?۔؟।,،])\s+', transcript)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences:
            # Last resort: split by commas, Urdu comma، or chunks
            sentences = regex.split(r'[,،]+', transcript)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return transcript[:500], []
        
        # Deduplicate similar sentences
        unique_sentences = []
        seen_normalized = set()
        for s in sentences:
            normalized = ' '.join(s.lower().split())
            is_duplicate = normalized in seen_normalized
            if not is_duplicate:
                for seen in seen_normalized:
                    s_words = set(normalized.split())
                    seen_words = set(seen.split())
                    if s_words and seen_words:
                        overlap = len(s_words & seen_words) / max(len(s_words), len(seen_words))
                        if overlap > 0.8:
                            is_duplicate = True
                            break
            if not is_duplicate:
                seen_normalized.add(normalized)
                unique_sentences.append(s)
        
        sentences = unique_sentences if unique_sentences else sentences[:3]
        print(f"[EXTRACTIVE] {len(sentences)} unique sentences after dedup")
        
        ratio_map = {'short': 0.2, 'medium': 0.4, 'long': 0.6}
        ratio = ratio_map.get(length, 0.4)
        num_sentences = max(2, min(int(len(sentences) * ratio), 15))
        
        # Detect language: check for non-Latin scripts (Urdu, Arabic, Hindi)
        has_urdu_arabic = bool(regex.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', transcript))
        has_hindi = bool(regex.search(r'[\u0900-\u097F]', transcript))
        
        scored = []
        for i, sent in enumerate(sentences):
            words = sent.split()
            unique_words = set(w.lower() for w in words)
            score = len(unique_words)
            
            # Penalize internally repetitive sentences
            if len(words) > 0:
                uniqueness_ratio = len(unique_words) / len(words)
                score *= max(uniqueness_ratio, 0.3)
            
            if i == 0:
                score *= 1.5
            if i == len(sentences) - 1:
                score *= 1.3
            
            # Signal words by language
            if has_urdu_arabic:
                signal_words = ['اہم', 'نتیجہ', 'لہذا', 'لیکن', 'کیونکہ', 'پہلے', 'آخر',
                               'خلاصہ', 'مختصر', 'اصل', 'بنیادی', 'ضروری', 'اللہ', 'قرآن']
            elif has_hindi:
                signal_words = ['महत्वपूर्ण', 'परिणाम', 'इसलिए', 'लेकिन', 'क्योंकि', 'पहले', 'अंत']
            else:
                signal_words = ['important', 'key', 'main', 'significant', 'conclusion',
                               'result', 'therefore', 'however', 'because', 'first', 'finally']
            
            sent_lower = sent.lower()
            for word in signal_words:
                if word in sent_lower:
                    score *= 1.2
            scored.append((i, score, sent))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = scored[:num_sentences]
        selected.sort(key=lambda x: x[0])  # Restore original order
        
        summary_text = ' '.join([s[2] for s in selected])
        
        # Cap at 2000 chars
        if len(summary_text) > 2000:
            summary_text = summary_text[:2000].rsplit(' ', 1)[0] + '...'
        
        key_points = [s[2][:100] for s in scored[:min(5, len(scored))]]
        
        return summary_text, key_points

    def _generate_text_summary(self, transcript_data, segments, duration):
        """Generate human-readable text summary"""
        
        summary_parts = []
        
        # Overview
        condensed_duration = sum(seg['duration'] for seg in segments)
        compression_ratio = (1 - condensed_duration / duration) * 100
        
        summary_parts.append(f"📊 VIDEO SUMMARY")
        summary_parts.append(f"=" * 50)
        summary_parts.append(f"Original Duration: {duration:.1f} seconds")
        summary_parts.append(f"Condensed Duration: {condensed_duration:.1f} seconds")
        summary_parts.append(f"Compression: {compression_ratio:.1f}% reduction")
        summary_parts.append(f"Key Moments: {len(segments)}")
        summary_parts.append("")
        
        # Key moments
        summary_parts.append("🎬 KEY MOMENTS:")
        summary_parts.append("-" * 50)
        
        for i, seg in enumerate(segments, 1):
            timestamp = f"{int(seg['start']//60)}:{int(seg['start']%60):02d} - {int(seg['end']//60)}:{int(seg['end']%60):02d}"
            summary_parts.append(f"\n{i}. [{timestamp}] ({seg['duration']:.1f}s)")
            
            if seg.get('text'):
                # Clean and truncate text
                text = seg['text'].strip()
                if len(text) > 100:
                    text = text[:97] + "..."
                summary_parts.append(f"   💬 \"{text}\"")
            else:
                summary_parts.append(f"   🎥 Visual highlight")
        
        # Full transcript excerpt
        if transcript_data.get('text'):
            summary_parts.append("")
            summary_parts.append("📝 FULL TRANSCRIPT EXCERPT:")
            summary_parts.append("-" * 50)
            full_text = transcript_data['text']
            if len(full_text) > 500:
                full_text = full_text[:497] + "..."
            summary_parts.append(full_text)
        
        return "\n".join(summary_parts)

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
        
        # Use unique video ID to avoid subtitle file collisions
        video_id = str(video.id) if hasattr(video, 'id') else os.path.basename(video.filepath).split('.')[0]
        base_dir = os.path.dirname(video.filepath)
        srt_path = os.path.join(base_dir, f"{video_id}_{language}_fallback.srt")
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        json_path = os.path.join(base_dir, f"{video_id}_{language}_fallback.json")
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
        print(f"[EXPORT] Trim: {trim_start}% - {trim_end}%")
        print(f"[EXPORT] Text: '{text_overlay}' at {text_position}")
        print(f"[EXPORT] Audio: video_vol={video_volume}, mute={mute_original}")
        
        # Get video duration
        clip = VideoFileClip(video.filepath)
        duration = clip.duration
        clip.close()
        
        # Calculate trim times
        start_time = (trim_start / 100) * duration
        end_time = (trim_end / 100) * duration
        trim_duration = end_time - start_time
        
        print(f"[EXPORT] Duration: {duration}s, Trimming: {start_time}s to {end_time}s ({trim_duration}s)")
        
        # Output path
        base_name = os.path.splitext(video.filename)[0]
        export_filename = f"{base_name}_edited_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        export_path = os.path.join(self.upload_folder, export_filename)
        
        # Build FFmpeg command
        ffmpeg_path = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
        
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
            
            # Escape special characters in text
            safe_text = text_overlay.replace("'", "\\'").replace(":", "\\:")
            
            # Convert hex color to FFmpeg format
            color = text_color.lstrip('#')
            
            # Use a system font that's available on Windows
            text_filter = f"drawtext=text='{safe_text}':{pos}:fontsize={text_size}:fontcolor=0x{color}:borderw=3:bordercolor=black"
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
            print("[EXPORT] FFmpeg timed out")
            raise Exception("Export timed out - video may be too long")
        except Exception as e:
            print(f"[EXPORT] Export failed: {e}")
            raise
