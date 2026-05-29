import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.services.transcript import get_transcript
from app.services.metadata import get_metadata

# Use any real public YouTube URL for testing
YT_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

print("Testing metadata...")
meta = get_metadata(YT_URL, "youtube")
print(f"Creator: {meta['creator']}")
print(f"Views: {meta['views']}")
print(f"Engagement rate: {meta['engagement_rate']}%")

print("\nTesting transcript...")
transcript = get_transcript(YT_URL, "youtube")
print(f"Transcript length: {len(transcript['full_text'])} chars")
print(f"First 200 chars: {transcript['full_text'][:200]}")
