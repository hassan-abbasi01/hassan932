from datetime import datetime
from bson.objectid import ObjectId

class SupportTicket:
    def __init__(self, user_id=None, name=None, email=None, subject=None, 
                 description=None, priority='medium', ticket_type='bug', 
                 status='open', created_at=None, updated_at=None, responses=None, _id=None):
        self._id = ObjectId(_id) if _id else ObjectId()
        self.user_id = ObjectId(user_id) if user_id else None
        self.name = name
        self.email = email
        self.subject = subject
        self.description = description
        self.priority = priority  # low, medium, high, urgent
        self.type = ticket_type   # bug, feature, question, other
        self.status = status      # open, in_progress, resolved, closed
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.responses = responses if responses is not None else []  # List of admin responses

    def to_dict(self):
        # Convert datetime objects to ISO format strings for JSON serialization
        responses_serialized = []
        if self.responses:
            for response in self.responses:
                # Handle both dict and non-dict responses
                if isinstance(response, dict):
                    response_copy = response.copy()
                    # Convert timestamp if it's a datetime object
                    if 'timestamp' in response_copy:
                        timestamp = response_copy['timestamp']
                        if hasattr(timestamp, 'isoformat'):
                            response_copy['timestamp'] = timestamp.isoformat()
                        elif not isinstance(timestamp, str):
                            response_copy['timestamp'] = str(timestamp)
                    responses_serialized.append(response_copy)
                else:
                    responses_serialized.append(response)
        
        # Helper function to serialize datetime
        def serialize_datetime(dt):
            if dt is None:
                return None
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            if isinstance(dt, str):
                return dt
            return str(dt)
        
        return {
            '_id': self._id if isinstance(self._id, ObjectId) else ObjectId(self._id),
            'user_id': str(self.user_id) if self.user_id else None,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'description': self.description,
            'priority': self.priority,
            'type': self.type,
            'status': self.status,
            'created_at': serialize_datetime(self.created_at),
            'updated_at': serialize_datetime(self.updated_at),
            'responses': responses_serialized
        }

    def to_json(self):
        """Return a JSON-serializable dict (with string IDs)"""
        d = self.to_dict()
        d['_id'] = str(d['_id'])
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(
            _id=data.get('_id'),
            user_id=data.get('user_id'),
            name=data.get('name'),
            email=data.get('email'),
            subject=data.get('subject'),
            description=data.get('description'),
            priority=data.get('priority', 'medium'),
            ticket_type=data.get('type', 'bug'),
            status=data.get('status', 'open'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            responses=data.get('responses', [])
        )
