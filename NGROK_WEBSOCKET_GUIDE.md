# 🚀 ngrok Setup & WebSocket Testing Guide

## STEP-BY-STEP PROCESS

### ✅ STEP 1: Backend Start Karo (DONE!)

Backend ab chal raha hai on port 5001:
```
http://localhost:5001
http://10.120.168.40:5001 (Local network IP)
```

---

### 🌐 STEP 2: ngrok Start Karo

**New PowerShell Terminal kholo aur run karo:**

```powershell
ngrok http 5001
```

**Output aisa dikhega:**
```
ngrok                                                                       

Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123-xyz.ngrok-free.app -> http://localhost:5001

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Important:** Copy the `Forwarding` URL
Example: `https://abc123-xyz.ngrok-free.app`

---

### 🔧 STEP 3: Frontend .env Update Karo

**File:** `c:\Users\Acer\Downloads\FYP 28 Dec impossible\FYP\.env`

```env
# Comment out local URL:
# VITE_API_URL=http://localhost:5001/api

# Add your ngrok URL (replace with YOUR actual ngrok URL):
VITE_API_URL=https://abc123-xyz.ngrok-free.app/api
```

**⚠️ Important:** 
- Replace `abc123-xyz.ngrok-free.app` with YOUR actual ngrok URL
- Keep `/api` at the end
- Restart frontend after changing .env

---

### ▶️ STEP 4: Frontend Restart Karo

```powershell
# In FYP directory
npm run dev
```

---

## 🔍 HOW TO CHECK IF WEBSOCKET IS WORKING

### Method 1: Browser Console (BEST METHOD) 🖥️

