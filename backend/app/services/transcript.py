import os
import re
import subprocess
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, CouldNotRetrieveTranscript

def extract_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract YouTube ID from: {url}")

def get_youtube_transcript(url: str) -> dict:
    video_id = extract_youtube_id(url)
    try:
        api = YouTubeTranscriptApi()
        try:
            # 1. Try to fetch English transcript first
            fetched = api.fetch(video_id, languages=["en"])
        except Exception:
            # 2. Fall back to any available transcript language
            ts_list = api.list(video_id)
            fetched = None
            for t in ts_list:
                fetched = t.fetch()
                break
            if fetched is None:
                raise ValueError("No transcripts found in any language")

        transcript_list = list(fetched)
        full_text = " ".join([t.text for t in transcript_list])
        # Keep timestamped chunks for citation
        chunks_with_time = [
            {"text": t.text, "start": t.start, "duration": t.duration}
            for t in transcript_list
        ]
        return {
            "video_id": video_id,
            "full_text": full_text,
            "timed_chunks": chunks_with_time,
            "source": "youtube_transcript_api"
        }
    except Exception:
        # Fallback: download audio and run Whisper
        return get_transcript_via_whisper(url, video_id)

def get_transcript_via_whisper(url: str, video_id: str) -> dict:
    import whisper
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "mp3",
            "-o", audio_path, url
        ], check=True, capture_output=True)
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return {
            "video_id": video_id,
            "full_text": result["text"],
            "timed_chunks": [
                {"text": s["text"], "start": s["start"], "duration": s["end"] - s["start"]}
                for s in result["segments"]
            ],
            "source": "whisper"
        }

def get_instagram_transcript(url: str) -> dict:
    """Download Instagram reel audio and transcribe with Whisper."""
    import whisper
    # Extract shortcode from URL
    m = re.search(r"/reel/([A-Za-z0-9_-]+)", url)
    if not m:
        raise ValueError(f"Cannot extract Instagram reel ID from: {url}")
    reel_id = m.group(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "reel.mp3")
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "mp3",
            "-o", audio_path, url
        ], check=True, capture_output=True)
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return {
            "video_id": reel_id,
            "full_text": result["text"],
            "timed_chunks": [
                {"text": s["text"], "start": s["start"], "duration": s["end"] - s["start"]}
                for s in result["segments"]
            ],
            "source": "whisper"
        }

def get_transcript(url: str, platform: str) -> dict:
    if platform == "youtube":
        return get_youtube_transcript(url)
    elif platform == "instagram":
        return get_instagram_transcript(url)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
