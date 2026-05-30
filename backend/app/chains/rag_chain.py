import os
import json
from typing import AsyncGenerator, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from app.services.embedder import get_retriever

SYSTEM_PROMPT = """You are an expert social media analytics assistant helping creators understand their video performance.

You have access to transcripts and metadata from two videos:
- Video A: {video_a_title} by {video_a_creator} ({video_a_platform})
  Views: {video_a_views} | Likes: {video_a_likes} | Comments: {video_a_comments}
  Engagement Rate: {video_a_engagement}% | Duration: {video_a_duration}s
  Followers: {video_a_followers} | Upload date: {video_a_date}
  Hashtags: {video_a_hashtags}

- Video B: {video_b_title} by {video_b_creator} ({video_b_platform})
  Views: {video_b_views} | Likes: {video_b_likes} | Comments: {video_b_comments}
  Engagement Rate: {video_b_engagement}% | Duration: {video_b_duration}s
  Followers: {video_b_followers} | Upload date: {video_b_date}
  Hashtags: {video_b_hashtags}

RULES:
1. Every claim you make must cite its source as [Video A - chunk N] or [Video B - chunk N].
2. Use actual numbers from the metadata above — never say "I don't have that data" for metadata.
3. For transcript-based questions, quote directly from the retrieved chunks.
4. Be specific and actionable. Creators need real advice, not generic tips.
5. If comparing engagement, always show the calculation: (likes + comments) / views × 100.

Retrieved context from transcripts:
{context}
"""


def format_docs_with_citations(docs: List[Document]) -> str:
    """Format retrieved chunks with source citations."""
    formatted = []
    for i, doc in enumerate(docs):
        video_id = doc.metadata.get("video_id", "?")
        chunk_idx = doc.metadata.get("chunk_index", i)
        is_hook = doc.metadata.get("is_hook", False)
        hook_label = " [HOOK - first 5 seconds]" if is_hook else ""
        formatted.append(
            f"[Video {video_id} - chunk {chunk_idx}]{hook_label}\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(formatted)


def build_metadata_context(session: dict) -> dict:
    """Extract all metadata fields for the system prompt."""
    a = session["video_a"]
    b = session["video_b"]
    return {
        "video_a_title": a.get("title", "Video A"),
        "video_a_creator": a.get("creator", "Unknown"),
        "video_a_platform": a.get("platform", ""),
        "video_a_views": f"{a.get('views', 0):,}",
        "video_a_likes": f"{a.get('likes', 0):,}",
        "video_a_comments": f"{a.get('comments', 0):,}",
        "video_a_engagement": a.get("engagement_rate", 0.0),
        "video_a_duration": a.get("duration_seconds", 0),
        "video_a_followers": (
            f"{a.get('follower_count', 0):,}"
            if isinstance(a.get("follower_count"), int)
            else "N/A"
        ),
        "video_a_date": a.get("upload_date", ""),
        "video_a_hashtags": a.get("hashtags", "none"),
        "video_b_title": b.get("title", "Video B"),
        "video_b_creator": b.get("creator", "Unknown"),
        "video_b_platform": b.get("platform", ""),
        "video_b_views": f"{b.get('views', 0):,}",
        "video_b_likes": f"{b.get('likes', 0):,}",
        "video_b_comments": f"{b.get('comments', 0):,}",
        "video_b_engagement": b.get("engagement_rate", 0.0),
        "video_b_duration": b.get("duration_seconds", 0),
        "video_b_followers": (
            f"{b.get('follower_count', 0):,}"
            if isinstance(b.get("follower_count"), int)
            else "N/A"
        ),
        "video_b_date": b.get("upload_date", ""),
        "video_b_hashtags": b.get("hashtags", "none"),
    }


async def stream_rag_response(
    question: str,
    session_id: str,
    session: dict,
) -> AsyncGenerator[str, None]:
    """
    Core RAG streaming function.
    1. Retrieve relevant chunks from ChromaDB
    2. Build prompt with metadata + chunks + history
    3. Stream GPT-4o-mini response token by token
    4. Yield citations at the end
    """
    # Guard: empty question
    if not question or not question.strip():
        yield "data: Please ask a question about the videos.\n\n"
        yield "data: [DONE]\n\n"
        return

    # Step 1 — Smart routing: filter by video if question targets one
    video_filter = None
    q_lower = question.lower()
    if "video a" in q_lower and "video b" not in q_lower:
        video_filter = "A"
    elif "video b" in q_lower and "video a" not in q_lower:
        video_filter = "B"

    retriever = get_retriever(session_id, video_filter)
    docs = retriever.invoke(question)

    # Always include hook chunks for hook-related questions
    if any(kw in q_lower for kw in ("hook", "first 5", "opening", "intro")):
        hook_retriever = get_retriever(session_id)
        all_docs = hook_retriever.vectorstore.get(
            where={
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"is_hook": {"$eq": True}},
                ]
            }
        )
        if all_docs and all_docs.get("documents"):
            existing_contents = {d.page_content for d in docs}
            for i, doc_text in enumerate(all_docs["documents"]):
                if doc_text not in existing_contents:
                    hook_doc = Document(
                        page_content=doc_text,
                        metadata=all_docs["metadatas"][i],
                    )
                    docs.insert(0, hook_doc)

    # Guard: no chunks found
    if not docs:
        yield "data: I couldn't find relevant transcript content for that question. Try rephrasing or asking about a specific video.\n\n"
        yield "data: [DONE]\n\n"
        return

    context = format_docs_with_citations(docs)
    meta = build_metadata_context(session)

    # Step 2 — Build chat history
    history_messages = []
    for turn in session.get("chat_history", []):
        history_messages.append(HumanMessage(content=turn["human"]))
        history_messages.append(AIMessage(content=turn["ai"]))

    # Step 3 — Build prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    # Step 4 — GPT-4o-mini with streaming
    # Why mini: 8x cheaper than GPT-4o, sufficient for RAG
    # where retrieved context does the heavy lifting
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,        # Low temp: factual, consistent answers
        streaming=True,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Step 5 — Format prompt and stream tokens
    full_response = ""
    prompt_value = prompt.format_messages(
        context=context,
        history=history_messages,
        question=question,
        **meta,
    )

    async for chunk in llm.astream(prompt_value):
        token = chunk.content
        if token:
            full_response += token
            yield f"data: {token}\n\n"

    # Step 6 — Yield citations as a final SSE event
    citations = [
        {
            "video_id": doc.metadata.get("video_id"),
            "chunk_index": doc.metadata.get("chunk_index"),
            "is_hook": doc.metadata.get("is_hook", False),
            "preview": doc.page_content[:100] + "...",
        }
        for doc in docs
    ]
    yield f"data: [CITATIONS]{json.dumps(citations)}\n\n"
    yield "data: [DONE]\n\n"

    # Step 7 — Update conversation memory (keep last 10 turns)
    session["chat_history"].append({
        "human": question,
        "ai": full_response,
    })
    if len(session["chat_history"]) > 10:
        session["chat_history"] = session["chat_history"][-10:]