1. **Open frontend** in browser (http://localhost:5173)
2. **Press F12** (Open Developer Tools)
3. **Go to Console tab**

**You will see:**
```javascript
Connecting to WebSocket at: https://abc123-xyz.ngrok-free.app
✅ WebSocket connected: abc123XYZ (socket ID)
Connection response: {status: 'connected', message: 'WebSocket connection established!'}
```

**If NOT working, you'll see:**
```javascript
WebSocket connection error: Error: ...
❌ WebSocket disconnected: transport error
```

---

### Method 2: Network Tab 🌐

1. **F12 → Network tab**
2. **Filter: WS** (WebSocket filter)
3. Look for connection to ngrok URL

**You should see:**
- **Name:** `socket.io/?EIO=4&transport=websocket`
- **Status:** `101 Switching Protocols` (GREEN)
- **Type:** `websocket`

**Click on it to see:**
- Messages being sent/received
- Connection status
- Frame details

---

### Method 3: Backend Logs 📋

**In backend terminal, you'll see:**

```
INFO:__main__:✅ Client connected: abc123XYZ
INFO:__main__:📡 Client abc123XYZ subscribed to video test-video-123 progress
```

**Every WebSocket event will be logged!**

---

### Method 4: ngrok Web Interface 🌍

**Open in browser:**
```
http://127.0.0.1:4040
```

**You'll see:**
- All HTTP requests
- WebSocket connections
- Request/Response details
- Real-time traffic

**Look for:**
- `/socket.io/` requests
- Status: `101 Switching Protocols`
- Upgrade: `websocket`

---

## 🧪 TESTING WEBSOCKET - Step by Step

### Test 1: Basic Connection Test

**In Browser Console:**
```javascript
// Check if socket is connected
console.log('Socket connected:', window.socket?.connected);
```

---

### Test 2: Manual WebSocket Test

**Create a test HTML file:** `websocket-test.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
</head>
<body>
    <h1>WebSocket Test</h1>
    <div id="status">Connecting...</div>
    <button onclick="testMessage()">Send Test Message</button>
    <button onclick="testProgress()">Test Video Progress</button>
    <div id="messages"></div>

    <script>
        // Replace with YOUR ngrok URL
        const WS_URL = 'https://abc123-xyz.ngrok-free.app';
        
        const socket = io(WS_URL);
        
        socket.on('connect', () => {
            document.getElementById('status').innerHTML = '✅ Connected! ID: ' + socket.id;
            console.log('✅ WebSocket connected:', socket.id);
        });
        
        socket.on('disconnect', () => {
            document.getElementById('status').innerHTML = '❌ Disconnected';
            console.log('❌ WebSocket disconnected');
        });
        
        socket.on('connection_response', (data) => {
            console.log('Connection response:', data);
            addMessage('📨 Connection response: ' + JSON.stringify(data));
        });
        
        socket.on('processing_progress', (data) => {
            console.log('📊 Progress:', data);
            addMessage('📊 Progress: ' + data.progress + '% - ' + data.message);
        });
        
        socket.on('test_response', (data) => {
            console.log('📩 Test response:', data);
            addMessage('📩 Response: ' + JSON.stringify(data));
        });
        
        function testMessage() {
            socket.emit('test_message', { 
                message: 'Hello from browser!',
                timestamp: new Date().toISOString()
            });
            addMessage('📤 Sent test message');
        }
        
        function testProgress() {
            socket.emit('subscribe_video_progress', { 
                video_id: 'test-video-123' 
            });
            addMessage('📤 Subscribed to test video progress');
        }
        
        function addMessage(msg) {
            const div = document.createElement('div');
            div.textContent = msg;
            document.getElementById('messages').appendChild(div);
        }
    </script>
</body>
</html>
```

**Open this file in browser and click buttons to test!**

---

### Test 3: Using curl to Test Backend

```powershell
# Test health endpoint
curl https://abc123-xyz.ngrok-free.app/api/health

# Test progress endpoint (triggers WebSocket)
curl -X POST https://abc123-xyz.ngrok-free.app/api/test-progress/my-video-123
```

---

## ✅ WebSocket WORKING Signs

### In Browser Console:
```
✅ WebSocket connected: abc123XYZ
Connection response: {status: "connected", ...}
📡 Subscribed to video test-123 progress
📊 Progress: 25% - Extracting audio
📊 Progress: 50% - Generating subtitles
📊 Progress: 100% - Complete
```

### In Backend Terminal:
```
INFO:__main__:✅ Client connected: abc123XYZ
INFO:__main__:📡 Client abc123XYZ subscribed to video test-123
```

### In ngrok Dashboard (http://127.0.0.1:4040):
```
GET /socket.io/?EIO=4&transport=polling - 200
GET /socket.io/?EIO=4&transport=websocket - 101
```

---

## ❌ Common Issues & Solutions

### Issue 1: ngrok URL changes
**Problem:** Every time you restart ngrok, URL changes

**Solution:**
- Get paid ngrok account ($8/month) for static domain
- Or update .env every time
- Or use Cloudflare Tunnel (free, permanent URL)

---

### Issue 2: WebSocket not connecting
**Check:**
1. Is backend running? (`curl http://localhost:5001/api/health`)
2. Is ngrok running? (`http://127.0.0.1:4040`)
3. Is .env updated correctly?
4. Did you restart frontend after changing .env?
5. Check browser console for errors

---

### Issue 3: "ngrok-skip-browser-warning" header
**Solution:** Already handled in backend CORS config!

---

## 📊 SUMMARY - How to Know WebSocket is Working

### 1. **Backend Logs** ✅
```
INFO:__main__:✅ Client connected: XYZ123
```

### 2. **Browser Console** ✅
```javascript
✅ WebSocket connected: XYZ123
```

### 3. **Network Tab** ✅
- WS filter shows active connection
- Status: 101 Switching Protocols

### 4. **ngrok Dashboard** ✅
```
http://127.0.0.1:4040
Shows WebSocket upgrade requests
```

### 5. **Functional Test** ✅
- Upload video
- See real-time progress bar
- Progress updates without page refresh

---

## 🎯 Quick Checklist

- [ ] Backend running on port 5001
- [ ] ngrok running and showing forwarding URL
- [ ] .env updated with ngrok URL
- [ ] Frontend restarted
- [ ] Browser console shows "WebSocket connected"
- [ ] Backend logs show "Client connected"
- [ ] ngrok dashboard shows WebSocket traffic

**All green? WebSocket is working! 🎉**
