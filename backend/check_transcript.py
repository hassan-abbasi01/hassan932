"""Check what transcript Whisper generated for the peanut butter video"""
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017')
db = client['snipx']

video = db.videos.find_one({'_id': ObjectId('69b122c28d31ea387682a062')})

if video:
    print("Video:", video.get('filename'))
    print("Status:", video.get('status'))
    transcript = video.get('transcript')
    if transcript and isinstance(transcript, dict):
        print("Total words:", transcript.get('total_words'))
        print("Filler count:", transcript.get('filler_count'))
        print("Repeated count:", transcript.get('repeated_count'))
        print("\nFull text:", transcript.get('text', '')[:500])
        print("\nAll words:")
        for i, w in enumerate(transcript.get('words', [])):
            marks = []
            if w.get('is_filler'):
                marks.append("FILLER")
            if w.get('is_repeated'):
                marks.append("REPEATED")
            mark_str = " <-- " + ",".join(marks) if marks else ""
            print("  [%d] '%s' (%.2f - %.2f)%s" % (i, w.get('text',''), w.get('start',0), w.get('end',0), mark_str))
    else:
        print("No transcript or empty:", type(transcript))
else:
    print("Video not found!")
