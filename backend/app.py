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
from services.admin_service import AdminService

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
admin_service = AdminService(db, app.config['SECRET_KEY'])

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

# REQUEST LOGGING MIDDLEWARE - See ALL incoming requests
@app.before_request
def log_request():
    """Log every incoming request with details"""
    print(f"\n{'='*80}")
    print(f"[INCOMING REQUEST]")
    print(f"{'='*80}")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"Full URL: {request.url}")
    print(f"Remote Address: {request.remote_addr}")
    print(f"Headers: {dict(request.headers)}")
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            print(f"JSON Body: {request.get_json()}")
        elif request.form:
            print(f"Form Data: {dict(request.form)}")
        elif request.files:
            print(f"Files: {list(request.files.keys())}")
    print(f"{'='*80}\n")
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")

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
    redirect_uri = url_for('google_callback', _external=True)
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
    return redirect(f"http://localhost:5173/auth/callback?token={jwt_token}")



def require_auth(f):
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        # Also accept token from query param (for direct download links)
        token_param = request.args.get('token')
        
        if not auth_header and not token_param:
            return jsonify({'error': 'No authorization header'}), 401

        try:
            if auth_header:
                token = auth_header.split(' ')[1]
            else:
                token = token_param
            print(f"[AUTH] Auth header: {str(token)[:30] if token else 'None'}...")
            user_id = auth_service.verify_token(token)
            print(f"[AUTH] User ID from token: {user_id}")
            return f(user_id, *args, **kwargs)
        except Exception as e:
            print(f"[AUTH] Token verification failed: {e}")
            return jsonify({'error': str(e)}), 401

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
            
        return jsonify(ticket.to_json()), 200
    except Exception as e:
        logger.exception("Get support ticket error")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/support/tickets/<ticket_id>/reply', methods=['POST'])
