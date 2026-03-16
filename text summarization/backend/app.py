from flask import Flask, request, jsonify, redirect, url_for, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
from authlib.integrations.flask_client import OAuth
from datetime import datetime
from dotenv import load_dotenv
import logging
import os
from bson import ObjectId

# Fix Whisper Triton import error on Windows/GPU
os.environ['WHISPER_NO_TRITON'] = '1'

from services.auth_service import AuthService
from services.video_service import VideoService
from services.support_service import SupportService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enhanced CORS configuration to handle ngrok and cross-origin requests
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# App secret
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 500 * 1024 * 1024))

# MongoDB connection with fallback to Atlas
def connect_mongodb():
    """Try local MongoDB first, fallback to MongoDB Atlas if local fails"""
    local_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    atlas_uri = os.getenv('MONGODB_ATLAS_URI')
    
    # Try local MongoDB first
    try:
        client = MongoClient(local_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        logger.info("✅ Connected to local MongoDB")
        return client
    except Exception as e:
        logger.warning(f"⚠️ Local MongoDB connection failed: {str(e)}")
    
    # Fallback to MongoDB Atlas
    if atlas_uri:
        try:
            client = MongoClient(atlas_uri, serverSelectionTimeoutMS=10000)
            client.server_info()
            logger.info("✅ Connected to MongoDB Atlas (cloud)")
            return client
        except Exception as e:
            logger.error(f"❌ MongoDB Atlas connection failed: {str(e)}")
    else:
        logger.error("❌ No MONGODB_ATLAS_URI configured for fallback")
    
    raise Exception("Could not connect to any MongoDB instance")

try:
    client = connect_mongodb()
    db = client.snipx
except Exception as e:
    logger.error(f"❌ All MongoDB connections failed: {str(e)}")
    raise

# Initialize services
auth_service = AuthService(db)
video_service = VideoService(db, socketio)  # Pass socketio for real-time updates
support_service = SupportService(db)

# Import and log GPU status
from services.gpu_manager import gpu_manager, get_gpu_info

logger.info("\n" + "=" * 60)
logger.info("BACKEND SERVER GPU STATUS")
logger.info("=" * 60)
gpu_info = get_gpu_info()
if gpu_info:
    logger.info(f"✅ GPU Available: {gpu_info['name']}")
    logger.info(f"   Memory: {gpu_info['memory_total']:.2f} GB")
    logger.info(f"   CUDA: {gpu_info['cuda_version']}")
else:
    logger.info("❌ No GPU detected - Using CPU (slower)")
logger.info("=" * 60)

# OAuth setup
oauth = OAuth(app)

oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)



