# Remote Backend Setup & WebSocket Implementation Guide

**Date:** December 25, 2025  
**Project:** Video Processing Application (FYP)

---

## Table of Contents
1. [What We Accomplished](#what-we-accomplished)
2. [Configuration Changes](#configuration-changes)
3. [How It Works](#how-it-works)
4. [WebSocket vs REST API](#websocket-vs-rest-api)
5. [WebSocket Implementation Guide](#websocket-implementation-guide)
6. [Troubleshooting](#troubleshooting)

---

## What We Accomplished

### Project Goal
Enable access to the backend server running on lab PC (IP: 172.30.1.60) from home laptop (IP: 192.168.1.5) on a different network.

### Solution Implemented
Used **ngrok** tunnel service to expose the local backend to the internet without requiring router access or port forwarding.

### Architecture
```
[Home Laptop]                [Internet]              [Lab PC]
React Frontend  →  HTTPS via ngrok tunnel  →  Flask Backend
(192.168.1.5)      (ngrok URL)                (172.30.1.60)
                                                     ↓
                                                 MongoDB
```

### Key Components
- **Backend Server:** Flask API running on lab PC at port 5001
- **Frontend Client:** React/Vite app running on home laptop
- **Tunnel Service:** ngrok (free tier)
- **Communication:** HTTP/HTTPS REST API
- **Database:** MongoDB (local on lab PC)

---

## Configuration Changes

### 1. Environment Variables

#### Frontend `.env` (Project Root)
**Location:** `C:\Users\JAD\Documents\FYP\.env`

**Configuration:**
```env
# Remote Access (Home → Lab PC)
VITE_API_URL=https://convulsedly-ranunculaceous-bonita.ngrok-free.dev/api

# Local Development (Same PC) - Comment out above and use:
# VITE_API_URL=http://localhost:5001/api
```

#### Backend `.env`
**Location:** `C:\Users\JAD\Documents\FYP\backend\.env`

**No changes required** - Already configured correctly with:
```env
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
JWT_SECRET_KEY=your-super-secret-jwt-key
MONGODB_URI=mongodb://localhost:27017/snipx
```

---

### 2. Code Changes

#### Modified Files:

**1. `src/services/api.ts`**
```typescript
// BEFORE:
const API_URL = 'http://localhost:5001/api';

// AFTER:
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
```
**Purpose:** Allow dynamic backend URL configuration via environment variable.

---

**2. `src/pages/Signup.tsx`**
```typescript
// BEFORE:
const response = await fetch('http://localhost:5001/api/auth/register', {
  // ...
});

// AFTER:
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
const response = await fetch(`${API_URL}/auth/register`, {
  // ...
});
```
**Purpose:** Fix hardcoded localhost URL in signup functionality.

---

**3. `src/pages/Login.tsx`**
```typescript
// BEFORE:
window.location.href = 'http://localhost:5001/api/auth/google/login';

// AFTER:
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
window.location.href = `${API_URL}/auth/google/login`;
```
**Purpose:** Fix Google OAuth redirect URL.

---

**4. `src/contexts/AuthContext.tsx`**
```typescript
// BEFORE:
fetch('http://localhost:5001/api/auth/me', {
  // ...
});

// AFTER:
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
fetch(`${API_URL}/auth/me`, {
  // ...
});
```
**Purpose:** Fix user authentication check endpoint.

---

**5. `src/components/AuthCallback.tsx`**
```typescript
// BEFORE:
fetch('http://localhost:5001/api/auth/me', {
  // ...
});

// AFTER:
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
fetch(`${API_URL}/auth/me`, {
  // ...
});
```
**Purpose:** Fix OAuth callback authentication.

---

## How It Works

### Step-by-Step Flow

#### 1. **Starting Backend on Lab PC**
```powershell
# Terminal 1: Start Flask backend
cd "C:\Users\GPU\Documents\FYP Dec 18\FYP\backend"
python app.py
# Backend runs on http://0.0.0.0:5001 (accessible from network)
```

#### 2. **Exposing Backend via ngrok**
```powershell
# Terminal 2: Start ngrok tunnel
ngrok http 5001
# ngrok provides public URL: https://convulsedly-ranunculaceous-bonita.ngrok-free.dev
```

**What ngrok does:**
- Creates secure tunnel from internet to your local port 5001
- Provides HTTPS URL that works from anywhere
- Bypasses firewall/router restrictions
- No configuration needed on router

#### 3. **Running Frontend on Home Laptop**
```powershell
# Edit .env file with ngrok URL
VITE_API_URL=https://convulsedly-ranunculaceous-bonita.ngrok-free.dev/api

# Start frontend
npm run dev
# Frontend runs on http://localhost:5173
```

#### 4. **Request Flow**
```
User Action (Home Laptop)
    ↓
Frontend makes HTTP request
    ↓
Request goes to ngrok URL (HTTPS)
    ↓
ngrok tunnel forwards to Lab PC port 5001
    ↓
Flask backend processes request
    ↓
Backend queries MongoDB
    ↓
Response sent back through ngrok
    ↓
Frontend receives response
    ↓
UI updates
```

---

## WebSocket vs REST API

### Current Implementation: REST API

#### How REST Works (Request-Response Pattern)
```
Client                          Server
  |                               |
  |------- HTTP Request --------->|
  |   (e.g., upload video)        |
  |                               | Process request
  |                               | Query database
  |<------ HTTP Response ---------|
  |   (e.g., video uploaded)      |
  |                               |
Connection closes
```

**Characteristics:**
- ✅ Simple to implement
- ✅ Stateless (each request independent)
- ✅ Works with standard HTTP
- ✅ Cacheable
- ❌ Client must ask for updates (polling)
- ❌ Not real-time
- ❌ Higher latency for frequent updates

**Use Cases:**
- Login/Logout
- Data fetching
- File uploads/downloads
- CRUD operations

---

### WebSocket: Real-Time Communication

#### How WebSocket Works (Persistent Connection)
```
Client                          Server
  |                               |
  |------- WebSocket Handshake -->|
  |<------ Connection Established-|
  |                               |
  |<====== Bidirectional ========>|
  |        Communication          |
  |                               |
  | Data can flow both ways       |
  | at any time without asking    |
  |                               |
  |<------ Server Push Update ----|
  |   (e.g., processing status)   |
  |                               |
Connection stays open
```

**Characteristics:**
- ✅ Real-time updates
- ✅ Low latency
- ✅ Bidirectional communication
- ✅ Server can push data without client asking
- ✅ Efficient for frequent updates
- ❌ More complex to implement
- ❌ Stateful (maintains connection)
- ❌ Not cacheable

**Use Cases:**
- Live chat
- Real-time notifications
- Progress bars
- Live dashboards
- Multiplayer games
- Stock tickers

---

### Comparison Table

| Feature | REST API | WebSocket |
|---------|----------|-----------|
| **Connection** | Opens/closes per request | Persistent connection |
| **Communication** | One-way (client asks) | Two-way (both can initiate) |
| **Real-time** | No (must poll) | Yes |
| **Latency** | Higher | Lower |
| **Overhead** | HTTP headers each request | Initial handshake only |
| **Complexity** | Simple | Moderate |
| **Scalability** | Easier to scale | Requires connection management |
| **Use Case** | CRUD, file operations | Live updates, notifications |

---

## WebSocket Implementation Guide

### When to Use WebSocket in Your App

**Perfect Use Cases:**
1. **Real-time Video Processing Progress**
   - Show live progress: "Extracting audio... 25%"
   - Display current processing step
   - Estimate time remaining

2. **Live Subtitle Generation**
   - Stream subtitles as they're transcribed
   - Show confidence scores in real-time

3. **Multi-user Notifications**
   - Notify when team member uploads video
   - Alert on processing completion

4. **Thumbnail Generation Status**
   - "Generating thumbnail 3/5..."
   - Show preview as thumbnails are created

---

### Backend Implementation (Flask + Socket.IO)

#### Step 1: Install Dependencies
```powershell
cd backend
pip install flask-socketio python-socketio
```

#### Step 2: Update `app.py`

```python
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connection_response', {'status': 'Connected to backend'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('subscribe_video_progress')
def handle_subscribe(data):
    """Client subscribes to updates for specific video"""
    video_id = data.get('video_id')
    print(f'Client subscribed to video {video_id}')

# Emit progress updates during video processing
def process_video_with_realtime_updates(video_id):
    """Modified video processing with WebSocket updates"""
    
    # Step 1: Extract audio
    socketio.emit('processing_progress', {
        'video_id': video_id,
        'step': 'extracting_audio',
        'progress': 20,
        'message': 'Extracting audio from video...'
    })
    # ... actual audio extraction code ...
    
    # Step 2: Generate subtitles
    socketio.emit('processing_progress', {
        'video_id': video_id,
        'step': 'generating_subtitles',
        'progress': 50,
        'message': 'Generating subtitles with Whisper...'
    })
    # ... actual subtitle generation ...
    
    # Step 3: Create thumbnails
    socketio.emit('processing_progress', {
        'video_id': video_id,
        'step': 'creating_thumbnails',
        'progress': 75,
        'message': 'Creating video thumbnails...'
    })
    # ... actual thumbnail generation ...
    
    # Step 4: Complete
    socketio.emit('processing_complete', {
        'video_id': video_id,
        'progress': 100,
        'message': 'Processing complete!',
        'outputs': {
            'subtitles': 'path/to/subtitles.srt',
            'thumbnails': ['thumb1.jpg', 'thumb2.jpg']
        }
    })

# Update video processing endpoint
@app.route('/api/videos/<video_id>/process', methods=['POST'])
def process_video(video_id):
    # Start processing in background thread
    socketio.start_background_task(
        process_video_with_realtime_updates, 
        video_id
    )
    return jsonify({'message': 'Processing started'}), 202

# Run with socketio instead of app.run()
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
```

---

### Frontend Implementation (React + Socket.IO Client)

#### Step 1: Install Dependencies
```powershell
npm install socket.io-client
```

#### Step 2: Create WebSocket Service

**File: `src/services/websocket.ts`**
```typescript
import { io, Socket } from 'socket.io-client';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
const WS_URL = API_URL.replace('/api', ''); // Remove /api for WebSocket base URL

let socket: Socket | null = null;

export const connectWebSocket = (): Socket => {
  if (socket?.connected) {
    return socket;
  }

  socket = io(WS_URL, {
    autoConnect: true,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
  });

  socket.on('connect', () => {
    console.log('✅ WebSocket connected:', socket?.id);
  });

  socket.on('disconnect', (reason) => {
    console.log('❌ WebSocket disconnected:', reason);
  });

  socket.on('connect_error', (error) => {
    console.error('WebSocket connection error:', error);
  });

  return socket;
};

export const disconnectWebSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};

// Subscribe to video processing updates
export const subscribeToVideoProgress = (
  videoId: string,
  onProgress: (data: any) => void,
  onComplete: (data: any) => void
) => {
  if (!socket) {
    socket = connectWebSocket();
  }

  // Tell server we want updates for this video
  socket.emit('subscribe_video_progress', { video_id: videoId });

  // Listen for progress updates
  socket.on('processing_progress', (data) => {
    if (data.video_id === videoId) {
      onProgress(data);
    }
  });

  // Listen for completion
  socket.on('processing_complete', (data) => {
    if (data.video_id === videoId) {
      onComplete(data);
    }
  });
};

// Unsubscribe from updates
export const unsubscribeFromVideoProgress = () => {
  if (socket) {
    socket.off('processing_progress');
    socket.off('processing_complete');
  }
};

export { socket };
```

---

#### Step 3: Use WebSocket in Component

**File: `src/components/VideoProcessor.tsx`**
```typescript
import React, { useEffect, useState } from 'react';
import { 
  connectWebSocket, 
  subscribeToVideoProgress,
  unsubscribeFromVideoProgress,
  disconnectWebSocket 
} from '../services/websocket';

interface ProcessingStatus {
  step: string;
  progress: number;
  message: string;
}

export const VideoProcessor: React.FC<{ videoId: string }> = ({ videoId }) => {
  const [status, setStatus] = useState<ProcessingStatus>({
    step: 'idle',
    progress: 0,
    message: 'Ready to process'
  });
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    // Connect to WebSocket when component mounts
    connectWebSocket();

    // Subscribe to this video's progress
    subscribeToVideoProgress(
      videoId,
      // On progress update
      (data) => {
        setStatus({
          step: data.step,
          progress: data.progress,
          message: data.message
        });
      },
      // On completion
      (data) => {
        setStatus({
          step: 'complete',
          progress: 100,
          message: data.message
        });
        setIsComplete(true);
      }
    );

    // Cleanup on unmount
    return () => {
      unsubscribeFromVideoProgress();
      disconnectWebSocket();
    };
  }, [videoId]);

  const startProcessing = async () => {
    try {
      const response = await fetch(`${API_URL}/videos/${videoId}/process`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        setStatus({
          step: 'starting',
          progress: 5,
          message: 'Starting video processing...'
        });
      }
    } catch (error) {
      console.error('Failed to start processing:', error);
    }
  };

  return (
    <div className="video-processor">
      <h2>Video Processing</h2>
      
      {/* Progress Bar */}
      <div className="progress-container">
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${status.progress}%` }}
          />
        </div>
        <span className="progress-text">{status.progress}%</span>
      </div>

      {/* Status Message */}
      <p className="status-message">{status.message}</p>
      
      {/* Current Step */}
      <div className="processing-steps">
        <div className={status.step === 'extracting_audio' ? 'active' : ''}>
          🎵 Extract Audio
        </div>
        <div className={status.step === 'generating_subtitles' ? 'active' : ''}>
          📝 Generate Subtitles
        </div>
        <div className={status.step === 'creating_thumbnails' ? 'active' : ''}>
          🖼️ Create Thumbnails
        </div>
      </div>

      {/* Action Buttons */}
      {!isComplete && (
        <button onClick={startProcessing}>Start Processing</button>
      )}
      
      {isComplete && (
        <div className="completion-message">
          ✅ Processing Complete!
        </div>
      )}
    </div>
  );
};
```

---

#### Step 4: Add Styles

**File: `src/styles/video-processor.css`**
```css
.video-processor {
  max-width: 600px;
  margin: 20px auto;
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

.progress-container {
  margin: 20px 0;
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: #e0e0e0;
  border-radius: 15px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s ease;
  border-radius: 15px;
}

.progress-text {
  display: block;
  text-align: center;
  margin-top: 5px;
  font-weight: bold;
}

.status-message {
  text-align: center;
  color: #555;
  font-size: 14px;
  margin: 10px 0;
}

.processing-steps {
  display: flex;
  justify-content: space-around;
  margin: 20px 0;
}

.processing-steps div {
  padding: 10px;
  background: white;
  border-radius: 5px;
  opacity: 0.5;
  transition: all 0.3s;
}

.processing-steps div.active {
  opacity: 1;
  background: #4CAF50;
  color: white;
  transform: scale(1.1);
}

.completion-message {
  background: #4CAF50;
  color: white;
  padding: 15px;
  border-radius: 5px;
  text-align: center;
  font-weight: bold;
}
```

---

### WebSocket with ngrok

**Good News:** WebSocket works perfectly with ngrok! No additional configuration needed.

```powershell
# Start backend with WebSocket support
python app.py

# In another terminal, start ngrok
ngrok http 5001
```

**Frontend .env:**
```env
VITE_API_URL=https://your-ngrok-url.ngrok-free.dev/api
```

The WebSocket connection will automatically use the same ngrok URL:
- REST API: `https://your-ngrok-url.ngrok-free.dev/api`
- WebSocket: `wss://your-ngrok-url.ngrok-free.dev` (note: wss = WebSocket Secure)

---

## Troubleshooting

### Common Issues & Solutions

#### 1. **ngrok URL Changes Every Restart**

**Problem:** Free ngrok URLs are temporary and change when you restart ngrok.

**Solutions:**
- **Quick Fix:** Update `.env` with new URL each time
- **Permanent Fix:** Upgrade to ngrok paid plan ($8/month) for static domain
- **Alternative:** Use Cloudflare Tunnel (free, permanent URL)

**Cloudflare Tunnel Setup:**
```powershell
# Install
winget install Cloudflare.cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create lab-backend

# Run tunnel (permanent URL)
cloudflared tunnel --url http://localhost:5001 run lab-backend
```

---

#### 2. **Connection Refused Errors**

**Symptoms:**
```
Failed to fetch
net::ERR_CONNECTION_REFUSED
```

**Causes & Solutions:**

**A. Backend not running:**
```powershell
# Check if backend is running
# Should see: Running on http://0.0.0.0:5001
cd backend
python app.py
```

**B. Wrong URL in .env:**
```env
# Make sure VITE_API_URL is set correctly
VITE_API_URL=https://your-ngrok-url/api
```

**C. Frontend not restarted after .env change:**
```powershell
# Must restart dev server after changing .env
Ctrl+C
npm run dev
```

**D. ngrok not running:**
```powershell
# Check ngrok terminal
# Should see: Forwarding https://...
ngrok http 5001
```

---

#### 3. **401 Unauthorized Errors**

**Symptoms:**
```
POST /api/auth/login 401 UNAUTHORIZED
Error: Invalid email or password
```

**Causes & Solutions:**

**A. Account doesn't exist:**
- Click "Sign Up" instead of "Login"
- Create new account with email/password

**B. Wrong password:**
- Use "Forgot Password" feature
- Or create new account

**C. Database issue:**
```powershell
# Check MongoDB is running
sc query MongoDB

# Or use MongoDB Atlas (cloud) instead
```

---

#### 4. **CORS Errors**

**Symptoms:**
```
Access to fetch blocked by CORS policy
```

**Solution:**
Backend already configured with CORS:
```python
from flask_cors import CORS
CORS(app, supports_credentials=True)
```

If still having issues, update to allow specific origins:
```python
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
CORS(app, 
     supports_credentials=True, 
     origins=[frontend_url, 'http://localhost:5173'])
```

---

#### 5. **WebSocket Connection Fails**

**Symptoms:**
```
WebSocket connection error
WebSocket disconnected
```

**Solutions:**

**A. Check Socket.IO versions match:**
```powershell
# Backend
pip show flask-socketio python-socketio

# Frontend
npm list socket.io-client
```

**B. Verify CORS settings:**
```python
socketio = SocketIO(app, cors_allowed_origins="*")
```

**C. Check WebSocket URL:**
```typescript
// Should NOT include /api
const WS_URL = 'https://your-ngrok-url.ngrok-free.dev';
```

**D. ngrok WebSocket support:**
Free ngrok supports WebSocket by default, no changes needed!

---

#### 6. **Environment Variables Not Loading**

**Symptoms:**
```
API still connecting to localhost despite .env change
```

**Solutions:**

**A. Restart dev server:**
```powershell
Ctrl+C  # Stop server
npm run dev  # Start again
```

**B. Clear browser cache:**
- Press `Ctrl+Shift+R` (hard refresh)
- Or clear cache in browser settings

**C. Check .env file location:**
```
Should be in project root:
C:\Users\JAD\Documents\FYP\.env
NOT in src/ or backend/
```

**D. Verify environment variable name:**
```env
# Must be exactly this (with VITE_ prefix):
VITE_API_URL=https://...

# NOT:
API_URL=...
REACT_APP_API_URL=...
```

---

### Network Debugging Commands

**Check if backend is reachable:**
```powershell
# From home laptop
curl https://your-ngrok-url.ngrok-free.dev/api/test-db

# Should return JSON response
```

**Check ngrok status:**
```
Open browser to: http://127.0.0.1:4040
Shows all requests going through ngrok
```

**Check WebSocket connection:**
```javascript
// In browser console
const socket = io('https://your-ngrok-url.ngrok-free.dev');
socket.on('connect', () => console.log('Connected!'));
```

---

## Quick Reference

### Switching Between Local and Remote

#### Local Development (Same PC)
```env
# .env
# VITE_API_URL=http://localhost:5001/api
# (commented out or removed)
```

```powershell
# Terminal 1: Backend
cd backend
python app.py

# Terminal 2: Frontend
npm run dev
```

---

#### Remote Access (Home ← Lab PC)

**On Lab PC:**
```powershell
# Terminal 1: Backend
cd backend
python app.py

# Terminal 2: ngrok
ngrok http 5001
# Copy the forwarding URL
```

**On Home Laptop:**
```env
# .env
VITE_API_URL=https://your-ngrok-url.ngrok-free.dev/api
```

```powershell
# Restart frontend
npm run dev
```

---

### Important URLs

| Service | Local | Remote (ngrok) |
|---------|-------|----------------|
| Backend API | `http://localhost:5001/api` | `https://your-url.ngrok-free.dev/api` |
| Frontend | `http://localhost:5173` | `http://localhost:5173` |
| MongoDB | `mongodb://localhost:27017` | (same, local to backend) |
| ngrok Dashboard | `http://127.0.0.1:4040` | - |

---

### Useful Commands

```powershell
# Check IP address
ipconfig

# Test backend connection
curl http://localhost:5001/api/test-db

# Check if port is in use
netstat -ano | findstr :5001

# Kill process on port
taskkill /PID <PID> /F

# Check MongoDB status
sc query MongoDB

# Update ngrok
ngrok update

# Install Python packages
pip install -r requirements.txt

# Install npm packages
npm install

# Build frontend for production
npm run build
```

---

## Summary

### What We Achieved ✅
1. **Remote Backend Access** - Access lab PC backend from home
2. **Environment Configuration** - Dynamic URL configuration via .env
3. **Code Flexibility** - Easily switch between local/remote modes
4. **Documentation** - Complete WebSocket implementation guide

### Technologies Used
- **Backend:** Flask, Python, MongoDB
- **Frontend:** React, TypeScript, Vite
- **Tunnel:** ngrok (free tier)
- **Protocol:** HTTP/HTTPS REST API
- **Future:** WebSocket for real-time features

### Key Learnings
1. **Client-Server Architecture** - Separation of frontend and backend
2. **Environment Variables** - Configuration without code changes
3. **Tunneling Services** - Expose local servers without router access
4. **REST vs WebSocket** - When to use each communication pattern

---

**Document End**

---

## Appendix: Additional Resources

### ngrok Documentation
- Official Site: https://ngrok.com
- Documentation: https://ngrok.com/docs
- Pricing: https://ngrok.com/pricing

### WebSocket Resources
- Socket.IO: https://socket.io/docs/v4/
- Flask-SocketIO: https://flask-socketio.readthedocs.io/
- WebSocket Protocol: https://datatracker.ietf.org/doc/html/rfc6455

### Alternative Tunnel Services
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Tailscale: https://tailscale.com/
- localtunnel: https://localtunnel.github.io/www/

---

*Created: December 25, 2025*  
*Author: FYP Project Team*  
*Version: 1.0*
