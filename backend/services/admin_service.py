import jwt
import bcrypt
from datetime import datetime, timedelta
from bson import ObjectId
from models.admin import Admin
from models.activity_log import ActivityLog, PlatformStats

class AdminService:
    """
    Admin service for authentication, user management, and analytics
    """
    
    def __init__(self, db, secret_key):
        self.db = db
        self.admins_collection = db.admins
        self.users_collection = db.users
        self.videos_collection = db.videos
        self.logs_collection = db.activity_logs
        self.secret_key = secret_key
        
        # Create indexes
        self.admins_collection.create_index("email", unique=True)
        self.logs_collection.create_index([("timestamp", -1)])
        self.logs_collection.create_index("user_id")
        
        # Create default super admin if no admins exist
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default super admin on first run"""
        if self.admins_collection.count_documents({}) == 0:
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
            admin = Admin(
                email="admin@snipx.com",
                password_hash=password_hash.decode('utf-8'),
                name="Super Admin",
                role="super_admin"
            )
            self.admins_collection.insert_one(admin.to_dict(include_sensitive=True))
            print(f"[ADMIN] ✅ Default super admin created: admin@snipx.com / admin123")
    
    # ===================== AUTHENTICATION =====================
    
    def login(self, email, password, ip_address=None):
        """Admin login with JWT token"""
        try:
            print(f"\n[DEBUG] Admin login attempt for: {email}")
            
            # **SECURITY**: Check if this email belongs to a regular user account
            # Regular users should ONLY login through /api/auth/login
            user_exists = self.users_collection.find_one({"email": email})
            print(f"[DEBUG] User exists in users collection: {user_exists is not None}")
            if user_exists:
                self._log_activity(None, 'user', 'admin_login_attempt', 'auth',
                                 {'reason': 'User tried to login as admin', 'email': email}, ip_address)
                return {"success": False, "message": "Please use the regular login page for user accounts"}
            
            admin_data = self.admins_collection.find_one({"email": email})
            print(f"[DEBUG] Admin found in admins collection: {admin_data is not None}")
            
            if not admin_data:
                self._log_activity(None, 'admin', 'login_failed', 'auth', 
                                 {'reason': 'Invalid email', 'email': email}, ip_address)
                return {"success": False, "message": "Invalid credentials"}
            
            print(f"[DEBUG] Admin is_active: {admin_data.get('is_active', True)}")
            if not admin_data.get('is_active', True):
                self._log_activity(str(admin_data['_id']), 'admin', 'login_blocked', 'auth',
                                 {'reason': 'Account disabled'}, ip_address)
                return {"success": False, "message": "Account is disabled"}
            
            # Verify password
            password_hash = admin_data.get('password_hash', '').encode('utf-8')
            print(f"[DEBUG] Password hash exists: {bool(password_hash)}")
            password_match = bcrypt.checkpw(password.encode('utf-8'), password_hash)
            print(f"[DEBUG] Password match: {password_match}")
            if not password_match:
                self._log_activity(str(admin_data['_id']), 'admin', 'login_failed', 'auth',
                                 {'reason': 'Invalid password'}, ip_address)
                return {"success": False, "message": "Invalid credentials"}
            
            # Update last login
            self.admins_collection.update_one(
                {"_id": admin_data['_id']},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            # Generate JWT token
            admin = Admin.from_dict(admin_data)
            token = self._generate_token(str(admin_data['_id']), admin.role)
            
            # Log successful login
            self._log_activity(str(admin_data['_id']), 'admin', 'login_success', 'auth',
                             {'name': admin.name}, ip_address)
            
            return {
                "success": True,
                "token": token,
                "admin": {
                    "id": str(admin_data['_id']),
                    "email": admin.email,
                    "name": admin.name,
                    "role": admin.role,
                    "permissions": admin.permissions
                }
            }
            
        except Exception as e:
            print(f"[ADMIN] Login error: {e}")
            return {"success": False, "message": "Login failed"}
    
    def verify_token(self, token):
        """Verify admin JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            admin_id = payload.get('admin_id')
            
            admin_data = self.admins_collection.find_one({"_id": ObjectId(admin_id)})
            if not admin_data or not admin_data.get('is_active', True):
                return None
            
            return Admin.from_dict(admin_data)
            
        except jwt.ExpiredSignatureError:
            print("[ADMIN] Token expired")
            return None
        except jwt.InvalidTokenError:
            print("[ADMIN] Invalid token")
            return None
    
    def _generate_token(self, admin_id, role):
        """Generate JWT token for admin"""
        payload = {
            'admin_id': admin_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    # ===================== USER MANAGEMENT =====================
    
    def get_all_users(self, page=1, limit=20, search=None, sort_by='created_at'):
        """Get paginated list of users"""
        try:
            skip = (page - 1) * limit
            query = {}
            
            # Search filter
            if search:
                query['$or'] = [
                    {'email': {'$regex': search, '$options': 'i'}},
                    {'first_name': {'$regex': search, '$options': 'i'}},
                    {'last_name': {'$regex': search, '$options': 'i'}}
                ]
            
            # Get total count
            total = self.users_collection.count_documents(query)
            
            # Get users
            users = list(self.users_collection.find(query)
                        .sort(sort_by, -1)
                        .skip(skip)
                        .limit(limit))
            
            # Format users with video count
            result = []
            for user in users:
                user_info = {
                    'id': str(user['_id']),
                    'email': user.get('email'),
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'created_at': user.get('created_at'),
                    'video_count': len(user.get('videos', [])),
                    'last_active': self._get_user_last_activity(str(user['_id']))
                }
                result.append(user_info)
            
            return {
                'success': True,
                'users': result,
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit
            }
            
        except Exception as e:
            print(f"[ADMIN] Get users error: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_user_details(self, user_id):
        """Get detailed user information"""
        try:
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            # Get user's videos
            videos = list(self.videos_collection.find({"user_id": user_id}))
            
            # Get recent activity
            recent_activity = list(self.logs_collection.find(
                {"user_id": user_id, "user_type": "user"}
            ).sort("timestamp", -1).limit(20))
            
            return {
                'success': True,
                'user': {
                    'id': str(user['_id']),
                    'email': user.get('email'),
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'created_at': user.get('created_at'),
                    'updated_at': user.get('updated_at'),
                    'settings': user.get('settings', {}),
                    'video_count': len(videos),
                    'videos': [{
                        'id': str(v['_id']),
                        'title': v.get('title'),
                        'duration': v.get('duration'),
                        'file_size': v.get('file_size'),
                        'uploaded_at': v.get('uploaded_at'),
                        'enhanced': v.get('enhanced', False)
                    } for v in videos],
                    'recent_activity': [{
                        'action': log.get('action'),
                        'category': log.get('category'),
                        'timestamp': log.get('timestamp'),
                        'details': log.get('details', {})
                    } for log in recent_activity]
                }
            }
            
        except Exception as e:
            print(f"[ADMIN] Get user details error: {e}")
            return {'success': False, 'message': str(e)}
    
    def delete_user(self, admin_id, user_id, reason=None):
        """Delete a user and their videos"""
        try:
            # Get user first
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            # Delete user's videos
            videos = self.videos_collection.find({"user_id": user_id})
            for video in videos:
                # TODO: Delete video files from storage
                pass
            
            self.videos_collection.delete_many({"user_id": user_id})
            
            # Delete user
            self.users_collection.delete_one({"_id": ObjectId(user_id)})
            
            # Log action
            self._log_activity(admin_id, 'admin', 'user_deleted', 'admin', {
                'deleted_user_id': user_id,
                'email': user.get('email'),
                'reason': reason
            })
            
            return {'success': True, 'message': 'User deleted successfully'}
            
        except Exception as e:
            print(f"[ADMIN] Delete user error: {e}")
            return {'success': False, 'message': str(e)}
    
    def update_user_status(self, admin_id, user_id, is_active):
        """Activate or deactivate user"""
        try:
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                self._log_activity(admin_id, 'admin', 'user_status_changed', 'admin', {
                    'user_id': user_id,
                    'new_status': 'active' if is_active else 'inactive'
                })
                return {'success': True}
            else:
                return {'success': False, 'message': 'User not found'}
                
        except Exception as e:
            print(f"[ADMIN] Update user status error: {e}")
            return {'success': False, 'message': str(e)}
    
    # ===================== VIDEO MANAGEMENT =====================
    
    def get_all_videos(self, page=1, limit=20, search=None, filter_by=None):
        """Get paginated list of videos"""
        try:
            skip = (page - 1) * limit
            query = {}
            
            # Search filter — search by filename (Video model has no 'title' field)
            if search:
                query['filename'] = {'$regex': search, '$options': 'i'}
            
            # Additional filters — 'enhanced' = status is 'completed'
            if filter_by == 'enhanced':
                query['status'] = 'completed'
            elif filter_by == 'unprocessed':
                query['status'] = {'$ne': 'completed'}
            
            total = self.videos_collection.count_documents(query)
            
            # Sort by _id descending (most recent first) since upload_date is a string
            videos = list(self.videos_collection.find(query)
                         .sort('_id', -1)
                         .skip(skip)
                         .limit(limit))
            
            # Get user info for each video
            result = []
            for video in videos:
                user = None
                user_id = video.get('user_id')
                if user_id:
                    try:
                        user = self.users_collection.find_one({"_id": ObjectId(user_id)})
                    except Exception:
                        pass
                
                # duration is in metadata.duration, file size is 'size' or 'file_size'
                metadata = video.get('metadata', {})
                file_size = video.get('size') or video.get('file_size', 0)
                duration = metadata.get('duration', 0) if isinstance(metadata, dict) else 0
                
                result.append({
                    'id': str(video['_id']),
                    'title': video.get('filename', 'Untitled'),
                    'duration': duration,
                    'file_size': file_size,
                    'uploaded_at': video.get('upload_date'),
                    'enhanced': video.get('status') == 'completed',
                    'status': video.get('status', 'uploaded'),
                    'user_email': user.get('email') if user else 'Unknown'
                })
            
            return {
                'success': True,
                'videos': result,
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit
            }
            
        except Exception as e:
            print(f"[ADMIN] Get videos error: {e}")
            return {'success': False, 'message': str(e)}
    
    def delete_video(self, admin_id, video_id, reason=None):
        """Delete a video"""
        try:
            video = self.videos_collection.find_one({"_id": ObjectId(video_id)})
            if not video:
                return {'success': False, 'message': 'Video not found'}
            
            # TODO: Delete video file from storage
            
            self.videos_collection.delete_one({"_id": ObjectId(video_id)})
            
            # Remove from user's video list
            self.users_collection.update_one(
                {"_id": ObjectId(video.get('user_id'))},
                {"$pull": {"videos": video_id}}
            )
            
            # Log action
            self._log_activity(admin_id, 'admin', 'video_deleted', 'admin', {
                'video_id': video_id,
                'title': video.get('title'),
                'reason': reason
            })
            
            return {'success': True, 'message': 'Video deleted successfully'}
            
        except Exception as e:
            print(f"[ADMIN] Delete video error: {e}")
            return {'success': False, 'message': str(e)}
    
    # ===================== ANALYTICS =====================
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        try:
            stats = PlatformStats.calculate_stats(self.db)
            
            # Additional time-based stats
            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            stats['users_this_week'] = self.users_collection.count_documents({
                'created_at': {'$gte': week_ago}
            })
            stats['users_this_month'] = self.users_collection.count_documents({
                'created_at': {'$gte': month_ago}
            })
            # upload_date is stored as ISO string
            stats['videos_this_week'] = self.videos_collection.count_documents({
                'upload_date': {'$gte': week_ago.isoformat()}
            })
            stats['videos_this_month'] = self.videos_collection.count_documents({
                'upload_date': {'$gte': month_ago.isoformat()}
            })
            
            return {'success': True, 'stats': stats}
            
        except Exception as e:
            print(f"[ADMIN] Get dashboard stats error: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_activity_logs(self, page=1, limit=50, filter_category=None, filter_user_type=None):
        """Get activity logs with pagination"""
        try:
            skip = (page - 1) * limit
            query = {}
            
            if filter_category:
                query['category'] = filter_category
            if filter_user_type:
                query['user_type'] = filter_user_type
            
            total = self.logs_collection.count_documents(query)
            logs = list(self.logs_collection.find(query)
                       .sort('timestamp', -1)
                       .skip(skip)
                       .limit(limit))
            
            return {
                'success': True,
                'logs': [{
                    'id': str(log['_id']),
                    'user_id': log.get('user_id'),
                    'user_type': log.get('user_type'),
                    'action': log.get('action'),
                    'category': log.get('category'),
                    'details': log.get('details', {}),
                    'timestamp': log.get('timestamp'),
                    'ip_address': log.get('ip_address')
                } for log in logs],
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit
            }
            
        except Exception as e:
            print(f"[ADMIN] Get activity logs error: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_analytics_chart_data(self, chart_type='users', period='week'):
        """Get data for analytics charts"""
        try:
            now = datetime.utcnow()
            
            if period == 'week':
                days = 7
                start_date = now - timedelta(days=days)
            elif period == 'month':
                days = 30
                start_date = now - timedelta(days=days)
            else:  # year
                days = 365
                start_date = now - timedelta(days=days)
            
            # Generate date range
            dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days + 1)]
            
            if chart_type == 'users':
                # Count new users per day
                pipeline = [
                    {'$match': {'created_at': {'$gte': start_date}}},
                    {'$group': {
                        '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'_id': 1}}
                ]
                results = list(self.users_collection.aggregate(pipeline))
                
            elif chart_type == 'videos':
                # Count video uploads per day
                pipeline = [
                    {'$match': {'uploaded_at': {'$gte': start_date}}},
                    {'$group': {
                        '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$uploaded_at'}},
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'_id': 1}}
                ]
                results = list(self.videos_collection.aggregate(pipeline))
            
            elif chart_type == 'activity':
                # Count activities per day
                pipeline = [
                    {'$match': {'timestamp': {'$gte': start_date}}},
                    {'$group': {
                        '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'_id': 1}}
                ]
                results = list(self.logs_collection.aggregate(pipeline))
            
            # Create map of date -> count
            data_map = {r['_id']: r['count'] for r in results}
            
            # Fill in all dates with 0 for missing days
            chart_data = [data_map.get(date, 0) for date in dates]
            
            return {
                'success': True,
                'labels': dates,
                'data': chart_data
            }
            
        except Exception as e:
            print(f"[ADMIN] Get chart data error: {e}")
            return {'success': False, 'message': str(e)}
    
    # ===================== HELPER METHODS =====================
    
    def _log_activity(self, user_id, user_type, action, category, details=None, ip_address=None):
        """Log an activity"""
        try:
            log = ActivityLog(user_id, user_type, action, category, details, ip_address)
            self.logs_collection.insert_one(log.to_dict())
        except Exception as e:
            print(f"[ADMIN] Log activity error: {e}")
    
    def _get_user_last_activity(self, user_id):
        """Get user's last activity timestamp"""
        try:
            log = self.logs_collection.find_one(
                {"user_id": user_id, "user_type": "user"},
                sort=[("timestamp", -1)]
            )
            return log.get('timestamp') if log else None
        except:
            return None
