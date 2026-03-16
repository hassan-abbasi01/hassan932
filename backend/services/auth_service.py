import jwt
import bcrypt
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import os
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db):
        self.db = db
        self.users = db.users
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'your-default-secret-key-change-this-in-production')
        
        # Ensure we have a valid string secret key
        if not self.secret_key or not isinstance(self.secret_key, str):
            self.secret_key = 'your-default-secret-key-change-this-in-production'

    def register_user(self, email, password, first_name=None, last_name=None):
        if self.users.find_one({"email": email}):
            raise ValueError("Email already registered")

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
        # **SECURITY**: Check if this email belongs to an admin account
        # Admins should ONLY login through /api/admin/login
        admins_collection = self.db.admins
        admin_exists = admins_collection.find_one({"email": email})
        if admin_exists:
            raise ValueError("Admin accounts must login through the Admin Portal")
        
        # Fetch raw user document
        user_doc = self.users.find_one({"email": email})
        if not user_doc:
            raise ValueError("Invalid email or password")

        # Verify password — support both 'password_hash' (app.py) and 'password' (app_fast.py legacy)
        stored_hash = user_doc.get('password_hash') or user_doc.get('password')
        if not stored_hash:
            raise ValueError("Invalid email or password")
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            raise ValueError("Invalid email or password")

        # Generate JWT
        token = self.generate_token(str(user_doc['_id']))

        # Build JSON-serializable user dict
        user_data = {
            'id': str(user_doc['_id']),
            'email': user_doc['email'],
            'firstName': user_doc.get('first_name'),
            'lastName': user_doc.get('last_name')
        }

        return token, user_data

    def generate_token(self, user_id):
        try:
            payload = {
                'user_id': str(user_id),  # Ensure user_id is a string
                'exp': datetime.utcnow() + timedelta(days=1)
            }
            return jwt.encode(payload, self.secret_key, algorithm='HS256')
        except Exception as e:
            raise ValueError(f"Failed to generate token: {str(e)}")

    def verify_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    def get_user_by_id(self, user_id):
        from models.user import User  # import here to avoid circular
        user_doc = self.users.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise ValueError("User not found")
        return User.from_dict(user_doc)

    def update_user(self, user_id, updates):
        updates['updated_at'] = datetime.utcnow()
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        )
        if result.modified_count == 0:
            raise ValueError("User not found or no changes made")
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id):
        """
        Delete a user account and all associated data
        """
        try:
            # First check if user exists
            user_doc = self.users.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                raise ValueError("User not found")
            
            # Delete all user's videos from videos collection
            from pymongo import MongoClient
            videos_collection = self.db.videos
            user_videos = videos_collection.find({"user_id": ObjectId(user_id)})
            
            # Delete video files from filesystem
            import os
            for video in user_videos:
                try:
                    # Delete video file
                    if video.get('filepath') and os.path.exists(video['filepath']):
                        os.remove(video['filepath'])
                    
                    # Delete processed outputs
                    outputs = video.get('outputs', {})
                    for output_type, output_path in outputs.items():
                        if isinstance(output_path, str) and os.path.exists(output_path):
                            os.remove(output_path)
                        elif isinstance(output_path, dict):
                            for path in output_path.values():
                                if isinstance(path, str) and os.path.exists(path):
                                    os.remove(path)
                except Exception as e:
                    logger.warning(f"Failed to delete video files for user {user_id}: {str(e)}")
            
            # Delete all user's videos from database
            videos_collection.delete_many({"user_id": ObjectId(user_id)})
            
            # Delete user's support tickets
            support_tickets_collection = self.db.support_tickets
            support_tickets_collection.delete_many({"user_id": ObjectId(user_id)})
            
            # Finally delete the user account
            result = self.users.delete_one({"_id": ObjectId(user_id)})
            
            if result.deleted_count == 0:
                raise ValueError("Failed to delete user account")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise ValueError(f"Failed to delete account: {str(e)}")

    def create_demo_user(self):
        """
        Create or get demo user and return token
        """
        demo_email = "demo@snipx.com"
        demo_password = "demo1234"
        
        # Check if demo user already exists
        user_doc = self.users.find_one({"email": demo_email})
        
        if not user_doc:
            # Create demo user
            try:
                user_id = self.register_user(
                    email=demo_email,
                    password=demo_password,
                    first_name="Demo",
                    last_name="User"
                )
                user_doc = self.users.find_one({"_id": ObjectId(user_id)})
            except ValueError:
                # If registration fails, try to get existing user
                user_doc = self.users.find_one({"email": demo_email})
                if not user_doc:
                    raise ValueError("Failed to create demo user")
        
        # Generate token for demo user
        token = self.generate_token(str(user_doc['_id']))
        
        # Build user data
        user_data = {
            'id': str(user_doc['_id']),
            'email': user_doc['email'],
            'firstName': user_doc.get('first_name'),
            'lastName': user_doc.get('last_name')
        }
        
        return token, user_data