@app.route('/api/auth/google/login')
def google_login():
    # Use explicit redirect URI from environment or construct from request
    backend_url = os.getenv('BACKEND_URL', request.host_url.rstrip('/'))
    
    # Force HTTPS for ngrok URLs (ngrok provides HTTPS by default)
    if 'ngrok' in backend_url and backend_url.startswith('http://'):
        backend_url = backend_url.replace('http://', 'https://')
    
    redirect_uri = f"{backend_url}/api/auth/google/callback"
    logger.info(f"[OAUTH] Google login redirect URI: {redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/api/auth/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token, nonce=None)

    user = db.users.find_one({'email': user_info['email']})
    if not user:
        user_id = str(db.users.insert_one({
            'email': user_info['email'],
            'first_name': user_info.get('given_name'),
            'last_name': user_info.get('family_name'),
            'oauth_id': user_info['sub'],
            'provider': 'google',
            'created_at': datetime.utcnow()
        }).inserted_id)
    else:
        user_id = str(user['_id'])

    jwt_token = auth_service.generate_token(user_id)
    
    # Auto-detect frontend URL: check if backend is ngrok (use Netlify), else use localhost
    backend_url = request.host_url.rstrip('/')
    if 'ngrok' in backend_url:
        # Production: ngrok backend -> Netlify frontend
        frontend_url = os.getenv('FRONTEND_URL', 'https://snipxai.netlify.app')
    else:
        # Local development: localhost backend -> localhost frontend
        frontend_url = 'http://localhost:5173'
    
    logger.info(f"[OAUTH] Redirecting to frontend: {frontend_url}")
    return redirect(f"{frontend_url}/auth/callback?token={jwt_token}")



def require_auth(f):
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        logger.info(f"[AUTH] Request to {request.path}")
        logger.info(f"[AUTH] Origin: {request.headers.get('Origin')}")
        logger.info(f"[AUTH] Auth header present: {bool(auth_header)}")
        
        if not auth_header:
            logger.warning(f"[AUTH] Missing Authorization header for {request.path}")
            return jsonify({'error': 'No authorization header'}), 401

        try:
            # Extract token from "Bearer <token>" format
            token_parts = auth_header.split(' ')
            if len(token_parts) != 2 or token_parts[0] != 'Bearer':
                logger.error(f"[AUTH] Invalid Authorization header format")
                return jsonify({'error': 'Invalid authorization header format'}), 401
            
            token = token_parts[1]
            logger.info(f"[AUTH] Token length: {len(token)}")
            
            user_id = auth_service.verify_token(token)
            logger.info(f"[AUTH] ✅ Authenticated user: {user_id}")
            return f(user_id, *args, **kwargs)
        except Exception as e:
            logger.error(f"[AUTH] ❌ Token verification failed: {e}")
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 401

    decorated.__name__ = f.__name__
    return decorated

@app.route('/api/system/gpu-status', methods=['GET'])
def get_gpu_status():
    """Get current GPU status and availability"""
    try:
        from services.gpu_manager import has_gpu, get_gpu_info, gpu_manager
        
        gpu_info = get_gpu_info()
        mem_info = gpu_manager.get_gpu_memory_info() if has_gpu() else None
        
        return jsonify({
            'hasGPU': has_gpu(),
            'gpu': gpu_info,
            'memory': mem_info,
            'backends': {
                'pytorch': 'cuda' if has_gpu() else 'cpu',
                'ffmpeg_encoder': get_ffmpeg_encoder('h264'),
                'opencv_cuda': gpu_manager.opencv_cuda
            }
        }), 200
    except Exception as e:
        logger.exception("GPU status error")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-db', methods=['GET'])
def test_db():
    try:
        test_result = db.users.find_one()
        if test_result and '_id' in test_result:
            test_result['_id'] = str(test_result['_id'])

        return jsonify({
            "status": "success",
            "message": "MongoDB is connected",
            "sample_user": test_result
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "MongoDB connection failed",
            "error": str(e)
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        if not all(field in data for field in ['email', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400

        user_id = auth_service.register_user(
            email=data['email'],
            password=data['password'],
            first_name=data.get('firstName'),
            last_name=data.get('lastName')
        )
        return jsonify({'message': 'User registered successfully', 'user_id': str(user_id)}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception("Signup error")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or not all(field in data for field in ['email', 'password']):
            return jsonify({'message': 'Missing credentials'}), 400

        token, user = auth_service.login_user(data['email'], data['password'])
        return jsonify({'token': token, 'user': user}), 200
    except ValueError as e:
        return jsonify({'message': str(e)}), 401
    except Exception as e:
        logger.exception("Login error")
        return jsonify({'message': str(e)}), 500

@app.route('/api/auth/demo', methods=['POST'])
def demo_login():
    try:
        token, user = auth_service.create_demo_user()
        return jsonify({'token': token, 'user': user}), 200
    except Exception as e:
        logger.exception("Demo login error")
        return jsonify({'message': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message']
        conversation_history = data.get('history', [])
        
        # Simple fallback response for now
        response = "I'm a basic chatbot. For detailed support, please use the support ticket system in the Help section."
        
        return jsonify({
            'response': response,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("Chat error")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/support/tickets', methods=['POST'])
@require_auth
def create_support_ticket(user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['name', 'email', 'subject', 'description', 'priority', 'type']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        ticket_id = support_service.create_ticket(user_id, data)
        
        return jsonify({
            'message': 'Support ticket created successfully',
            'ticket_id': ticket_id
        }), 201
        
    except Exception as e:
        logger.exception("Support ticket creation error")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/support/tickets', methods=['GET'])
@require_auth
def get_support_tickets(user_id):
    try:
        # Get tickets for the authenticated user
        tickets = support_service.get_user_tickets(user_id)
        return jsonify(tickets), 200
    except Exception as e:
        logger.exception("Get support tickets error")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/support/tickets/<ticket_id>', methods=['GET'])
@require_auth
def get_support_ticket(user_id, ticket_id):
    try:
        ticket = support_service.get_ticket(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Ensure user owns the ticket
        if str(ticket.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized access to ticket'}), 403
            
        return jsonify(ticket.to_dict()), 200
    except Exception as e:
        logger.exception("Get support ticket error")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_video(user_id):
    try:
        # Emit upload started event
        socketio.emit('upload_progress', {
            'step': 'validation',
            'progress': 0,
            'message': 'Validating video file...',
            'timestamp': datetime.now().isoformat()
        })
        
        if 'video' not in request.files:
            socketio.emit('upload_progress', {
                'step': 'failed',
                'progress': 0,
                'message': 'No video file provided',
                'timestamp': datetime.now().isoformat()
            })
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            socketio.emit('upload_progress', {
                'step': 'failed',
                'progress': 0,
                'message': 'No selected file',
                'timestamp': datetime.now().isoformat()
            })
            return jsonify({'error': 'No selected file'}), 400

        # Emit validation complete
        socketio.emit('upload_progress', {
            'step': 'validation',
            'progress': 25,
            'message': 'Validation complete. Saving file...',
            'timestamp': datetime.now().isoformat()
        })
        
        # Emit saving progress
        socketio.emit('upload_progress', {
            'step': 'saving',
            'progress': 50,
            'message': 'Saving video to server...',
            'timestamp': datetime.now().isoformat()
        })

        video_id = video_service.save_video(file, user_id)
        
        # Emit processing metadata
        socketio.emit('upload_progress', {
            'video_id': str(video_id),
            'step': 'metadata',
            'progress': 75,
            'message': 'Extracting video metadata...',
            'timestamp': datetime.now().isoformat()
        })
        
        # Emit completion
        socketio.emit('upload_progress', {
            'video_id': str(video_id),
            'step': 'completed',
            'progress': 100,
            'message': 'Upload completed successfully!',
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({'message': 'Video uploaded successfully', 'video_id': str(video_id)}), 200
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        socketio.emit('upload_progress', {
            'step': 'failed',
            'progress': 0,
            'message': f'Upload failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/process', methods=['POST'])
@require_auth
def process_video(user_id, video_id):
    try:
        print(f"[PROCESS] ==================== RAW REQUEST ====================")
        print(f"[PROCESS] request.json: {request.json}")
        print(f"[PROCESS] =======================================================")
        
        # Frontend may send options directly OR wrapped in 'options' key
        if request.json and 'options' in request.json:
            options = request.json.get('options', {})
        else:
            options = request.json if request.json else {}
        
        logger.info(f"Processing video {video_id} with options: {options}")
        print(f"[PROCESS] ==================== VIDEO PROCESSING ====================")
        print(f"[PROCESS] Video ID: {video_id}")
        print(f"[PROCESS] Full options: {options}")
        print(f"[PROCESS] FILLER OPTIONS CHECK:")
        print(f"[PROCESS]   detect_and_remove_fillers: {options.get('detect_and_remove_fillers')}")
        print(f"[PROCESS]   detect_repeated_words: {options.get('detect_repeated_words')}")
        print(f"[PROCESS]   cut_filler_segments: {options.get('cut_filler_segments')}")
        print(f"[PROCESS]   filler_removal_level: {options.get('filler_removal_level')}")
        print(f"[PROCESS] generate_thumbnail: {options.get('generate_thumbnail', False)}")
        print(f"[PROCESS] thumbnail_text: '{options.get('thumbnail_text')}'")
        print(f"[PROCESS] thumbnail_frame_index: {options.get('thumbnail_frame_index')}")
        print(f"[PROCESS] thumbnail_font_size: {options.get('thumbnail_font_size')}")
        print(f"[PROCESS] thumbnail_text_color: {options.get('thumbnail_text_color')}")
        print(f"[PROCESS] thumbnail_outline_color: {options.get('thumbnail_outline_color')}")
        print(f"[PROCESS] thumbnail_position: {options.get('thumbnail_position')}")
        print(f"[PROCESS] thumbnail_font_style: {options.get('thumbnail_font_style')}")
        print(f"[PROCESS] thumbnail_shadow: {options.get('thumbnail_shadow')}")
        print(f"[PROCESS] thumbnail_background: {options.get('thumbnail_background')}")
        print(f"[PROCESS] thumbnail_background_color: {options.get('thumbnail_background_color')}")
        print(f"[PROCESS] ===========================================================")
        
        video_service.process_video(video_id, options)
        
        # Get updated video to check outputs
        video = video_service.get_video(video_id)
        if video:
            print(f"[PROCESS] Video outputs after processing: {video.outputs}")
            logger.info(f"Video outputs: {video.outputs}")
        
        return jsonify({'message': 'Processing completed successfully'}), 200
    except Exception as e:
        logger.error(f"Process error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>', methods=['GET'])
@require_auth
def get_video_status(user_id, video_id):
    try:
        logger.info(f"Getting video status for video_id: {video_id}, user_id: {user_id}")
        print(f"[GET_VIDEO] Fetching video {video_id}")
        
        video = video_service.get_video(video_id)
        if not video:
            logger.error(f"Video not found: {video_id}")
            print(f"[GET_VIDEO] Video not found: {video_id}")
            return jsonify({'error': 'Video not found'}), 404

        print(f"[GET_VIDEO] Found video: {video.filename}, status: {video.status}")

        # Convert custom Video object to dict
        if hasattr(video, 'to_dict'):
            video_dict = video.to_dict()
        elif hasattr(video, '__dict__'):
            video_dict = video.__dict__
        else:
            raise ValueError("Cannot serialize Video object")

        # Clean up any non-serializable fields (e.g., ObjectId)
        if '_id' in video_dict:
            video_dict['_id'] = str(video_dict['_id'])
        if 'user_id' in video_dict:
            video_dict['user_id'] = str(video_dict['user_id'])

        print(f"[GET_VIDEO] Returning video data: status={video_dict.get('status')}, outputs={video_dict.get('outputs')}")
        return jsonify(video_dict), 200

    except Exception as e:
        logger.error(f"Fetch video error: {str(e)}")
        print(f"[GET_VIDEO] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos', methods=['GET'])
@require_auth
def get_user_videos(user_id):
    try:
        print(f"[GET_VIDEOS] Fetching videos for user_id: {user_id}")
        videos = video_service.get_user_videos(user_id)
        print(f"[GET_VIDEOS] Found {len(videos)} videos")
        return jsonify(videos), 200
    except Exception as e:
        logger.error(f"List videos error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>', methods=['DELETE'])
@require_auth
def delete_video(user_id, video_id):
    try:
        video_service.delete_video(video_id, user_id)
        return jsonify({'message': 'Video deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Delete video error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Export/Render video with all edits (trim, text overlay, music)
@app.route('/api/videos/<video_id>/export', methods=['POST'])
@require_auth
def export_video(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json() or {}
        
        # Get edit parameters
        trim_start = data.get('trim_start', 0)  # Percentage 0-100
        trim_end = data.get('trim_end', 100)  # Percentage 0-100
        text_overlay = data.get('text_overlay', '')
        text_position = data.get('text_position', 'center')
        text_color = data.get('text_color', '#ffffff')
        text_size = data.get('text_size', 32)
        music_volume = data.get('music_volume', 50)
        video_volume = data.get('video_volume', 100)
        mute_original = data.get('mute_original', False)
        
        logger.info(f"Exporting video {video_id} with edits: trim={trim_start}-{trim_end}%, text='{text_overlay}'")
        
        # Process video with edits using video service
        export_path = video_service.export_video_with_edits(
            video_id=video_id,
            trim_start=trim_start,
            trim_end=trim_end,
            text_overlay=text_overlay,
            text_position=text_position,
            text_color=text_color,
            text_size=text_size,
            music_volume=music_volume,
            video_volume=video_volume,
            mute_original=mute_original
        )
        
        if not export_path or not os.path.exists(export_path):
            return jsonify({'error': 'Export failed'}), 500
        
        # Return the download URL
        return jsonify({
            'message': 'Video exported successfully',
            'download_url': f'/api/videos/{video_id}/download-export'
        }), 200
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Download exported video
@app.route('/api/videos/<video_id>/download-export', methods=['GET'])
@require_auth
def download_exported_video(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the exported video path
        export_path = video.outputs.get('exported_video', video.outputs.get('processed_video', video.filepath))
        
        if not os.path.exists(export_path):
            return jsonify({'error': 'Exported video not found'}), 404
        
        # Generate filename
        base_name = os.path.splitext(video.filename)[0]
        download_name = f"{base_name}_edited.mp4"
        
        return send_file(
            export_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=download_name,
            conditional=False
        )
    except Exception as e:
        logger.error(f"Download export error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Add download endpoint for processed videos
@app.route('/api/videos/<video_id>/download', methods=['GET'])
@require_auth
def download_video(user_id, video_id):
    from flask import Response, stream_with_context
    
    try:
        logger.info(f"[DOWNLOAD] Request for video: {video_id} by user: {user_id}")
        
        video = video_service.get_video(video_id)
        if not video:
            logger.error(f"[DOWNLOAD] Video not found: {video_id}")
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            logger.warning(f"[DOWNLOAD] Unauthorized access attempt by user {user_id}")
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the processed video path (prefer processed, fallback to original)
        processed_path = video.outputs.get('processed_video', video.filepath)
        logger.info(f"[DOWNLOAD] Video path: {processed_path}")
        logger.info(f"[DOWNLOAD] Video outputs: {video.outputs}")
        logger.info(f"[DOWNLOAD] Video filepath: {video.filepath}")
        
        # Handle None filepath
        if not processed_path:
            logger.error(f"[DOWNLOAD] Video filepath is None")
            return jsonify({'error': 'Video file path not found in database'}), 404
        
        if not os.path.exists(processed_path):
            logger.error(f"[DOWNLOAD] File not found on disk: {processed_path}")
            return jsonify({'error': 'Video file not found on server'}), 404
        
        # Check file size
        file_size = os.path.getsize(processed_path)
        logger.info(f"[DOWNLOAD] File size: {file_size / (1024*1024):.2f} MB")
        
        # Generate download filename
        base_name = os.path.splitext(video.filename)[0]
        prefix = "enhanced" if video.outputs.get('processed_video') else "original"
        download_name = f"{prefix}_{video.filename}"
        
        logger.info(f"[DOWNLOAD] Streaming file: {download_name}")
        
        # Stream file in chunks for ngrok compatibility
        def generate():
            with open(processed_path, 'rb') as f:
                chunk_size = 8192  # 8KB chunks
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(stream_with_context(generate()), mimetype='video/mp4')
        response.headers['Content-Disposition'] = f'attachment; filename="{download_name}"'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        
        logger.info(f"[DOWNLOAD] Starting stream for {download_name}")
        return response
        
    except Exception as e:
        logger.error(f"[DOWNLOAD] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/videos/<video_id>/download/original', methods=['GET'])
@require_auth
def download_original_video(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Always return the original uploaded video
        if not os.path.exists(video.filepath):
            return jsonify({'error': 'Original video not found'}), 404
        
        return send_file(
            video.filepath,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"original_{video.filename}",
            conditional=False
        )
    except Exception as e:
        logger.error(f"Download original error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/thumbnails/generate', methods=['POST'])
@require_auth
def generate_thumbnails(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json() or {}
        count = data.get('count', 5)
        style = data.get('style', 'auto')
        
        # Generate thumbnails
        video_service._generate_thumbnail(video)
        
        # Update video in database
        video_service.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": video.to_dict()}
        )
        
        return jsonify({
            'message': 'Thumbnails generated successfully',
            'thumbnails': video.outputs.get('thumbnails', []),
            'count': len(video.outputs.get('thumbnails', []))
        }), 200
        
    except Exception as e:
        logger.error(f"Generate thumbnails error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/audio/enhance', methods=['POST'])
@require_auth
def enhance_audio_realtime(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json() or {}
        enhancement_type = data.get('type', 'full')
        noise_reduction = data.get('noiseReduction', data.get('noise_reduction', True))
        volume_boost = data.get('volumeBoost', 20)
        
        # DEBUG: Log all received options
        logger.info(f"[ENHANCE AUDIO] Received options: {data}")
        
        # Enhanced audio processing options - use ALL options from frontend
        options = {
            'audio_enhancement_type': data.get('audio_enhancement_type', enhancement_type),
            'noise_reduction': noise_reduction,
            'volume_boost': volume_boost,
            'enhance_audio': True,
            'pause_threshold': data.get('pause_threshold', 500),
            'detect_and_remove_fillers': data.get('detect_and_remove_fillers', False),
            'detect_repeated_words': data.get('detect_repeated_words', False),
            'cut_filler_segments': data.get('cut_filler_segments', False),
            'filler_removal_level': data.get('filler_removal_level', 'medium')
        }
        
        logger.info(f"[ENHANCE AUDIO] Processing with options: {options}")
        
        video_service._enhance_audio(video, options)
        
        # Update video in database
        video_service.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": video.to_dict()}
        )
        
        return jsonify({
            'message': 'Audio enhanced successfully',
            'enhancement_type': enhancement_type,
            'processed_audio': video.outputs.get('processed_video')
        }), 200
        
    except Exception as e:
        logger.error(f"Audio enhancement error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/merge', methods=['POST'])
@require_auth
def merge_videos(user_id):
    """Merge multiple videos into a single video"""
    try:
        data = request.get_json()
        video_ids = data.get('video_ids', [])
        
        if not video_ids or len(video_ids) < 2:
            return jsonify({'error': 'At least 2 videos are required for merging'}), 400
        
        # Verify all videos exist and belong to user
        videos = []
        for vid_id in video_ids:
            video = video_service.get_video(vid_id)
            if not video:
                return jsonify({'error': f'Video {vid_id} not found'}), 404
            if str(video.user_id) != str(user_id):
                return jsonify({'error': 'Unauthorized'}), 403
            videos.append(video)
        
        # Merge videos using moviepy
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        logger.info(f"Merging {len(videos)} videos for user {user_id}")
        
        clips = []
        for video in videos:
            clip = VideoFileClip(video.filepath)
            clips.append(clip)
        
        # Concatenate all clips
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Generate output filename and path
        upload_folder = os.getenv('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        merged_filename = f"merged_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
        merged_path = os.path.join(upload_folder, merged_filename)
        
        logger.info(f"Writing merged video to: {merged_path}")
        
        # Write merged video
        final_clip.write_videofile(
            merged_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Get duration before closing
        merged_duration = final_clip.duration
        file_size = os.path.getsize(merged_path)
        
        # Clean up clips
        for clip in clips:
            clip.close()
        final_clip.close()
        
        # Create new video entry in database - use dict directly to avoid serialization issues
        merged_video_doc = {
            'user_id': ObjectId(user_id),
            'filename': merged_filename,
            'filepath': merged_path,
            'size': file_size,
            'status': 'completed',
            'processing_options': {},
            'upload_date': datetime.utcnow(),
            'process_start_time': None,
            'process_end_time': None,
            'error': None,
            'metadata': {
                'duration': merged_duration,
                'merged_from': video_ids,
                'format': 'mp4',
                'resolution': None,
                'fps': None
            },
            'outputs': {},
            'transcript': None
        }
        
        result = video_service.videos.insert_one(merged_video_doc)
        merged_video_id = str(result.inserted_id)
        
        logger.info(f"Videos merged successfully: {merged_video_id}")
        logger.info(f"Merged video saved - filepath: {merged_path}, exists: {os.path.exists(merged_path)}")
        
        return jsonify({
            'message': 'Videos merged successfully',
            'video_id': merged_video_id,
            'filename': merged_filename
        }), 200
        
    except Exception as e:
        logger.error(f"Merge videos error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/status', methods=['GET'])
@require_auth
def get_processing_status(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Return detailed processing status
        status_info = {
            'status': video.status,
            'progress': {
                'upload': 100 if video.status != 'uploading' else 50,
                'processing': 100 if video.status == 'completed' else (75 if video.status == 'processing' else 0),
                'thumbnails': 100 if video.outputs.get('thumbnails') else 0,
                'audio_enhancement': 100 if video.outputs.get('processed_video') else 0,
                'subtitles': 100 if video.outputs.get('subtitles') else 0
            },
            'outputs': {
                'thumbnails_count': len(video.outputs.get('thumbnails', [])),
                'has_enhanced_audio': bool(video.outputs.get('processed_video')),
                'has_subtitles': bool(video.outputs.get('subtitles')),
                'has_summary': bool(video.outputs.get('summary'))
            },
            'metadata': video.metadata,
            'processing_time': (
                (video.process_end_time - video.process_start_time).total_seconds()
                if video.process_start_time and video.process_end_time
                else None
            )
        }
        
        return jsonify(status_info), 200
        
    except Exception as e:
        logger.error(f"Get processing status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/subtitles', methods=['GET'])
@require_auth
def get_video_subtitles(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        subtitles_info = video.outputs.get('subtitles', {})
        if not subtitles_info:
            return jsonify([]), 200
        
        json_path = subtitles_info.get('json')
        if not json_path or not os.path.exists(json_path):
            return jsonify([]), 200
        
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            subtitle_data = json.load(f)
        
        return jsonify(subtitle_data.get('segments', [])), 200
        
    except Exception as e:
        logger.error(f"Get subtitles error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/summary', methods=['GET'])
@require_auth
def get_video_summary(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        summary_info = video.outputs.get('summary', '')
        if not summary_info:
            return jsonify({'error': 'No summary available', 'summary': None}), 200
        
        import json as json_lib
        
        # If summary_info is a file path
        if isinstance(summary_info, str) and os.path.exists(summary_info):
            with open(summary_info, 'r', encoding='utf-8') as f:
                summary_data = json_lib.load(f)
            return jsonify({'summary': summary_data}), 200
        
        # If summary_info is already JSON string
        if isinstance(summary_info, str):
            try:
                summary_data = json_lib.loads(summary_info)
                return jsonify({'summary': summary_data}), 200
            except json_lib.JSONDecodeError:
                return jsonify({'summary': {'text': summary_info}}), 200
        
        return jsonify({'summary': summary_info}), 200
        
    except Exception as e:
        logger.error(f"Get summary error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/subtitles/<language>/download', methods=['GET'])
@require_auth
def download_subtitles(user_id, video_id, language):

    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        format_type = request.args.get('format', 'srt')
        subtitles_info = video.outputs.get('subtitles', {})
        
        if not subtitles_info:
            return jsonify({'error': 'No subtitles found'}), 404
        
        # If it's a string (old format), try to find the file
        if isinstance(subtitles_info, str):
            subtitle_path = subtitles_info
        else:
            subtitle_path = subtitles_info.get('srt' if format_type == 'srt' else 'json')
        
        if not subtitle_path or not os.path.exists(subtitle_path):
            return jsonify({'error': 'Subtitle file not found'}), 404
        
        filename = f"{video.filename}_{language}.{format_type}"
        return send_file(
            subtitle_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Download subtitles error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/subtitles/generate', methods=['POST'])
@require_auth
def generate_subtitles(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        language = data.get('language', 'en')
        style = data.get('style', 'clean')
        
        # Generate subtitles
        options = {
            'subtitle_language': language,
            'subtitle_style': style,
            'generate_subtitles': True
        }
        
        video_service._generate_subtitles(video, options)
        
        # Update video in database
        video_service.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": video.to_dict()}
        )
        
        return jsonify({
            'message': 'Subtitles generated successfully',
            'language': language,
            'style': style
        }), 200
        
    except Exception as e:
        logger.error(f"Generate subtitles error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/dub', methods=['POST'])
@require_auth
def dub_video(user_id, video_id):
    """Dub video into another language using AI-powered speech synthesis"""
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        target_language = data.get('targetLanguage', 'en')
        source_language = data.get('sourceLanguage')  # Optional, auto-detect if not provided
        mix_original = data.get('mixOriginal', False)  # Keep original audio at low volume
        
        # Validate target language
        from services.dubbing_service import SUPPORTED_LANGUAGES
        if target_language not in SUPPORTED_LANGUAGES:
            return jsonify({
                'error': f'Unsupported language: {target_language}',
                'supported_languages': SUPPORTED_LANGUAGES
            }), 400
        
        logger.info(f"[DUB] Starting dubbing for video {video_id} to {target_language}")
        
        # Start dubbing process (async via video_service)
        result = video_service.dub_video_to_language(
            video_id=video_id,
            target_language=target_language,
            source_language=source_language,
            mix_original=mix_original,
            user_id=user_id
        )
        
        return jsonify({
            'message': 'Dubbing started',
            'videoId': video_id,
            'targetLanguage': target_language,
            'targetLanguageName': SUPPORTED_LANGUAGES[target_language],
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Dub video error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/dubbing-languages', methods=['GET'])
def get_dubbing_languages(video_id):
    """Get list of supported languages for dubbing"""
    from services.dubbing_service import SUPPORTED_LANGUAGES
    return jsonify({
        'languages': SUPPORTED_LANGUAGES
    }), 200

@app.route('/api/videos/<video_id>/detect-fillers', methods=['POST'])
@require_auth
def detect_filler_words(user_id, video_id):
    """Detect filler words in a video - uses existing transcript from auto-transcription"""
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if transcript exists (generated during upload)
        if not video.transcript:
            logger.info(f"[FILLER DETECTION] No transcript found, generating now...")
            video_service._auto_transcribe_video(video_id, video.filepath)
            video = video_service.get_video(video_id)
            
            if not video or not video.transcript:
                return jsonify({'error': 'Failed to generate transcript'}), 500
        
        transcript_data = video.transcript
        
        # Extract filler words from existing transcript
        filler_words = transcript_data.get('filler_words', [])
        repeated_words = transcript_data.get('repeated_words', [])
        
        # Combine and categorize
        all_fillers = []
        for fw in filler_words:
            all_fillers.append({
                'word': fw['word'],
                'start': fw['start'],
                'end': fw['end'],
                'type': 'filler',
                'confidence': fw.get('confidence', 0.95)
            })
        
        for rw in repeated_words:
            all_fillers.append({
                'word': rw['word'],
                'start': rw['start'],
                'end': rw['end'],
                'type': 'repeated',
                'confidence': rw.get('confidence', 0.95)
            })
        
        # Sort by timestamp
        all_fillers.sort(key=lambda x: x['start'])
        
        # Calculate stats
        total_duration = video.metadata.get('duration', 0)
        total_filler_time = sum([fw['end'] - fw['start'] for fw in all_fillers])
        
        # Get full transcript text
        transcript_text = transcript_data.get('text', '')
        
        logger.info(f"[FILLER DETECTION] Using existing transcript: {len(filler_words)} fillers, {len(repeated_words)} repeated")
        
        return jsonify({
            'filler_words': all_fillers,
            'transcript': transcript_text,
            'total_duration': total_duration,
            'total_filler_time': total_filler_time,
            'filler_count': len(filler_words),
            'repeated_count': len(repeated_words),
            'phrase_count': 0,  # Not tracked separately in current implementation
            'detection_level': 'auto'
        }), 200
        
    except Exception as e:
        logger.error(f"[FILLER DETECTION] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/transcript', methods=['GET'])
@require_auth
def get_transcript(user_id, video_id):
    """Get auto-generated transcript with filler word highlights"""
    try:
        logger.info(f"[TRANSCRIPT] Getting transcript for video: {video_id}")
        
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if transcript exists
        if not video.transcript:
            # Transcript not generated yet, try to generate now
            logger.info(f"[TRANSCRIPT] No transcript found, generating now...")
            video_service._auto_transcribe_video(video_id, video.filepath)
            
            # Re-fetch video
            video = video_service.get_video(video_id)
            if not video or not video.transcript:
                return jsonify({'error': 'Transcript not available'}), 404
        
        logger.info(f"[TRANSCRIPT] Returning transcript: {video.transcript['total_words']} words")
        return jsonify(video.transcript), 200
        
    except Exception as e:
        logger.error(f"[TRANSCRIPT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<video_id>/thumbnail', methods=['GET'])
def get_video_thumbnail(video_id):
    try:
        # Allow token from query string for img tags
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'No authorization provided'}), 401
        
        # Verify token
        try:
            user_id = auth_service.verify_token(token)
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
        
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the thumbnail index (default to primary/middle one)
        thumbnail_index = request.args.get('index', type=int)
        
        if thumbnail_index is not None:
            # Get specific thumbnail by index
            thumbnails = video.outputs.get('thumbnails', [])
            if 0 <= thumbnail_index < len(thumbnails):
                thumbnail_path = thumbnails[thumbnail_index]
            else:
                return jsonify({'error': 'Thumbnail index out of range'}), 404
        else:
            # Get primary thumbnail
            thumbnail_path = video.outputs.get('thumbnail')
        
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            return jsonify({'error': 'Thumbnail not found'}), 404
        
        print(f"[THUMBNAIL SERVE] Serving thumbnail: {thumbnail_path}")
        print(f"[THUMBNAIL SERVE] File size: {os.path.getsize(thumbnail_path)} bytes")
        
        # Verify it's a valid image before sending
        try:
            from PIL import Image
            with Image.open(thumbnail_path) as test_img:
                print(f"[THUMBNAIL SERVE] Image verified: {test_img.size}, mode: {test_img.mode}, format: {test_img.format}")
                # Ensure it's RGB
                if test_img.mode != 'RGB':
                    print(f"[THUMBNAIL SERVE] WARNING: Image is {test_img.mode}, converting to RGB")
                    rgb_img = test_img.convert('RGB')
                    rgb_img.save(thumbnail_path, 'JPEG', quality=95)
                    print(f"[THUMBNAIL SERVE] Converted and resaved as RGB JPEG")
        except Exception as verify_err:
            print(f"[THUMBNAIL SERVE] ERROR: Invalid image file: {verify_err}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Thumbnail file is corrupted'}), 500
        
        return send_file(
            thumbnail_path,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=None
        )
        
    except Exception as e:
        logger.error(f"Get thumbnail error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/thumbnail/download', methods=['GET'])
@require_auth
def download_video_thumbnail(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the thumbnail
        thumbnail_path = video.outputs.get('thumbnail')
        
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            return jsonify({'error': 'Thumbnail not found'}), 404
        
        print(f"[THUMBNAIL DOWNLOAD] Original file: {thumbnail_path}")
        
        # Create a fresh JPEG in memory using BytesIO for ngrok compatibility
        from PIL import Image
        from io import BytesIO
        
        try:
            # Open and convert to fresh JPEG in memory
            with Image.open(thumbnail_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    print(f"[THUMBNAIL DOWNLOAD] Converting from {img.mode} to RGB")
                    img = img.convert('RGB')
                
                # Save to memory buffer with maximum quality
                img_buffer = BytesIO()
                img.save(img_buffer, format='JPEG', quality=100, optimize=False, subsampling=0, progressive=False)
                img_buffer.seek(0)  # Reset to beginning for reading
                
                print(f"[THUMBNAIL DOWNLOAD] Created fresh JPEG in memory: {len(img_buffer.getvalue())} bytes")
            
            # Generate download filename
            base_name = os.path.splitext(video.filename)[0]
            download_filename = f"{base_name}_thumbnail.jpg"
            
            # Use send_file with BytesIO for proper binary streaming over ngrok
            response = send_file(
                img_buffer,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=download_filename,
                max_age=0
            )
            
            # Override headers to prevent ngrok compression/modification
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Content-Transfer-Encoding'] = 'binary'
            response.direct_passthrough = False
            
            print(f"[THUMBNAIL DOWNLOAD] Sending via send_file with BytesIO")
            return response
            
        except Exception as e:
            print(f"[THUMBNAIL DOWNLOAD] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to process thumbnail: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Download thumbnail error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/thumbnails', methods=['GET'])
@require_auth
def get_all_thumbnails(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        thumbnails = video.outputs.get('thumbnails', [])
        thumbnail_info = []
        
        for i, thumb_path in enumerate(thumbnails):
            if os.path.exists(thumb_path):
                thumbnail_info.append({
                    'index': i,
                    'url': f'/api/videos/{video_id}/thumbnail?index={i}',
                    'filename': os.path.basename(thumb_path)
                })
        
        return jsonify({
            'thumbnails': thumbnail_info,
            'primary_index': 2 if len(thumbnails) > 2 else 0,
            'count': len(thumbnail_info)
        }), 200
        
    except Exception as e:
        logger.error(f"Get thumbnails error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user(user_id):
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user['_id'] = str(user['_id'])
    user.pop('password', None)
    return jsonify(user), 200

@app.route('/api/auth/delete-account', methods=['DELETE'])
@require_auth
def delete_account(user_id):
    try:
        # Delete user account and all associated data
        auth_service.delete_user(user_id)
        
        logger.info(f"User account deleted successfully: {user_id}")
        return jsonify({
            'message': 'Account deleted successfully',
            'deleted_user_id': user_id
        }), 200
        
    except ValueError as e:
        logger.error(f"Delete account error for user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Unexpected error deleting account for user {user_id}")
        return jsonify({'error': 'Internal server error'}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    logger.info(f'Client connected: {request.sid}')
    emit('connection_response', {'status': 'connected', 'message': 'WebSocket connection established'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'Client disconnected: {request.sid}')

@socketio.on('subscribe_video_progress')
def handle_subscribe(data):
    video_id = data.get('video_id')
    logger.info(f'Client {request.sid} subscribed to video {video_id} progress')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)