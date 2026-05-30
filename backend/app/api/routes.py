import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.transcript import get_transcript
from app.services.metadata import get_metadata
from app.services.embedder import embed_and_store, delete_session_chunks
from app.services.session_store import load_sessions, save_sessions
from app.chains.rag_chain import stream_rag_response

router = APIRouter()

# Load existing sessions on startup — persists across server restarts
sessions: dict = load_sessions()


class IngestRequest(BaseModel):
    video_a_url: str
    video_a_platform: str   # "youtube" or "instagram"
    video_b_url: str
    video_b_platform: str


class IngestResponse(BaseModel):
    session_id: str
    video_a: dict
    video_b: dict
    status: str


@router.get("/health")
async def health_check():
    from app.services.embedder import get_vectorstore
    vs = get_vectorstore()
    count = vs._collection.count()
    return {
        "status": "ok",
        "service": "RAG Creator Chat",
        "chunks_in_db": count,
        "active_sessions": len(sessions),
    }


@router.post("/ingest", response_model=IngestResponse)
async def ingest_videos(req: IngestRequest):
    """
    Pull transcripts + metadata for both videos,
    chunk + embed them, store in ChromaDB.
    Returns a session_id for subsequent chat calls.
    """
    session_id = str(uuid.uuid4())

    try:
        # Run both videos in parallel — halves ingest time
        loop = asyncio.get_event_loop()

        transcript_a, transcript_b = await asyncio.gather(
            loop.run_in_executor(None, get_transcript, req.video_a_url, req.video_a_platform),
            loop.run_in_executor(None, get_transcript, req.video_b_url, req.video_b_platform),
        )

        metadata_a, metadata_b = await asyncio.gather(
            loop.run_in_executor(None, get_metadata, req.video_a_url, req.video_a_platform),
            loop.run_in_executor(None, get_metadata, req.video_b_url, req.video_b_platform),
        )

        result_a = embed_and_store(transcript_a, metadata_a, "A", session_id)
        result_b = embed_and_store(transcript_b, metadata_b, "B", session_id)

        # Store metadata in session for RAG chain to access
        sessions[session_id] = {
            "video_a": {**metadata_a, "transcript_preview": transcript_a["full_text"][:300]},
            "video_b": {**metadata_b, "transcript_preview": transcript_b["full_text"][:300]},
            "chat_history": []
        }

        # Persist session to disk
        save_sessions(sessions)

        return IngestResponse(
            session_id=session_id,
            video_a={**result_a, "metadata": metadata_a},
            video_b={**result_b, "metadata": metadata_b},
            status="ready"
        )

    except Exception as e:
        # Clean up any partial data on failure
        delete_session_chunks(session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Return session metadata — used by frontend to populate video cards."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    return {
        "session_id": session_id,
        "video_a": session["video_a"],
        "video_b": session["video_b"],
    }


@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """Delete session data and ChromaDB chunks."""
    delete_session_chunks(session_id)
    sessions.pop(session_id, None)
    save_sessions(sessions)
    return {"status": "deleted"}


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    question: str


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Stream a RAG response for a question about the two videos.
    Returns Server-Sent Events (SSE).
    """
    if req.session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please ingest videos first."
        )

    session = sessions[req.session_id]

    async def event_generator():
        async for chunk in stream_rag_response(
            question=req.question,
            session_id=req.session_id,
            session=session,
        ):
            yield chunk
        # Persist updated chat history after full response
        save_sessions(sessions)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering
        },
    )


@router.delete("/chat/{session_id}/history")
async def clear_history(session_id: str):
    """Clear chat history for a session without deleting embeddings."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions[session_id]["chat_history"] = []
    save_sessions(sessions)
    return {"status": "history cleared"}
