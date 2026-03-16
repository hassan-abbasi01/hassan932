# 🎓 FYP VIVA PREPARATION NOTES
## SnipX - AI-Powered Video Enhancement Platform

---

# 📋 TABLE OF CONTENTS
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Video Enhancement Module](#3-video-enhancement-module)
4. [Subtitles Module](#4-subtitles-module)
5. [React Frontend](#5-react-frontend)
6. [Flask Backend](#6-flask-backend)
7. [MongoDB Database](#7-mongodb-database)
8. [API Endpoints](#8-api-endpoints)
9. [Key Code Snippets](#9-key-code-snippets)
10. [Common Viva Questions](#10-common-viva-questions)

---

# 1. PROJECT OVERVIEW

## 1.1 What is SnipX?
SnipX is an **AI-powered video enhancement platform** that provides:
- **Automatic subtitle generation** using OpenAI Whisper (supports 16+ languages including Urdu)
- **AI-powered thumbnail generation** using BLIP image captioning
- **Audio enhancement** with noise reduction, filler word removal, and silence cutting
- **Video color enhancement** using AI-based analysis
- **Real-time video editing** capabilities

## 1.2 Technology Stack
| Layer | Technologies |
|-------|-------------|
| **Frontend** | React, TypeScript, Tailwind CSS, Vite |
| **Backend** | Python, Flask, Flask-CORS |
| **Database** | MongoDB with PyMongo |
| **AI/ML** | OpenAI Whisper, BLIP (Salesforce), TensorFlow, PyTorch |
| **Video Processing** | MoviePy, OpenCV, FFmpeg |
| **Audio Processing** | PyDub, Librosa, SciPy |
| **Authentication** | JWT (JSON Web Tokens), bcrypt, OAuth 2.0 (Google) |

## 1.3 Key Features
1. ✅ Multi-language subtitle generation (16+ languages)
2. ✅ AI-powered YouTube thumbnail generation
3. ✅ Audio enhancement and noise reduction
4. ✅ Silence detection and removal
5. ✅ Video color/brightness/contrast enhancement
6. ✅ User authentication (JWT + Google OAuth)
7. ✅ Video management dashboard
8. ✅ Support ticket system

---

# 2. SYSTEM ARCHITECTURE

## 2.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT SIDE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   React     │  │  TypeScript │  │  Tailwind   │              │
│  │   Frontend  │  │   API       │  │    CSS      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SERVER SIDE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Flask     │  │   Video     │  │   Auth      │              │
│  │   Backend   │  │   Service   │  │   Service   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Whisper   │  │   BLIP      │  │   OpenCV    │              │
│  │   ASR       │  │   Captioner │  │   Processing│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      MongoDB                             │    │
│  │   Collections: users, videos, support_tickets            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 2.2 Data Flow
1. User uploads video → Frontend sends to `/api/upload`
2. Backend saves file → Creates MongoDB document
3. User triggers processing → Backend processes with AI models
4. Results saved → Thumbnails, subtitles, enhanced video stored
5. Frontend fetches results → Displays to user

---

# 3. VIDEO ENHANCEMENT MODULE

## 3.1 Overview
The video enhancement module provides:
- **AI Color Enhancement** - Automatic brightness, contrast, saturation adjustment
- **Audio Enhancement** - Noise reduction, filler word removal
- **Silence Cutting** - Remove silent parts from video
- **Thumbnail Generation** - AI-powered YouTube thumbnails

## 3.2 AI Color Enhancement
```python
class AIColorEnhancer:
    """AI-based automatic color and saturation enhancement"""
    
    def __init__(self):
        self.optimal_saturation_range = (0.3, 0.7)
        
    def analyze_video_colors(self, video_path, sample_frames=30):
        """Analyze video to determine optimal color adjustments"""
        cap = cv2.VideoCapture(video_path)
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, total_frames // sample_frames)
        
        saturation_values = []
        brightness_values = []
        contrast_values = []
        
        while cap.isOpened() and analyzed < sample_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Convert to HSV for analysis
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Get saturation (S channel)
            saturation = hsv[:, :, 1] / 255.0
            saturation_values.append(np.mean(saturation))
            
            # Get brightness (V channel)
            brightness = hsv[:, :, 2] / 255.0
            brightness_values.append(np.mean(brightness))
            
            # Calculate contrast (std dev of brightness)
            contrast_values.append(np.std(brightness))
        
        cap.release()
        
        return {
            'saturation': np.mean(saturation_values),
            'brightness': np.mean(brightness_values),
            'contrast': np.mean(contrast_values)
        }
    
    def apply_ai_enhancement(self, frame, saturation_mult, brightness_mult, contrast_mult):
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
            enhanced = np.clip((enhanced - 128) * contrast_mult + 128, 0, 255)
        
        return enhanced.astype(np.uint8)
```

## 3.3 Audio Enhancement
```python
class AudioEnhancer:
    """AI-powered audio enhancement with filler word removal and noise reduction"""
    
    def enhance_audio(self, audio_path, options):
        """Main audio enhancement pipeline"""
        audio = AudioSegment.from_file(audio_path)
        
        # Step 1: Remove silence/pauses
        audio = self._remove_silence(audio, options.get('pause_threshold', 500))
        
        # Step 2: Remove filler words
        audio = self._remove_fillers(audio, options.get('enhancement_type', 'medium'))
        
        # Step 3: Noise reduction
        audio = self._reduce_noise(audio, options.get('noise_reduction', 'moderate'))
        
        # Step 4: Normalize and compress
        audio = normalize(audio)
        audio = compress_dynamic_range(audio, threshold=-20.0, ratio=4.0)
        
        return audio
    
    def _remove_silence(self, audio, min_silence_len=500):
        """Remove silent sections from audio"""
        silence_thresh = audio.dBFS - 14  # Adaptive threshold
        
        # Split on silence
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=100  # Keep 100ms for natural sound
        )
        
        # Combine chunks with small gaps
        combined = AudioSegment.empty()
        for chunk in chunks:
            combined += chunk
            combined += AudioSegment.silent(duration=50)
        
        return combined
    
    def _reduce_noise(self, audio, level='moderate'):
        """Apply noise reduction based on level"""
        if level == 'moderate':
            audio = audio.high_pass_filter(80)  # Remove low-frequency rumble
            audio = audio.low_pass_filter(8000)  # Remove high-frequency noise
            audio = normalize(audio)
        elif level == 'strong':
            audio = audio.high_pass_filter(100)
            audio = audio.low_pass_filter(7000)
            audio = compress_dynamic_range(audio)
            audio = self._apply_spectral_noise_reduction(audio)
        
        return audio
```

## 3.4 AI Thumbnail Generation
```python
class AIThumbnailGenerator:
    """AI-powered YouTube thumbnail generator with BLIP captioning"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
    def _load_model(self):
        """Lazy load BLIP model for image captioning"""
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        ).to(self.device)
    
    def generate_catchy_text(self, frame_path, video_filename):
        """Generate catchy text using AI image captioning"""
        self._load_model()
        
        # Load and process image
        image = Image.open(frame_path).convert('RGB')
        
        # Generate caption using BLIP
        inputs = self.processor(image, return_tensors="pt").to(self.device)
        out = self.model.generate(**inputs, max_length=20)
        caption = self.processor.decode(out[0], skip_special_tokens=True)
        
        # Convert to catchy thumbnail text
        return self._make_catchy(caption, video_filename)
    
    def _calculate_frame_quality(self, frame):
        """Calculate quality score for a frame using multiple metrics"""
        score = 0.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        score += min(laplacian_var / 500, 1.0) * 0.35
        
        # 2. Brightness Score
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 127.5) / 127.5
        score += brightness_score * 0.20
        
        # 3. Color Richness (saturation)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:,:,1])
        score += min(saturation / 180, 1.0) * 0.20
        
        # 4. Face Detection Score
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        score += min(len(faces) * 0.5, 1.0) * 0.15
        
        # 5. Composition Score (rule of thirds)
        score += self._calculate_composition_score(frame) * 0.10
        
        return score
    
    def create_youtube_thumbnail(self, frame_path, text, output_path):
        """Create professional YouTube thumbnail"""
        img = Image.open(frame_path).convert('RGB')
        
        # Resize to YouTube format (1280x720)
        img = self._resize_with_crop(img, (1280, 720))
        
        # Apply visual enhancements (CLAHE, saturation boost, sharpening)
        img = self._enhance_image(img)
        
        # Add text overlay with professional styling
        img = self._add_professional_text(img, text)
        
        # Save with high quality
        img.save(output_path, 'JPEG', quality=95)
        return output_path
```

---

# 4. SUBTITLES MODULE

## 4.1 Overview
The subtitles module uses **OpenAI Whisper** for automatic speech recognition (ASR):
- Supports **16+ languages** including Urdu, Arabic, Hindi
- Multiple subtitle styles: clean, casual, formal, creative
- Export formats: SRT, JSON
- Real-time subtitle preview

## 4.2 Whisper Integration
```python
def _generate_subtitles(self, video, options):
    """Enhanced subtitle generation with language support"""
    language = options.get('subtitle_language', 'en')
    style = options.get('subtitle_style', 'clean')
    
    # Extract audio from video
    clip = VideoFileClip(video.filepath)
    audio_path = f"{os.path.splitext(video.filepath)[0]}_audio.wav"
    clip.audio.write_audiofile(audio_path)
    
    # Use Whisper for transcription
    import whisper
    
    # Select optimal model based on language
    model_size = self._get_optimal_whisper_model(language)
    # For Urdu: "large-v3", For English: "medium"
    
    model = whisper.load_model(model_size)
    
    # Preprocess audio for better recognition
    processed_audio = self._preprocess_audio_for_transcription(audio_path, language)
    
    # Get transcription options optimized for language
    transcription_options = self._get_transcription_options(language)
    
    # Transcribe
    result = model.transcribe(
        processed_audio,
        language=self._get_whisper_language_code(language),
        **transcription_options
    )
    
    # Extract segments with timestamps
    segments = []
    for segment in result['segments']:
        text = self._post_process_transcription(segment['text'], language)
        segments.append({
            'start': segment['start'],
            'end': segment['end'],
            'text': text,
            'confidence': segment.get('avg_logprob', 0.0)
        })
    
    # Generate SRT and JSON formats
    srt_content, json_data = self._create_subtitles_from_segments(segments, language, style)
    
    # Save files
    srt_path = f"{os.path.splitext(video.filepath)[0]}_{language}.srt"
    json_path = f"{os.path.splitext(video.filepath)[0]}_{language}.json"
    
    video.outputs["subtitles"] = {
        "srt": srt_path,
        "json": json_path,
        "language": language,
        "style": style
    }
```

## 4.3 Language-Specific Optimization
```python
def _get_optimal_whisper_model(self, language):
    """Get optimal Whisper model size based on language"""
    if language in ['ur', 'ru-ur']:  # Urdu
        return "large-v3"  # Best model for Urdu
    elif language in ['ar', 'hi', 'zh', 'ja', 'ko']:  # Complex scripts
        return "large"
    elif language in ['en', 'es', 'fr', 'de']:  # Well-supported
        return "medium"
    else:
        return "base"

def _get_transcription_options(self, language):
    """Get optimal transcription options for each language"""
    base_options = {
        "word_timestamps": True,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0
    }
    
    if language in ['ur', 'ru-ur']:  # Urdu-specific
        return {
            **base_options,
            "temperature": (0.0, 0.2, 0.4, 0.6, 0.8),
            "compression_ratio_threshold": 2.4,
            "condition_on_previous_text": True,
            "initial_prompt": "یہ ایک اردو زبان کی ویڈیو ہے۔",
            "beam_size": 5,
            "best_of": 5
        }
    return base_options
```

## 4.4 Supported Languages
| Code | Language | Flag | Model Size |
|------|----------|------|------------|
| `en` | English | 🇺🇸 | medium |
| `ur` | Urdu | 🇵🇰 | large-v3 |
| `ru-ur` | Roman Urdu | 🇵🇰 | large-v3 |
| `ar` | Arabic | 🇸🇦 | large |
| `hi` | Hindi | 🇮🇳 | large |
| `es` | Spanish | 🇪🇸 | medium |
| `fr` | French | 🇫🇷 | medium |
| `de` | German | 🇩🇪 | medium |
| `zh` | Chinese | 🇨🇳 | large |
| `ja` | Japanese | 🇯🇵 | large |
| `ko` | Korean | 🇰🇷 | large |

---

# 5. REACT FRONTEND

## 5.1 Project Structure
```
src/
├── App.tsx              # Main app with routing
├── main.tsx             # Entry point
├── index.css            # Global styles (Tailwind)
├── components/
│   ├── VideoEditor.tsx      # Main video editor
│   ├── SubtitleEditor.tsx   # Subtitle management
│   ├── ThumbnailGenerator.tsx # Thumbnail preview
│   ├── VideoPlayer.tsx      # Video playback
│   ├── Navbar.tsx           # Navigation
│   ├── LiveChat.tsx         # Chat support
│   └── AuthCallback.tsx     # OAuth callback
├── contexts/
│   └── AuthContext.tsx      # Authentication state
├── pages/
│   ├── Home.tsx             # Landing page
│   ├── Editor.tsx           # Editor page
│   ├── Login.tsx / Signup.tsx
│   ├── Profile.tsx          # User profile
│   └── Admin.tsx            # Admin dashboard
└── services/
    └── api.ts               # API service class
```

## 5.2 Authentication Context
```typescript
// src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ApiService } from '../services/api';

interface User {
  email: string;
  firstName?: string;
  lastName?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginAsDemo: () => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check for existing token on mount
    const token = ApiService.getToken();
    if (token) {
      setUser({ email: 'demo@snipx.com', firstName: 'Demo', lastName: 'User' });
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await ApiService.login(email, password);
    setUser(response.user);
  };

  const logout = () => {
    ApiService.clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, ... }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
```

## 5.3 API Service Class
```typescript
// src/services/api.ts
import { z } from 'zod';

const API_URL = 'http://localhost:5001/api';

// Validation schemas using Zod
const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

export class ApiService {
  private static token: string | null = null;

  static setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  static getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  static clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  private static async request(endpoint: string, options: RequestInit = {}) {
    const token = this.getToken();
    const isForm = options.body instanceof FormData;

    const headers: HeadersInit = {
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    };

    const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });

    if (!res.ok) {
      const payload = await res.json();
      throw new Error(payload.message || payload.error || `HTTP ${res.status}`);
    }

    return res.json();
  }

  static async login(email: string, password: string) {
    const validated = loginSchema.parse({ email, password });
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(validated)
    });
    this.setToken(data.token);
    return data;
  }

  static async uploadVideo(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('video', file);
    
    return this.request('/upload', {
      method: 'POST',
      body: formData
    });
  }

  static async processVideo(videoId: string, options: ProcessingOptions) {
    return this.request(`/videos/${videoId}/process`, {
      method: 'POST',
      body: JSON.stringify({ options })
    });
  }

  static async getVideoSubtitles(videoId: string): Promise<SubtitleData[]> {
    const response = await this.request(`/videos/${videoId}/subtitles`);
    return response?.segments || [];
  }
}
```

## 5.4 Video Editor Component
```typescript
// src/components/VideoEditor.tsx (key parts)
const VideoEditor = () => {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);

  const uploadFile = async (file: File) => {
    const response = await ApiService.uploadVideo(file);
    setVideoId(response.video_id);
    toast.success('Video uploaded successfully!');
  };

  const handleProcessVideo = async () => {
    if (!videoId) return;

    setIsProcessing(true);
    try {
      const options = {
        generate_subtitles: true,
        subtitle_language: 'en',
        cut_silence: true,
        enhance_audio: true,
        generate_thumbnail: true
      };

      await ApiService.processVideo(videoId, options);
      
      // Get processed video data
      const videoData = await ApiService.getVideo(videoId);
      
      // Load thumbnail if available
      if (videoData.outputs?.thumbnail) {
        setThumbnailUrl(ApiService.getVideoThumbnailUrl(videoId));
      }
      
      toast.success('Video processed successfully!');
    } catch (error) {
      toast.error('Processing failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div>
      {/* Upload Section */}
      <input type="file" accept="video/*" onChange={handleFileChange} />
      
      {/* Process Button */}
      <button onClick={handleProcessVideo} disabled={isProcessing}>
        {isProcessing ? 'Processing...' : 'Process Video'}
      </button>
      
      {/* Thumbnail Preview */}
      {thumbnailUrl && <ThumbnailGenerator thumbnailUrl={thumbnailUrl} />}
      
      {/* Subtitle Editor */}
      {videoId && <SubtitleEditor videoId={videoId} />}
    </div>
  );
};
```

## 5.5 App Routing
```typescript
// src/App.tsx
function App() {
  const { isAuthenticated } = useAuth();
  
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/editor" />} />
        <Route path="/signup" element={!isAuthenticated ? <Signup /> : <Navigate to="/editor" />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        
        {/* Protected Routes */}
        <Route path="/" element={<Home />} />
        <Route path="/editor" element={<Editor />} />
        <Route path="/profile" element={isAuthenticated ? <Profile /> : <Navigate to="/login" />} />
        <Route path="/admin" element={isAuthenticated ? <Admin /> : <Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}
```

---

# 6. FLASK BACKEND

## 6.1 Project Structure
```
backend/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── utils.py               # Utility functions
├── video_processor.py     # Basic video processor
├── models/
│   ├── user.py            # User model
│   ├── video.py           # Video model
│   └── support_ticket.py  # Support ticket model
├── services/
│   ├── auth_service.py    # Authentication logic
│   ├── video_service.py   # Video processing logic (2200+ lines)
│   └── support_service.py # Support ticket logic
└── uploads/               # Uploaded files
```

## 6.2 Main Application Setup
```python
# backend/app.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# MongoDB Connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.snipx
print("✅ Connected to MongoDB")

# Initialize Services
auth_service = AuthService(db)
video_service = VideoService(db)
support_service = SupportService(db)

# OAuth Setup (Google)
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    client_kwargs={'scope': 'openid email profile'}
)
```

## 6.3 Authentication Decorator
```python
def require_auth(f):
    """Decorator to require JWT authentication"""
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        try:
            token = auth_header.split(' ')[1]
            user_id = auth_service.verify_token(token)
            return f(user_id, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401

    decorated.__name__ = f.__name__
    return decorated
```

## 6.4 Authentication Service
```python
# backend/services/auth_service.py
import jwt
import bcrypt
from datetime import datetime, timedelta
from bson.objectid import ObjectId

class AuthService:
    def __init__(self, db):
        self.db = db
        self.users = db.users
        self.secret_key = os.getenv('JWT_SECRET_KEY')

    def register_user(self, email, password, first_name=None, last_name=None):
        if self.users.find_one({"email": email}):
            raise ValueError("Email already registered")

        # Hash password with bcrypt
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        user_doc = {
            "email": email,
            "password_hash": password_hash,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": datetime.utcnow()
        }
        result = self.users.insert_one(user_doc)
        return str(result.inserted_id)

    def login_user(self, email, password):
        user_doc = self.users.find_one({"email": email})
        if not user_doc:
            raise ValueError("Invalid email or password")

        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user_doc['password_hash']):
            raise ValueError("Invalid email or password")

        # Generate JWT
        token = self.generate_token(str(user_doc['_id']))
        
        user_data = {
            'id': str(user_doc['_id']),
            'email': user_doc['email'],
            'firstName': user_doc.get('first_name'),
            'lastName': user_doc.get('last_name')
        }

        return token, user_data

    def generate_token(self, user_id):
        payload = {
            'user_id': str(user_id),
            'exp': datetime.utcnow() + timedelta(days=1)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
```

---

# 7. MONGODB DATABASE

## 7.1 Connection Setup
```python
# Connection String (from .env)
MONGODB_URI=mongodb://localhost:27017/snipx
# OR for MongoDB Atlas:
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/snipx

# Connection in app.py
from pymongo import MongoClient

client = MongoClient(os.getenv('MONGODB_URI'))
db = client.snipx  # Database name

# Collections
users = db.users
videos = db.videos
support_tickets = db.support_tickets
```

## 7.2 Database Schema

### Users Collection
```javascript
{
  "_id": ObjectId("..."),
  "email": "user@example.com",
  "password_hash": Binary("..."),  // bcrypt hash
  "first_name": "John",
  "last_name": "Doe",
  "created_at": ISODate("2024-12-18T10:00:00Z"),
  "updated_at": ISODate("2024-12-18T10:00:00Z"),
  "videos": [],  // Array of video IDs
  "settings": {
    "default_language": "en",
    "auto_enhance_audio": false,
    "generate_thumbnails": true
  }
}
```

### Videos Collection
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),  // Reference to users
  "filename": "my_video.mp4",
  "filepath": "uploads/my_video.mp4",
  "size": 10485760,  // bytes
  "status": "completed",  // uploaded, processing, completed, failed
  "processing_options": {
    "generate_subtitles": true,
    "subtitle_language": "en",
    "enhance_audio": true,
    "generate_thumbnail": true
  },
  "upload_date": ISODate("..."),
  "process_start_time": ISODate("..."),
  "process_end_time": ISODate("..."),
  "error": null,
  "metadata": {
    "duration": 120.5,
    "format": "mp4",
    "resolution": "1920x1080",
    "fps": 30
  },
  "outputs": {
    "processed_video": "uploads/my_video_enhanced.mp4",
    "thumbnail": "uploads/my_video_thumb_1.jpg",
    "thumbnails": ["uploads/my_video_thumb_1.jpg", "..."],
    "subtitles": {
      "srt": "uploads/my_video_en.srt",
      "json": "uploads/my_video_en.json",
      "language": "en",
      "style": "clean"
    }
  }
}
```

### Support Tickets Collection
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Feature Request",
  "description": "I would like...",
  "priority": "medium",  // low, medium, high, urgent
  "type": "feature",  // bug, feature, question, other
  "status": "open",  // open, in_progress, resolved, closed
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

## 7.3 MongoDB Operations Examples
```python
# INSERT - Create new video
video_doc = {
    "user_id": ObjectId(user_id),
    "filename": filename,
    "filepath": filepath,
    "status": "uploaded",
    "upload_date": datetime.utcnow()
}
result = db.videos.insert_one(video_doc)
video_id = str(result.inserted_id)

# FIND - Get video by ID
video = db.videos.find_one({"_id": ObjectId(video_id)})

# FIND - Get all videos for user
videos = db.videos.find({"user_id": ObjectId(user_id)})

# UPDATE - Update video status
db.videos.update_one(
    {"_id": ObjectId(video_id)},
    {"$set": {
        "status": "completed",
        "outputs.thumbnail": thumbnail_path
    }}
)

# DELETE - Remove video
db.videos.delete_one({"_id": ObjectId(video_id)})

# AGGREGATE - Get user stats
pipeline = [
    {"$match": {"user_id": ObjectId(user_id)}},
    {"$group": {
        "_id": "$status",
        "count": {"$sum": 1}
    }}
]
stats = list(db.videos.aggregate(pipeline))
```

## 7.4 Data Models (Python)
```python
# backend/models/video.py
from datetime import datetime
from bson import ObjectId

class Video:
    def __init__(self, user_id, filename, filepath, size):
        self.user_id = user_id
        self.filename = filename
        self.filepath = filepath
        self.size = size
        self.status = "uploaded"
        self.processing_options = {}
        self.upload_date = datetime.utcnow()
        self.metadata = {
            "duration": None,
            "format": None,
            "resolution": None,
            "fps": None
        }
        self.outputs = {
            "processed_video": None,
            "thumbnail": None,
            "subtitles": None
        }

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "filename": self.filename,
            "filepath": self.filepath,
            "size": self.size,
            "status": self.status,
            "processing_options": self.processing_options,
            "upload_date": self.upload_date,
            "metadata": self.metadata,
            "outputs": self.outputs
        }

    @staticmethod
    def from_dict(data):
        video = Video(
            user_id=ObjectId(data["user_id"]),
            filename=data["filename"],
            filepath=data["filepath"],
            size=data["size"]
        )
        video.status = data.get("status", "uploaded")
        video.metadata = data.get("metadata", {})
        video.outputs = data.get("outputs", {})
        return video
```

---

# 8. API ENDPOINTS

## 8.1 Authentication Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login user | No |
| POST | `/api/auth/demo` | Demo login | No |
| GET | `/api/auth/me` | Get current user | Yes |
| DELETE | `/api/auth/delete-account` | Delete account | Yes |
| GET | `/api/auth/google/login` | Google OAuth login | No |
| GET | `/api/auth/google/callback` | Google OAuth callback | No |

## 8.2 Video Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/upload` | Upload video | Yes |
| GET | `/api/videos` | Get user's videos | Yes |
| GET | `/api/videos/<id>` | Get video details | Yes |
| DELETE | `/api/videos/<id>` | Delete video | Yes |
| POST | `/api/videos/<id>/process` | Process video | Yes |
| GET | `/api/videos/<id>/download` | Download processed video | Yes |
| GET | `/api/videos/<id>/status` | Get processing status | Yes |

## 8.3 Subtitle Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/videos/<id>/subtitles` | Get subtitles | Yes |
| POST | `/api/videos/<id>/subtitles/generate` | Generate subtitles | Yes |
| GET | `/api/videos/<id>/subtitles/<lang>/download` | Download subtitles | Yes |

## 8.4 Thumbnail Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/videos/<id>/thumbnail` | Get thumbnail | Yes |
| GET | `/api/videos/<id>/thumbnails` | Get all thumbnails | Yes |
| POST | `/api/videos/<id>/thumbnails/generate` | Generate thumbnails | Yes |

## 8.5 Support Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/support/tickets` | Create ticket | Yes |
| GET | `/api/support/tickets` | Get user tickets | Yes |
| GET | `/api/support/tickets/<id>` | Get ticket details | Yes |

---

# 9. KEY CODE SNIPPETS

## 9.1 Video Upload Flow
```python
@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_video(user_id):
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save and validate video
    video_id = video_service.save_video(file, user_id)

    return jsonify({
        'message': 'Video uploaded successfully',
        'video_id': str(video_id)
    }), 200
```

## 9.2 Video Processing Flow
```python
def process_video(self, video_id, options):
    video = self.get_video(video_id)
    video.status = "processing"
    video.process_start_time = datetime.utcnow()
    
    try:
        if options.get('cut_silence'):
            self._cut_silence(video)
        
        if options.get('enhance_audio'):
            self._enhance_audio(video, options)
        
        if options.get('generate_thumbnail'):
            self._generate_thumbnail(video, options)
        
        if options.get('generate_subtitles'):
            self._generate_subtitles(video, options)

        video.status = "completed"
    except Exception as e:
        video.status = "failed"
        video.error = str(e)
    finally:
        video.process_end_time = datetime.utcnow()
        self.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": video.to_dict()}
        )
```

## 9.3 Frontend Upload with Progress
```typescript
static async uploadVideo(file: File, onProgress?: (progress: number) => void) {
  const formData = new FormData();
  formData.append('video', file);
  
  if (onProgress) {
    const interval = setInterval(() => {
      onProgress(Math.min(90, Math.random() * 85 + 10));
    }, 200);
    
    try {
      const result = await this.request('/upload', {
        method: 'POST',
        body: formData
      });
      clearInterval(interval);
      onProgress(100);
      return result;
    } catch (error) {
      clearInterval(interval);
      throw error;
    }
  }
  
  return this.request('/upload', {
    method: 'POST',
    body: formData
  });
}
```

---

# 10. COMMON VIVA QUESTIONS

## 10.1 Project Understanding

**Q1: What is the main purpose of your project?**
> SnipX is an AI-powered video enhancement platform that automates video processing tasks like subtitle generation, thumbnail creation, audio enhancement, and silence removal. It helps content creators improve their videos efficiently using AI/ML technologies.

**Q2: What problem does it solve?**
> Content creators spend hours manually editing videos, creating subtitles, and designing thumbnails. SnipX automates these tasks using AI - Whisper for speech-to-text, BLIP for image understanding, and various audio processing algorithms.

**Q3: Who is the target audience?**
> YouTubers, social media content creators, educators creating video content, businesses needing video processing, and anyone who needs to enhance videos with subtitles or thumbnails.

## 10.2 Technical Questions

**Q4: Why did you choose MongoDB over SQL databases?**
> MongoDB is ideal for this project because:
> - **Schema flexibility**: Video metadata varies (duration, resolution, outputs)
> - **JSON-like documents**: Natural fit for storing processing options and outputs
> - **Scalability**: Handles large files and many users efficiently
> - **Easy integration**: PyMongo works seamlessly with Python/Flask

**Q5: Explain the authentication flow.**
> 1. User registers with email/password (bcrypt hashing)
> 2. Login generates JWT token with 24-hour expiry
> 3. Token stored in localStorage on frontend
> 4. Every API request includes token in Authorization header
> 5. Backend decorator validates token and extracts user_id
> 6. Google OAuth also supported for social login

**Q6: How does Whisper subtitle generation work?**
> 1. Extract audio from video using MoviePy
> 2. Preprocess audio (normalize, filter noise)
> 3. Select optimal Whisper model based on language
> 4. Transcribe with language-specific options (beam search, temperature)
> 5. Post-process text for each language
> 6. Generate SRT and JSON formats with timestamps

**Q7: How do you handle video processing errors?**
> We use try-except blocks throughout processing:
> - Status tracked: "uploaded" → "processing" → "completed"/"failed"
> - Errors logged with traceback
> - Error message stored in video document
> - Frontend shows appropriate error messages
> - Cleanup of temporary files in finally block

**Q8: Explain the thumbnail generation algorithm.**
> 1. Open video with OpenCV
> 2. Sample frames at intervals across video
> 3. Calculate quality score for each frame:
>    - Sharpness (Laplacian variance)
>    - Brightness (not too dark/bright)
>    - Color richness (saturation)
>    - Face detection score
>    - Composition (rule of thirds)
> 4. Select top 5 frames by quality
> 5. Generate catchy text using BLIP AI
> 6. Create professional thumbnail with text overlay

## 10.3 Architecture Questions

**Q9: Why Flask instead of Django?**
> - **Lightweight**: Perfect for API-focused applications
> - **Flexibility**: More control over project structure
> - **Easy integration**: Works well with AI/ML libraries
> - **Simpler**: Less boilerplate for REST APIs
> - **Performance**: Faster for this use case

**Q10: Why React with TypeScript?**
> - **Type safety**: Catches errors at compile time
> - **Better IDE support**: Autocomplete and refactoring
> - **Scalability**: Easier to maintain larger codebase
> - **Documentation**: Types serve as documentation
> - **Industry standard**: Common in production apps

**Q11: How do you ensure security?**
> - **Password hashing**: bcrypt with salt
> - **JWT tokens**: Signed, time-limited tokens
> - **Authorization checks**: Every endpoint verifies ownership
> - **Input validation**: Zod schemas on frontend, Python validation on backend
> - **CORS configuration**: Restricted to allowed origins
> - **File validation**: MIME type checking for uploads

## 10.4 Future Improvements

**Q12: What improvements would you make?**
> 1. **Real-time processing**: WebSocket for progress updates
> 2. **Queue system**: Celery for background processing
> 3. **Cloud storage**: AWS S3 for video files
> 4. **CDN**: Faster video delivery
> 5. **More AI features**: Video summarization, auto-captioning
> 6. **Mobile app**: React Native companion
> 7. **Batch processing**: Multiple videos at once

## 10.5 Demonstration Points
- Show video upload and processing flow
- Demonstrate subtitle generation in multiple languages
- Show AI thumbnail generation with BLIP
- Explain MongoDB document structure
- Walk through authentication flow
- Show error handling and validation

---

# 📝 QUICK REFERENCE CARD

## Key Technologies
| Component | Technology |
|-----------|------------|
| Frontend | React + TypeScript + Tailwind |
| Backend | Flask + Python |
| Database | MongoDB |
| Speech-to-Text | OpenAI Whisper |
| Image Captioning | Salesforce BLIP |
| Video Processing | MoviePy + OpenCV |
| Audio Processing | PyDub + Librosa |
| Authentication | JWT + bcrypt + OAuth |

## Important Files
- `backend/app.py` - Main Flask app (750 lines)
- `backend/services/video_service.py` - Video processing (2200+ lines)
- `backend/services/auth_service.py` - Authentication
- `src/App.tsx` - Main React app
- `src/services/api.ts` - API service class
- `src/contexts/AuthContext.tsx` - Auth state management

## Commands to Run
```bash
# Backend
cd backend
pip install -r requirements.txt
python app.py

# Frontend
npm install
npm run dev
```

## Environment Variables
```
MONGODB_URI=mongodb://localhost:27017/snipx
JWT_SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=524288000
```

---

**Good luck with your viva! 🎓**
