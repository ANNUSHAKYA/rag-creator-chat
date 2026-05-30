import asyncio
import httpx
import json

SESSION_ID = "93d9a5f2-b18f-4e7e-80cc-3387bbd42f2f"

QUESTIONS = [
    "What is the engagement rate of each video?",
    "Why did Video A get more engagement than Video B?",
    "Compare the hooks in the first 5 seconds of each video.",
    "Who is the creator of Video B and what is their follower count?",
    "Suggest 3 improvements for Video B based on what worked in Video A.",
]

async def ask(question: str):
    print(f"\n{'='*60}")
    print(f"Q: {question}")
    print(f"{'='*60}")

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/chat",
            json={"session_id": SESSION_ID, "question": question}
        ) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    elif data.startswith("[CITATIONS]"):
                        citations = json.loads(data[11:])
                        print(f"\n\nSources used:")
                        for c in citations:
                            print(f"  - Video {c['video_id']} chunk {c['chunk_index']}: {c['preview']}")
                    else:
                        token = data
                        if data.startswith('"') and data.endswith('"'):
                            try:
                                token = json.loads(data)
                            except Exception:
                                pass
                        print(token, end="", flush=True)

async def main():
    for q in QUESTIONS:
        await ask(q)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
