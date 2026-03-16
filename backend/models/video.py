from datetime import datetime
from bson import ObjectId

class Video:
    def __init__(self, user_id, filename, filepath, size):
        self._id = None
        self.user_id = user_id
        self.filename = filename
        self.filepath = filepath
        self.size = size
        self.status = "uploaded"
        self.processing_options = {}
        self.upload_date = datetime.utcnow()
        self.process_start_time = None
        self.process_end_time = None
        self.error = None
        self.metadata = {
            "duration": None,
            "format": None,
            "resolution": None,
            "fps": None
        }
        self.outputs = {
            "processed_video": None,
            "thumbnail": None,
            "subtitles": None,
            "summary": None
        }
        self.transcript = None  # Store full transcription with timestamps and filler markers

    def to_dict(self):
        result = {
            "user_id": str(self.user_id),
            "filename": self.filename,
            "filepath": self.filepath,
            "size": self.size,
            "file_size": self.size,
            "status": self.status,
            "processing_options": self.processing_options,
            "upload_date": self.upload_date.isoformat() if isinstance(self.upload_date, datetime) else self.upload_date,
            "process_start_time": self.process_start_time.isoformat() if isinstance(self.process_start_time, datetime) else self.process_start_time,
            "process_end_time": self.process_end_time.isoformat() if isinstance(self.process_end_time, datetime) else self.process_end_time,
            "error": self.error,
            "metadata": self.metadata,
            "outputs": self.outputs,
            "transcript": self.transcript
        }
        if self._id:
            result["_id"] = str(self._id)
        return result

    @staticmethod
    def from_dict(data):
        video = Video(
            user_id=ObjectId(data["user_id"]) if isinstance(data["user_id"], str) else data["user_id"],
            filename=data.get("filename", ""),
            filepath=data.get("filepath", ""),
            size=data.get("size", 0)
        )
        video._id = data.get("_id")
        video.status = data.get("status", "uploaded")
        video.processing_options = data.get("processing_options", {})
        video.upload_date = data.get("upload_date", datetime.utcnow())
        video.process_start_time = data.get("process_start_time")
        video.process_end_time = data.get("process_end_time")
        video.error = data.get("error")
        video.metadata = data.get("metadata", {})
        video.outputs = data.get("outputs", {})
        video.transcript = data.get("transcript")
        return video