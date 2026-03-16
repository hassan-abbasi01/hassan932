from datetime import datetime
from bson import ObjectId

class Admin:
    """
    Admin user model with role-based permissions
    
    Roles:
    - super_admin: Full access to everything
    - admin: Can manage users and videos
    - moderator: Can view analytics and manage content
    - support: Can only access chat/support features
    """
    
    def __init__(self, email, password_hash, name, role='admin'):
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.role = role  # super_admin, admin, moderator, support
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_login = None
        self.is_active = True
        self.permissions = self._get_permissions_by_role(role)
        self.avatar = None
        self.phone = None
        self.two_factor_enabled = False
        
    def _get_permissions_by_role(self, role):
        """Get default permissions based on role"""
        permissions_map = {
            'super_admin': {
                'manage_admins': True,
                'manage_users': True,
                'manage_videos': True,
                'view_analytics': True,
                'system_settings': True,
                'support_chat': True,
                'delete_users': True,
                'delete_videos': True
            },
            'admin': {
                'manage_admins': False,
                'manage_users': True,
                'manage_videos': True,
                'view_analytics': True,
                'system_settings': False,
                'support_chat': True,
                'delete_users': False,
                'delete_videos': True
            },
            'moderator': {
                'manage_admins': False,
                'manage_users': False,
                'manage_videos': True,
                'view_analytics': True,
                'system_settings': False,
                'support_chat': True,
                'delete_users': False,
                'delete_videos': False
            },
            'support': {
                'manage_admins': False,
                'manage_users': False,
                'manage_videos': False,
                'view_analytics': False,
                'system_settings': False,
                'support_chat': True,
                'delete_users': False,
                'delete_videos': False
            }
        }
        return permissions_map.get(role, permissions_map['support'])
    
    def has_permission(self, permission):
        """Check if admin has specific permission"""
        return self.permissions.get(permission, False)
    
    def to_dict(self, include_sensitive=False):
        """Convert admin to dictionary"""
        data = {
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "is_active": self.is_active,
            "permissions": self.permissions,
            "avatar": self.avatar,
            "phone": self.phone,
            "two_factor_enabled": self.two_factor_enabled
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data
    
    @staticmethod
    def from_dict(data):
        """Create admin from dictionary"""
        admin = Admin(
            email=data["email"],
            password_hash=data.get("password_hash"),
            name=data.get("name", "Admin User"),
            role=data.get("role", "admin")
        )
        admin.created_at = data.get("created_at", datetime.utcnow())
        admin.updated_at = data.get("updated_at", datetime.utcnow())
        admin.last_login = data.get("last_login")
        admin.is_active = data.get("is_active", True)
        admin.permissions = data.get("permissions", admin._get_permissions_by_role(admin.role))
        admin.avatar = data.get("avatar")
        admin.phone = data.get("phone")
        admin.two_factor_enabled = data.get("two_factor_enabled", False)
        return admin
