import os
import time
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from tenacity import retry, stop_after_attempt, wait_exponential

class RetryingGoogleEmbeddings(Embeddings):
    """
    Wrapper around GoogleGenerativeAIEmbeddings to support automatic retrying
    with exponential backoff on rate limits (429s), and batching of requests
    with a small delay to respect Google AI Studio free tier limits.
    """
    def __init__(self, google_api_key: str):
        self.underlying = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=google_api_key
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        batch_size = 5
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self._embed_batch_with_retry(batch)
            results.extend(batch_embeddings)
            if i + batch_size < len(texts):
                time.sleep(1.0)  # Rate limiting safety sleep
        return results

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True
    )
    def _embed_batch_with_retry(self, batch: List[str]) -> List[List[float]]:
        return self.underlying.embed_documents(batch)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True
    )
    def embed_query(self, text: str) -> List[float]:
        return self.underlying.embed_query(text)

# Persistent ChromaDB directory — survives server restarts
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "../../.chroma")

def get_embeddings():
    """
    Get embeddings model. Dynamic fallback/routing to:
    1. Local CPU (sentence-transformers) by default, or if EMBEDDING_PROVIDER is set to local.
    2. Gemini (Google AI Studio) if EMBEDDING_PROVIDER is set to gemini.
    3. OpenAI if EMBEDDING_PROVIDER is set to openai.
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "local")
    
    if provider == "openai":
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    elif provider == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY")
        return RetryingGoogleEmbeddings(gemini_key)
    else:
        # Default to 100% local, high-performance, unlimited CPU embeddings
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_chroma_dir() -> str:
    """Return separate directory for different providers to avoid vector dimension clashes."""
    provider = os.getenv("EMBEDDING_PROVIDER", "local")
    return os.path.join(CHROMA_DIR, provider)

def get_vectorstore() -> Chroma:
    """Return persistent ChromaDB vectorstore."""
    return Chroma(
        collection_name="creator_videos",
        embedding_function=get_embeddings(),
        persist_directory=get_chroma_dir()
    )

def chunk_transcript(
    transcript: dict,
    video_label: str,       # "A" or "B"
    metadata: dict
) -> List[Document]:
    """
    Split transcript into chunks and wrap each as a LangChain Document.

    Chunk size: 300 tokens
    Overlap: 50 tokens

    Why 300/50?
    - Small enough to be semantically focused (one idea per chunk)
    - Large enough to have context (not single sentences)
    - Overlap prevents cutting a key idea at a boundary
    - At 1000 creators/day: ~20 chunks per video × 2 videos = 40 chunks
      per creator. ChromaDB handles 10M+ chunks on a single node.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_text(transcript["full_text"])

    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                # Required for filtering in RAG queries
                "video_id": video_label,           # "A" or "B"
                "video_url": metadata.get("url", ""),
                "platform": metadata.get("platform", ""),
                "creator": metadata.get("creator", ""),
                "views": metadata.get("views", 0),
                "likes": metadata.get("likes", 0),
                "comments": metadata.get("comments", 0),
                "engagement_rate": metadata.get("engagement_rate", 0.0),
                "follower_count": metadata.get("follower_count", 0) or 0,
                "duration_seconds": metadata.get("duration_seconds", 0),
                "upload_date": metadata.get("upload_date", ""),
                "hashtags": ", ".join(metadata.get("hashtags", [])),
                "title": metadata.get("title", ""),
                "chunk_index": i,
                "total_chunks": len(chunks),
                # Store first chunk separately — used for hook comparison
                "is_hook": i == 0,
            }
        )
        documents.append(doc)

    return documents

def embed_and_store(
    transcript: dict,
    metadata: dict,
    video_label: str,
    session_id: str
) -> dict:
    """
    Chunk, embed, and store a video's transcript in ChromaDB.
    Tags every chunk with session_id so multiple users don't collide.
    """
    documents = chunk_transcript(transcript, video_label, metadata)

    # Add session_id to every chunk for isolation between users
    for doc in documents:
        doc.metadata["session_id"] = session_id

    vectorstore = get_vectorstore()
    vectorstore.add_documents(documents)

    return {
        "video_label": video_label,
        "chunks_stored": len(documents),
        "video_id": transcript["video_id"],
        "title": metadata.get("title", ""),
    }

def get_retriever(session_id: str, video_filter: str = None):
    """
    Return a retriever scoped to a specific session.
    Optionally filter to a single video (A or B).

    k=4: retrieve 4 chunks per query — enough context without
    overwhelming the LLM context window.
    """
    vectorstore = get_vectorstore()

    # Build filter dict for ChromaDB
    where_filter = {"session_id": {"$eq": session_id}}
    if video_filter:
        where_filter = {
            "$and": [
                {"session_id": {"$eq": session_id}},
                {"video_id": {"$eq": video_filter}}
            ]
        }

    return vectorstore.as_retriever(
        search_type="mmr",          # Max Marginal Relevance — avoids duplicate chunks
        search_kwargs={
            "k": 4,
            "fetch_k": 20,          # Fetch 20, re-rank to top 4
            "filter": where_filter
        }
    )

def delete_session_chunks(session_id: str):
    """Clean up a session's chunks after use — important for cost at scale."""
    vectorstore = get_vectorstore()
    vectorstore._collection.delete(
        where={"session_id": {"$eq": session_id}}
    )
