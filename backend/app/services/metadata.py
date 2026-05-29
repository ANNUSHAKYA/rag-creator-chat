import re
import httpx
import subprocess
import json
from typing import Optional

def get_youtube_metadata(url: str) -> dict:
    """Use yt-dlp to pull YouTube metadata — no API key needed."""
    result = subprocess.run([
        "yt-dlp", "--dump-json", "--no-download", url
    ], capture_output=True, text=True, check=True)

    data = json.loads(result.stdout)

    view_count = data.get("view_count", 0) or 0
    like_count = data.get("like_count", 0) or 0
    comment_count = data.get("comment_count", 0) or 0

    engagement_rate = 0.0
    if view_count > 0:
        engagement_rate = round((like_count + comment_count) / view_count * 100, 4)

    return {
        "platform": "youtube",
        "url": url,
        "title": data.get("title", ""),
        "creator": data.get("uploader", ""),
        "channel_url": data.get("channel_url", ""),
        "follower_count": data.get("channel_follower_count", None),
        "views": view_count,
        "likes": like_count,
        "comments": comment_count,
        "engagement_rate": engagement_rate,
        "duration_seconds": data.get("duration", 0),
        "upload_date": data.get("upload_date", ""),
        "hashtags": data.get("tags", [])[:10],
        "description": data.get("description", "")[:500],
        "thumbnail": data.get("thumbnail", ""),
    }

def get_instagram_metadata(url: str) -> dict:
    """Use yt-dlp to pull Instagram reel metadata."""
    result = subprocess.run([
        "yt-dlp", "--dump-json", "--no-download",
        "--username", "anonymous", url
    ], capture_output=True, text=True)

    # yt-dlp may fail for private reels — handle gracefully
    if result.returncode != 0:
        m = re.search(r"/reel/([A-Za-z0-9_-]+)", url)
        reel_id = m.group(1) if m else "unknown"
        return {
            "platform": "instagram",
            "url": url,
            "video_id": reel_id,
            "creator": "unknown",
            "follower_count": None,
            "views": 0,
            "likes": 0,
            "comments": 0,
            "engagement_rate": 0.0,
            "duration_seconds": 0,
            "upload_date": "",
            "hashtags": [],
            "note": "Metadata limited — Instagram restricts public API access"
        }

    data = json.loads(result.stdout)
    view_count = data.get("view_count") or data.get("like_count", 0) or 0
    like_count = data.get("like_count", 0) or 0
    comment_count = data.get("comment_count", 0) or 0

    engagement_rate = 0.0
    if view_count > 0:
        engagement_rate = round((like_count + comment_count) / view_count * 100, 4)

    return {
        "platform": "instagram",
        "url": url,
        "title": data.get("title", ""),
        "creator": data.get("uploader", data.get("creator", "")),
        "follower_count": data.get("channel_follower_count", None),
        "views": view_count,
        "likes": like_count,
        "comments": comment_count,
        "engagement_rate": engagement_rate,
        "duration_seconds": data.get("duration", 0),
        "upload_date": data.get("upload_date", ""),
        "hashtags": data.get("tags", [])[:10],
        "thumbnail": data.get("thumbnail", ""),
    }

def get_metadata(url: str, platform: str) -> dict:
    if platform == "youtube":
        return get_youtube_metadata(url)
    elif platform == "instagram":
        return get_instagram_metadata(url)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
