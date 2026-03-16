"""
Quick Start Backend - For Testing ngrok & WebSocket
Starts Flask server without heavy AI models for quick testing
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = False  # Disable debug mode
app.config['SECRET_KEY'] = 'test-secret-key'

CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Backend is running!'
    })

# Test endpoint
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({
        'message': 'Backend API is working!',
        'websocket_enabled': True,
        'timestamp': datetime.utcnow().isoformat()
    })

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    logger.info(f'✅ Client connected: {request.sid}')
    emit('connection_response', {
        'status': 'connected', 
        'message': 'WebSocket connection established!',
        'client_id': request.sid,
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'❌ Client disconnected: {request.sid}')

@socketio.on('subscribe_video_progress')
def handle_subscribe(data):
    video_id = data.get('video_id')
    logger.info(f'📡 Client {request.sid} subscribed to video {video_id} progress')
    
    # Send test progress updates
    emit('processing_progress', {
        'video_id': video_id,
        'step': 'started',
        'progress': 10,
        'message': '🚀 Processing started (TEST MODE)',
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('test_message')
def handle_test_message(data):
    logger.info(f'📨 Received test message: {data}')
    emit('test_response', {
        'message': 'Message received!',
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    })

# Test progress endpoint (simulates video processing)
@app.route('/api/test-progress/<video_id>', methods=['POST'])
def test_progress(video_id):
    """Send test progress updates via WebSocket"""
    
    # Emit progress updates
    socketio.emit('processing_progress', {
        'video_id': video_id,
        'step': 'extracting_audio',
        'progress': 25,
        'message': '🎵 Extracting audio (TEST)',
        'timestamp': datetime.utcnow().isoformat()
    })
    
    socketio.emit('processing_progress', {
        'video_id': video_id,
        'step': 'generating_subtitles',
        'progress': 50,
        'message': '📝 Generating subtitles (TEST)',
        'timestamp': datetime.utcnow().isoformat()
    })
    
    socketio.emit('processing_progress', {
        'video_id': video_id,
        'step': 'completed',
        'progress': 100,
        'message': '✅ Processing complete (TEST)',
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return jsonify({
        'message': 'Test progress updates sent via WebSocket',
        'video_id': video_id
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 QUICK START BACKEND - TEST MODE")
    print("="*60)
    print("✅ Flask server starting...")
    print("✅ WebSocket (Socket.IO) enabled")
    print("✅ CORS enabled for all origins")
    print("\n📍 Server URL: http://0.0.0.0:5001")
    print("📍 API Endpoints:")
    print("   - GET  /api/health")
    print("   - GET  /api/test")
    print("   - POST /api/test-progress/<video_id>")
    print("\n📡 WebSocket Events:")
    print("   - connect")
    print("   - disconnect")
    print("   - subscribe_video_progress")
    print("   - test_message")
    print("="*60 + "\n")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5001, use_reloader=False)