@require_auth
def user_reply_to_ticket(user_id, ticket_id):
    """User replies back to their support ticket"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Verify ticket belongs to user
        try:
            ticket = support_service.get_ticket(ticket_id)
        except Exception as e:
            logger.error(f"Error getting ticket: {e}")
            return jsonify({'error': 'Failed to retrieve ticket'}), 500
            
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        if str(ticket.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get user details
        try:
            from models.user import User
            user_obj = User.find_by_id(user_id)
            user_name = f"{user_obj.first_name} {user_obj.last_name}" if user_obj else "User"
        except Exception as e:
            logger.warning(f"Error getting user info: {e}")
            user_name = "User"
        
        # Create response data
        response_data = {
            'message': message,
            'responder_type': 'user',
            'responder_id': str(user_id),
            'responder_name': user_name,
            'timestamp': datetime.utcnow()
        }
        
        # Add response to ticket
        try:
            result = support_service.add_response(ticket_id, response_data)
        except Exception as e:
            logger.exception(f"Error adding user response: {e}")
            return jsonify({'error': f'Failed to add response: {str(e)}'}), 500
        
        if result:
            return jsonify({
                'message': 'Reply sent successfully',
                'response': response_data
            }), 200
        else:
            return jsonify({'error': 'Failed to add response'}), 500
            
    except Exception as e:
        logger.exception("User reply error")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_video(user_id):
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        video_id = video_service.save_video(file, user_id)

        return jsonify({'message': 'Video uploaded successfully', 'video_id': str(video_id)}), 200
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
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
        
        # Mark video as processing immediately so frontend knows it started
        video_service.update_video_status(video_id, 'processing')
        
        # Run heavy processing in a background thread so this request returns immediately
        import threading
        def _run():
            try:
                video_service.process_video(video_id, options)
                video = video_service.get_video(video_id)
                if video:
                    print(f"[PROCESS] Video outputs after processing: {video.outputs}")
                    logger.info(f"Video outputs: {video.outputs}")
            except Exception as ex:
                logger.error(f"[PROCESS] Background processing error: {ex}")
                import traceback; traceback.print_exc()
                video_service.update_video_status(video_id, 'failed')

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        
        return jsonify({'message': 'Processing started'}), 200
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
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the processed video path (prefer condensed_video for summarized videos)
        processed_path = (
            video.outputs.get('condensed_video') or
            video.outputs.get('processed_video') or
            video.filepath
        )
        
        # Resolve to absolute path so send_file works on Windows
        if not os.path.isabs(processed_path):
            processed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), processed_path)
        
        logger.info(f"[DOWNLOAD] Serving file: {processed_path}")
        
        if not os.path.exists(processed_path):
            logger.error(f"[DOWNLOAD] File not found: {processed_path}")
            return jsonify({'error': 'Processed video not found'}), 404
        
        # Use a friendly download filename
        if video.outputs.get('condensed_video'):
            dl_name = f"summarized_{video.filename}"
        else:
            dl_name = f"enhanced_{video.filename}"
        
        return send_file(
            processed_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=dl_name,
            conditional=False
        )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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

@app.route('/api/videos/<video_id>/summary', methods=['GET'])
@require_auth
def get_video_summary(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check for AI text summary file
        ai_summary_path = video.outputs.get('ai_text_summary', '')
        if ai_summary_path and isinstance(ai_summary_path, str) and os.path.exists(ai_summary_path):
            import json as json_lib
            with open(ai_summary_path, 'r', encoding='utf-8') as f:
                summary_data = json_lib.load(f)
            return jsonify({'summary': summary_data}), 200
        
        # Check for inline ai_text_summary in summary dict
        summary_info = video.outputs.get('summary', {})
        if isinstance(summary_info, dict) and 'ai_text_summary' in summary_info:
            return jsonify({'summary': summary_info['ai_text_summary']}), 200
        
        return jsonify({'error': 'No text summary available', 'summary': None}), 200
        
    except Exception as e:
        logger.error(f"Get summary error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/videos/<video_id>/download/summarized', methods=['GET'])
@require_auth
def download_summarized_video(user_id, video_id):
    try:
        video = video_service.get_video(video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if user owns the video
        if str(video.user_id) != str(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the condensed/summarized video path
        condensed_path = video.outputs.get('condensed_video')
        if not condensed_path:
            return jsonify({'error': 'No summarized video available'}), 404
        
        # Resolve to absolute path
        if not os.path.isabs(condensed_path):
            condensed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), condensed_path)
        
        logger.info(f"[DOWNLOAD SUMMARIZED] Serving file: {condensed_path}")
        
        if not os.path.exists(condensed_path):
            logger.error(f"[DOWNLOAD SUMMARIZED] File not found: {condensed_path}")
            return jsonify({'error': 'Summarized video not found'}), 404
        
        return send_file(
            condensed_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"summarized_{video.filename}",
            conditional=False
        )
    except Exception as e:
        logger.error(f"Download summarized error: {str(e)}")
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
        
        # Check if transcript exists and has actual words
        if not video.transcript or video.transcript.get('total_words', 0) == 0:
            # Transcript not generated yet or empty, try to generate now
            logger.info(f"[TRANSCRIPT] No transcript or 0 words, generating now...")
            video_service._auto_transcribe_video(video_id, video.filepath)
            
            # Re-fetch video
            video = video_service.get_video(video_id)
            if not video or not video.transcript or video.transcript.get('total_words', 0) == 0:
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
    
    # Convert ObjectId to string
    user['_id'] = str(user['_id'])
    
    # Remove sensitive fields (both old and new formats)
    user.pop('password', None)
    user.pop('password_hash', None)
    
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


# ============================================================================
# ADMIN API ROUTES
# ============================================================================

def admin_required(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        admin = admin_service.verify_token(token)
        
        if not admin:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add admin to request context
        request.admin = admin
        return f(*args, **kwargs)
    
    return decorated_function

def permission_required(permission):
    """Decorator to check specific admin permission"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'admin'):
                return jsonify({'error': 'Unauthorized'}), 401
            
            if not request.admin.has_permission(permission):
                return jsonify({'error': f'Permission denied: {permission}'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ===================== ADMIN AUTHENTICATION =====================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        ip_address = request.remote_addr
        result = admin_service.login(email, password, ip_address)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/admin/verify', methods=['GET'])
@admin_required
def admin_verify():
    """Verify admin token and return admin info"""
    try:
        admin = request.admin
        return jsonify({
            'success': True,
            'admin': {
                'email': admin.email,
                'name': admin.name,
                'role': admin.role,
                'permissions': admin.permissions
            }
        }), 200
    except Exception as e:
        logger.error(f"Admin verify error: {e}")
        return jsonify({'error': 'Verification failed'}), 500

# ===================== USER MANAGEMENT =====================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
@permission_required('manage_users')
def get_users():
    """Get paginated list of users"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'created_at')
        
        result = admin_service.get_all_users(page, limit, search, sort_by)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({'error': 'Failed to get users'}), 500

@app.route('/api/admin/users/<user_id>', methods=['GET'])
@admin_required
@permission_required('manage_users')
def get_user_detail(user_id):
    """Get detailed user information"""
    try:
        result = admin_service.get_user_details(user_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get user detail error: {e}")
        return jsonify({'error': 'Failed to get user details'}), 500

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@admin_required
@permission_required('delete_users')
def delete_user_by_admin(user_id):
    """Delete a user"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason')
        
        admin_id = str(request.admin.to_dict().get('_id', ''))
        result = admin_service.delete_user(admin_id, user_id, reason)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/admin/users/<user_id>/status', methods=['PUT'])
@admin_required
@permission_required('manage_users')
def update_user_status_by_admin(user_id):
    """Update user active status"""
    try:
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        admin_id = str(request.admin.to_dict().get('_id', ''))
        result = admin_service.update_user_status(admin_id, user_id, is_active)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Update user status error: {e}")
        return jsonify({'error': 'Failed to update user status'}), 500

# ===================== VIDEO MANAGEMENT =====================

@app.route('/api/admin/videos', methods=['GET'])
@admin_required
@permission_required('manage_videos')
def get_videos_by_admin():
    """Get paginated list of videos"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        search = request.args.get('search')
        filter_by = request.args.get('filter')
        
        result = admin_service.get_all_videos(page, limit, search, filter_by)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get videos error: {e}")
        return jsonify({'error': 'Failed to get videos'}), 500

@app.route('/api/admin/videos/<video_id>', methods=['DELETE'])
@admin_required
@permission_required('delete_videos')
def delete_video_by_admin(video_id):
    """Delete a video"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason')
        
        admin_id = str(request.admin.to_dict().get('_id', ''))
        result = admin_service.delete_video(admin_id, video_id, reason)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Delete video error: {e}")
        return jsonify({'error': 'Failed to delete video'}), 500

# ===================== ANALYTICS & DASHBOARD =====================

@app.route('/api/admin/dashboard/stats', methods=['GET'])
@admin_required
@permission_required('view_analytics')
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        result = admin_service.get_dashboard_stats()
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get dashboard stats error: {e}")
        return jsonify({'error': 'Failed to get dashboard stats'}), 500

@app.route('/api/admin/analytics/chart/<chart_type>', methods=['GET'])
@admin_required
@permission_required('view_analytics')
def get_analytics_chart(chart_type):
    """Get analytics chart data"""
    try:
        period = request.args.get('period', 'week')  # week, month, year
        
        result = admin_service.get_analytics_chart_data(chart_type, period)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get chart data error: {e}")
        return jsonify({'error': 'Failed to get chart data'}), 500

@app.route('/api/admin/activity-logs', methods=['GET'])
@admin_required
@permission_required('view_analytics')
def get_activity_logs():
    """Get activity logs"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        category = request.args.get('category')
        user_type = request.args.get('user_type')
        
        result = admin_service.get_activity_logs(page, limit, category, user_type)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get activity logs error: {e}")
        return jsonify({'error': 'Failed to get activity logs'}), 500

# ===================== ADMIN PROFILE =====================

@app.route('/api/admin/profile', methods=['GET'])
@admin_required
def get_admin_profile():
    """Get admin profile"""
    try:
        admin = request.admin
        return jsonify({
            'success': True,
            'profile': admin.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Get admin profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/admin/profile', methods=['PUT'])
@admin_required
def update_admin_profile():
    """Update admin profile"""
    try:
        data = request.get_json()
        # TODO: Implement profile update
        return jsonify({'success': True, 'message': 'Profile updated'}), 200
    except Exception as e:
        logger.error(f"Update admin profile error: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500

# ===================== ADMIN SUPPORT TICKETS =====================

@app.route('/api/support/all', methods=['GET'])
@admin_required
def get_all_support_tickets():
    """Get all support tickets (Admin only)"""
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        logger.info(f"[DEBUG] Fetching all support tickets, status={status}, priority={priority}")
        result = support_service.get_all_tickets(status=status, priority=priority)
        logger.info(f"[DEBUG] Got {len(result)} tickets from service")
        
        return jsonify({
            'success': True,
            'tickets': result
        }), 200
        
    except Exception as e:
        logger.error(f"Get all support tickets error: {e}")
        logger.exception("Full traceback:")
        return jsonify({'error': 'Failed to get support tickets'}), 500

@app.route('/api/support/ticket/<ticket_id>', methods=['GET'])
@admin_required
def get_ticket_details(ticket_id):
    """Get detailed ticket information with responses (Admin)"""
    try:
        ticket = support_service.get_ticket(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_json()
        }), 200
        
    except Exception as e:
        logger.error(f"Get ticket details error: {e}")
        return jsonify({'error': 'Failed to get ticket details'}), 500

@app.route('/api/support/ticket/<ticket_id>/reply', methods=['POST'])
@admin_required
def reply_to_ticket(ticket_id):
    """Admin reply to support ticket"""
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get admin info safely
        try:
            admin_dict = request.admin.to_dict()
            admin_id = str(admin_dict.get('_id', ''))
            admin_email = admin_dict.get('email', 'Admin')
        except Exception as e:
            logger.error(f"Error getting admin info: {e}")
            admin_id = 'admin'
            admin_email = 'Admin'
        
        # Add response with admin info
        response_data = {
            'message': message,
            'responder_type': 'admin',
            'responder_id': admin_id,
            'responder_name': admin_email,
            'timestamp': datetime.utcnow()
        }
        
        # Add response to database
        try:
            support_service.add_response(ticket_id, response_data)
        except Exception as e:
            logger.error(f"Error adding response: {e}")
            return jsonify({'error': f'Failed to add response: {str(e)}'}), 500
        
        # Update status to pending
        try:
            support_service.update_ticket_status(ticket_id, 'pending')
        except Exception as e:
            logger.warning(f"Error updating ticket status: {e}")
            # Don't fail the request if status update fails
        
        return jsonify({
            'success': True,
            'message': 'Reply sent successfully'
        }), 200
        
    except Exception as e:
        logger.exception("Reply to ticket error")
        return jsonify({'error': f'Failed to send reply: {str(e)}'}), 500


if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False, host='0.0.0.0', port=5001)