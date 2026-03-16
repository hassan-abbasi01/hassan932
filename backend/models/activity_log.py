from datetime import datetime
from bson import ObjectId

class ActivityLog:
    """
    Activity log model for tracking user and admin actions
    
    Categories:
    - auth: Login, logout, registration
    - video: Upload, delete, update, enhance
    - user: Profile update, settings change
    - admin: Admin actions, user management
    - system: System events, errors
    """
    
    def __init__(self, user_id, user_type, action, category, details=None, ip_address=None):
        self.user_id = user_id  # Can be user_id or admin_id
        self.user_type = user_type  # 'user' or 'admin'
        self.action = action  # e.g., 'login', 'video_upload', 'user_deleted'
        self.category = category  # auth, video, user, admin, system
        self.details = details or {}  # Additional data about the action
        self.ip_address = ip_address
        self.timestamp = datetime.utcnow()
        self.status = 'success'  # success, failed, pending
        
    def to_dict(self):
        """Convert activity log to dictionary"""
        return {
            "user_id": self.user_id,
            "user_type": self.user_type,
            "action": self.action,
            "category": self.category,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp,
            "status": self.status
        }
    
    @staticmethod
    def from_dict(data):
        """Create activity log from dictionary"""
        log = ActivityLog(
            user_id=data.get("user_id"),
            user_type=data.get("user_type", "user"),
            action=data.get("action"),
            category=data.get("category"),
            details=data.get("details", {}),
            ip_address=data.get("ip_address")
        )
        log.timestamp = data.get("timestamp", datetime.utcnow())
        log.status = data.get("status", "success")
        return log


class PlatformStats:
    """Helper class for platform statistics"""
    
    @staticmethod
    def calculate_stats(db):
        """Calculate current platform statistics"""
        users_collection = db.users
        videos_collection = db.videos
        logs_collection = db.activity_logs
        
        # Video model stores: 'size' (bytes), 'upload_date' (ISO string), 'metadata.duration' (seconds)
        # Status 'completed' means the video was enhanced/processed
        stats = {
            'total_users': users_collection.count_documents({}),
            'total_videos': videos_collection.count_documents({}),
            'total_storage_bytes': 0,
            'active_users_today': 0,
            'videos_uploaded_today': 0,
            'total_video_views': 0,
            'avg_video_duration': 0,
            'total_enhancements': videos_collection.count_documents({'status': 'completed'}),
        }
        
        # Calculate total storage — field is 'size', some older docs may also have 'file_size'
        pipeline = [
            {'$group': {'_id': None, 'total_size': {'$sum': '$size'}, 'total_file_size': {'$sum': '$file_size'}}}
        ]
        storage_result = list(videos_collection.aggregate(pipeline))
        if storage_result:
            total = (storage_result[0].get('total_size') or 0) + (storage_result[0].get('total_file_size') or 0)
            # Avoid double-counting: use whichever is larger (size is canonical)
            stats['total_storage_bytes'] = max(storage_result[0].get('total_size') or 0, storage_result[0].get('total_file_size') or 0)
        
        # Active users today — check activity_logs + also check users who logged in today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_iso = today_start.isoformat()
        
        active_from_logs = logs_collection.distinct('user_id', {
            'timestamp': {'$gte': today_start},
            'user_type': 'user'
        })
        
        # Also count users who uploaded videos today
        active_from_uploads = videos_collection.distinct('user_id', {
            'upload_date': {'$gte': today_iso}
        })
        
        all_active = set(str(uid) for uid in active_from_logs) | set(str(uid) for uid in active_from_uploads)
        stats['active_users_today'] = len(all_active)
        
        # Videos uploaded today — upload_date is stored as ISO string
        stats['videos_uploaded_today'] = videos_collection.count_documents({
            'upload_date': {'$gte': today_iso}
        })
        
        # Average video duration — stored in metadata.duration (seconds)
        avg_pipeline = [
            {'$match': {'metadata.duration': {'$exists': True, '$ne': None, '$gt': 0}}},
            {'$group': {'_id': None, 'avg_duration': {'$avg': '$metadata.duration'}}}
        ]
        avg_result = list(videos_collection.aggregate(avg_pipeline))
        if avg_result and avg_result[0].get('avg_duration') is not None:
            stats['avg_video_duration'] = round(avg_result[0].get('avg_duration'), 2)
        else:
            stats['avg_video_duration'] = 0
        
        return stats
