"""
Fast Start Backend - Full API without heavy AI models
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv
import logging
import os
import bcrypt
import jwt

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = False
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 500 * 1024 * 1024))

# Enhanced CORS configuration
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)

# MongoDB connection
try:
    client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client['snipx']
    users = db['users']
    videos = db['videos']
    logger.info("[OK] Connected to MongoDB")
except Exception as e:
    logger.warning(f"⚠️ MongoDB not available: {e}")
    db = None
    users = None
    videos = None

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Full backend is running!',
        'mongodb': 'connected' if db is not None else 'not connected'
    })

# Auth endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if users is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if user exists
        if users.find_one({'email': email}):
            return jsonify({'error': 'User already exists'}), 400
        
        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user = {
            'email': email,
            'password': hashed,
            'name': name,
            'created_at': datetime.utcnow(),
            'is_verified': True  # Auto-verify for development
        }
        
        result = users.insert_one(user)
        
        # Generate token
        token = jwt.encode(
            {'user_id': str(result.inserted_id), 'email': email},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return jsonify({
            'token': token,
            'user': {
                'id': str(result.inserted_id),
                'email': email,
                'name': name
            }
        })
        
    except Exception as e:
        logger.error(f"Register error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if users is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Find user
        user = users.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        token = jwt.encode(
            {'user_id': str(user['_id']), 'email': email},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return jsonify({
            'token': token,
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user.get('name', '')
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['user_id']
        
        if users is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get user
        user = users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'id': str(user['_id']),
            'email': user['email'],
            'name': user.get('name', '')
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': str(e)}), 500

# Video endpoints
@app.route('/api/upload', methods=['POST'])
def upload_video():
    try:
        # Get auth token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        logger.info(f"File saved: {filepath}")
        
        # Create video record
        if videos is not None:
            video_doc = {
                'user_id': user_id,
                'filename': filename,
                'original_filename': file.filename,
                'filepath': filepath,
                'status': 'uploaded',
                'created_at': datetime.now(),
                'file_size': os.path.getsize(filepath)
            }
            result = videos.insert_one(video_doc)
            video_id = str(result.inserted_id)
        else:
            # Fallback without database
            video_id = filename
        
        return jsonify({
            'video_id': video_id,
            'filename': filename,
            'message': 'Video uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos', methods=['GET'])
def get_videos():
    try:
        # Get auth token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        if videos is None:
            return jsonify({'videos': []})
        
        # Get user's videos
        user_videos = list(videos.find({'user_id': user_id}).sort('created_at', -1))
        
        # Convert ObjectId to string
        for video in user_videos:
            video['_id'] = str(video['_id'])
            if 'created_at' in video:
                video['created_at'] = video['created_at'].isoformat()
        
        return jsonify({'videos': user_videos})
        
    except Exception as e:
        logger.error(f"Get videos error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>', methods=['GET'])
def get_video(video_id):
    try:
        # Get auth token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        if videos is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get video
        video = videos.find_one({'_id': ObjectId(video_id), 'user_id': user_id})
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Convert ObjectId to string
        video['_id'] = str(video['_id'])
        if 'created_at' in video:
            video['created_at'] = video['created_at'].isoformat()
        
        return jsonify(video)
        
    except Exception as e:
        logger.error(f"Get video error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/process', methods=['POST'])
def process_video(video_id):
    try:
        # Get auth token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get processing options - frontend may send wrapped in 'options' key
        body = request.get_json() or {}
        if 'options' in body:
            options = body['options']
        else:
            options = body
        
        logger.info(f"Processing video {video_id} with options: {options}")
        
        # Update video status
        if videos is not None:
            videos.update_one(
                {'_id': ObjectId(video_id), 'user_id': user_id},
                {'$set': {'status': 'processing'}}
            )
        
        # Emit progress via WebSocket
        socketio.emit('video_progress', {
            'video_id': video_id,
            'progress': 10,
            'status': 'Processing started...'
        })
        
        # Run heavy AI processing in a background thread so this request returns immediately
        import threading
        def _run_processing():
            try:
                from services.video_service import VideoService
                svc = VideoService(db, socketio)
                svc.process_video(video_id, options)
                logger.info(f"[PROCESS] Background processing completed for {video_id}")
            except Exception as ex:
                logger.error(f"[PROCESS] Background processing error: {ex}")
                import traceback; traceback.print_exc()
                if videos is not None:
                    videos.update_one(
                        {'_id': ObjectId(video_id)},
                        {'$set': {'status': 'failed', 'error': str(ex)}}
                    )
        
        t = threading.Thread(target=_run_processing, daemon=True)
        t.start()
        
        return jsonify({
            'message': 'Processing started',
            'video_id': video_id
        })
        
    except Exception as e:
        logger.error(f"Process video error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/subtitles', methods=['GET'])
def get_video_subtitles(video_id):
    """Get subtitle data (JSON segments) for a video"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401

        if videos is None:
            return jsonify([]), 200

        video = videos.find_one({'_id': ObjectId(video_id)})
        if not video:
            return jsonify({'error': 'Video not found'}), 404

        subtitles_info = video.get('outputs', {}).get('subtitles', {})
        if not subtitles_info:
            return jsonify([]), 200

        json_path = subtitles_info.get('json') if isinstance(subtitles_info, dict) else None
        if not json_path or not os.path.exists(json_path):
            return jsonify([]), 200

        import json as _json
        with open(json_path, 'r', encoding='utf-8') as f:
            subtitle_data = _json.load(f)

        return jsonify(subtitle_data.get('segments', [])), 200

    except Exception as e:
        logger.error(f"Get subtitles error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/videos/<video_id>/thumbnail', methods=['GET'])
def get_video_thumbnail(video_id):
    """Serve a thumbnail image (used by <img> tags with ?token=... query param)"""
    try:
        from flask import send_file
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No authorization provided'}), 401
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401

        if videos is None:
            return jsonify({'error': 'Database not available'}), 500

        video = videos.find_one({'_id': ObjectId(video_id)})
        if not video:
            return jsonify({'error': 'Video not found'}), 404

        thumbnail_index = request.args.get('index', type=int)
        outputs = video.get('outputs', {})

        if thumbnail_index is not None:
            thumbs = outputs.get('thumbnails', [])
            if 0 <= thumbnail_index < len(thumbs):
                thumbnail_path = thumbs[thumbnail_index]
            else:
                return jsonify({'error': 'Thumbnail index out of range'}), 404
        else:
            thumbnail_path = outputs.get('thumbnail') or (outputs.get('thumbnails') or [None])[0]

        if not thumbnail_path or not os.path.exists(thumbnail_path):
            logger.error(f"[THUMBNAIL] outputs={outputs}, path={thumbnail_path}")
            return jsonify({'error': 'Thumbnail not found'}), 404

        return send_file(thumbnail_path, mimetype='image/jpeg', as_attachment=False)

    except Exception as e:
        logger.error(f"Get thumbnail error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/videos/<video_id>/thumbnail/download', methods=['GET'])
def download_video_thumbnail(video_id):
    """Download thumbnail as attachment"""
    try:
        from flask import send_file
        from PIL import Image
        from io import BytesIO

        token = request.headers.get('Authorization', '').replace('Bearer ', '') or request.args.get('token', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401

        if videos is None:
            return jsonify({'error': 'Database not available'}), 500

        video = videos.find_one({'_id': ObjectId(video_id)})
        if not video:
            return jsonify({'error': 'Video not found'}), 404

        outputs = video.get('outputs', {})
        thumbnail_path = outputs.get('thumbnail') or (outputs.get('thumbnails') or [None])[0]

        if not thumbnail_path or not os.path.exists(thumbnail_path):
            return jsonify({'error': 'Thumbnail not found'}), 404

        with Image.open(thumbnail_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=100)
            buf.seek(0)

        base_name = os.path.splitext(video.get('filename', 'thumbnail'))[0]
        response = send_file(buf, mimetype='image/jpeg', as_attachment=True,
                             download_name=f"{base_name}_thumbnail.jpg", max_age=0)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    except Exception as e:
        logger.error(f"Download thumbnail error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/videos/<video_id>/download/<file_type>', methods=['GET'])
def download_video_file(video_id, file_type):
    """Download processed video files (summarized video, subtitles, etc.)"""
    try:
        from flask import send_file
        
        # Get auth token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        if videos is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get video (filter by _id only — user_id format may differ after VideoService saves)
        video = videos.find_one({'_id': ObjectId(video_id)})
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Get the file path based on type
        file_path = None
        filename = None
        
        if file_type == 'summarized':
            file_path = video.get('outputs', {}).get('summary', {}).get('condensed_video_path')
            filename = f"{os.path.splitext(video['filename'])[0]}_summarized.mp4"
        elif file_type == 'summary_text':
            file_path = video.get('outputs', {}).get('summary_text_path')
            filename = f"{os.path.splitext(video['filename'])[0]}_summary.txt"
        elif file_type == 'subtitles':
            file_path = video.get('outputs', {}).get('subtitles_path')
            filename = f"{os.path.splitext(video['filename'])[0]}_subtitles.srt"
        elif file_type == 'thumbnail':
            file_path = video.get('outputs', {}).get('thumbnail_path')
            filename = f"{os.path.splitext(video['filename'])[0]}_thumbnail.png"
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': f'{file_type} not found or not yet generated'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/summary', methods=['GET'])
def get_video_summary(video_id):
    """Get video summary data including segments and statistics"""
    try:
        # Get auth token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Decode token
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        if videos is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get video
        video = videos.find_one({'_id': ObjectId(video_id), 'user_id': user_id})
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        summary_data = video.get('outputs', {}).get('summary', {})
        
        if not summary_data:
            return jsonify({'error': 'Summary not yet generated'}), 404
        
        return jsonify({
            'summary': summary_data,
            'video_id': video_id,
            'filename': video.get('filename')
        })
        
    except Exception as e:
        logger.error(f"Get summary error: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket handlers
@socketio.on('connect')
def handle_connect():
    logger.info(f'[+] Client connected: {request.sid}')
    emit('connection_response', {
        'status': 'connected',
        'message': 'WebSocket connection established!',
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'[-] Client disconnected: {request.sid}')

@socketio.on('subscribe_video_progress')
def handle_subscribe(data):
    video_id = data.get('video_id')
    logger.info(f'[WS] Client {request.sid} subscribed to video {video_id}')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("FAST START BACKEND - FULL API")
    print("="*60)
    print("[OK] Flask server starting...")
    print("[OK] WebSocket (Socket.IO) enabled")
    print("[OK] CORS enabled for all origins")
    print("[OK] Auth endpoints available")
    print(f"[OK] MongoDB: {'Connected' if db is not None else 'Not connected (will use fallback)'}")
    print("\n[*] Server URL: http://0.0.0.0:5001")
    print("[*] API Endpoints:")
    print("   - GET  /api/health")
    print("   - POST /api/auth/register")
    print("   - POST /api/auth/login")
    print("   - GET  /api/auth/me")
    print("   - POST /api/upload")
    print("   - GET  /api/videos")
    print("   - GET  /api/videos/<video_id>")
    print("   - POST /api/videos/<video_id>/process")
    print("   - GET  /api/videos/<video_id>/summary")
    print("   - GET  /api/videos/<video_id>/download/<file_type>")
    print("\n[*] WebSocket Events:")
    print("   - connect")
    print("   - disconnect")
    print("   - subscribe_video_progress")
    print("="*60 + "\n")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5001, use_reloader=False)
