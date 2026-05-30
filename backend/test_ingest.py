import asyncio
import httpx
from dotenv import load_dotenv
load_dotenv()

async def test_ingest():
    # Use two real short YouTube videos for speed
    payload = {
        "video_a_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_a_platform": "youtube",
        "video_b_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "video_b_platform": "youtube",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        print("Ingesting videos...")
        r = await client.post("http://localhost:8000/api/ingest", json=payload)
        data = r.json()

        if r.status_code != 200:
            print(f"Error status: {r.status_code}")
            print(f"Error detail: {r.text}")
            return None
            
        print(f"Session ID: {data['session_id']}")
        print(f"Video A chunks: {data['video_a']['chunks_stored']}")
        print(f"Video B chunks: {data['video_b']['chunks_stored']}")
        print(f"Video A engagement: {data['video_a']['metadata']['engagement_rate']}%")
        print(f"Video B engagement: {data['video_b']['metadata']['engagement_rate']}%")
        print(f"Status: {data['status']}")

        return data['session_id']

if __name__ == "__main__":
    asyncio.run(test_ingest())
