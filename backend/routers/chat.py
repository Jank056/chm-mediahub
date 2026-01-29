"""Chat router - proxies requests to the chatbot API with auth."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from middleware.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])

# Chatbot API URL (existing deployment)
import os
CHATBOT_API_URL = os.getenv("CHATBOT_API_URL", "http://host.docker.internal:8000")


class ChatQuery(BaseModel):
    """Chat query request."""
    query: str
    top_k: int = 5


class ChatResponse(BaseModel):
    """Chat response from the chatbot."""
    answer: str
    sources: list[dict] | None = None


class ChunkSearchRequest(BaseModel):
    """Direct chunk search request."""
    query: str
    top_k: int = 10
    source_type_filter: str | None = None  # "audio", "pdf", "chm_video"


class ChunkMetadata(BaseModel):
    """Metadata for a chunk."""
    source_type: str
    title: str | None = None
    doctors: str | None = None
    date: str | None = None
    url: str | None = None
    youtube_url: str | None = None
    thumbnail_url: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    summary: str | None = None


class ChunkResult(BaseModel):
    """A single chunk search result."""
    id: str
    text: str
    distance: float
    metadata: ChunkMetadata


class ChunkSearchResponse(BaseModel):
    """Response from chunk search."""
    chunks: list[ChunkResult]
    total_indexed: int
    query_time_ms: float


class SourceInfo(BaseModel):
    """Information about a content source."""
    id: str
    source_type: str
    title: str
    doctors: str | None = None
    youtube_url: str | None = None
    thumbnail_url: str | None = None
    url: str | None = None
    chunk_count: int
    date: str | None = None


class SourcesResponse(BaseModel):
    """Response containing all content sources."""
    sources: list[SourceInfo]
    totals: dict[str, int]


class SourceChunk(BaseModel):
    """A chunk belonging to a source."""
    id: str
    text: str
    start_time: float | None = None
    end_time: float | None = None
    page_num: int | None = None


class SourceChunksResponse(BaseModel):
    """Response containing chunks for a source."""
    source_id: str
    chunks: list[SourceChunk]
    count: int


class ChunkPosition(BaseModel):
    """Position of a chunk within the full document text."""
    id: str
    start_char: int
    end_char: int
    start_time: float | None = None
    end_time: float | None = None
    page_num: int | None = None


class SourceFullTextResponse(BaseModel):
    """Response containing the full reconstructed document text."""
    source_id: str
    full_text: str
    chunk_positions: list[ChunkPosition]
    chunk_count: int
    source_type: str | None = None
    title: str | None = None
    doctors: str | None = None
    youtube_url: str | None = None


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatQuery,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Send a query to the chatbot API."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CHATBOT_API_URL}/query",
                json={"query": request.query, "top_k": request.top_k},
            )
            if response.status_code == 200:
                data = response.json()
                return ChatResponse(
                    answer=data.get("answer", ""),
                    sources=data.get("sources"),
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Chatbot API error"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chatbot API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Chatbot API unavailable: {str(e)}")


@router.get("/health")
async def chat_health(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Check chatbot API health."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CHATBOT_API_URL}/health")
            if response.status_code == 200:
                return {"status": "healthy", "chatbot_api": CHATBOT_API_URL}
            return {"status": "unhealthy", "error": "Non-200 response"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/pdfs")
async def list_pdfs(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List available PDFs from the chatbot library."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CHATBOT_API_URL}/pdfs")
            if response.status_code == 200:
                return response.json()
            return {"pdfs": []}
    except Exception:
        return {"pdfs": []}


@router.post("/search/chunks", response_model=ChunkSearchResponse)
async def search_chunks(
    request: ChunkSearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Direct chunk search without LLM processing.

    Search the indexed content chunks directly and return results with full metadata.
    Useful for exploring the knowledge base and debugging.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "query": request.query,
                "top_k": request.top_k,
            }
            if request.source_type_filter:
                payload["source_type_filter"] = request.source_type_filter

            response = await client.post(
                f"{CHATBOT_API_URL}/search/chunks",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return ChunkSearchResponse(
                    chunks=[
                        ChunkResult(
                            id=chunk["id"],
                            text=chunk["text"],
                            distance=chunk["distance"],
                            metadata=ChunkMetadata(**chunk["metadata"]),
                        )
                        for chunk in data.get("chunks", [])
                    ],
                    total_indexed=data.get("total_indexed", 0),
                    query_time_ms=data.get("query_time_ms", 0),
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Chatbot API error"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chatbot API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Chatbot API unavailable: {str(e)}")


@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    List all content sources in the knowledge base.

    Returns aggregated source-level information for browsing the content library.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{CHATBOT_API_URL}/sources")

            if response.status_code == 200:
                data = response.json()
                return SourcesResponse(
                    sources=[
                        SourceInfo(**source)
                        for source in data.get("sources", [])
                    ],
                    totals=data.get("totals", {}),
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Chatbot API error"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chatbot API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Chatbot API unavailable: {str(e)}")


@router.get("/sources/{source_id:path}/chunks", response_model=SourceChunksResponse)
async def get_source_chunks(
    source_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get all chunks for a specific source.

    Returns chunks belonging to the source, ordered by timestamp/page.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # URL encode the source_id since it may contain special chars
            import urllib.parse
            encoded_id = urllib.parse.quote(source_id, safe="")
            response = await client.get(
                f"{CHATBOT_API_URL}/sources/{encoded_id}/chunks"
            )

            if response.status_code == 200:
                data = response.json()
                return SourceChunksResponse(
                    source_id=data.get("source_id", source_id),
                    chunks=[
                        SourceChunk(**chunk)
                        for chunk in data.get("chunks", [])
                    ],
                    count=data.get("count", 0),
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Chatbot API error"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chatbot API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Chatbot API unavailable: {str(e)}")


@router.get("/sources/{source_id:path}/full", response_model=SourceFullTextResponse)
async def get_source_full_text(
    source_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get the full reconstructed document text for a source.

    Fetches all chunks and joins them in order (by timestamp for audio,
    by page number for PDFs) to create a readable continuous document.
    Also returns chunk positions for optional highlighting overlay.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            import urllib.parse
            encoded_id = urllib.parse.quote(source_id, safe="")

            # Fetch chunks from chatbot API
            chunks_response = await client.get(
                f"{CHATBOT_API_URL}/sources/{encoded_id}/chunks"
            )

            if chunks_response.status_code != 200:
                raise HTTPException(
                    status_code=chunks_response.status_code,
                    detail="Failed to fetch source chunks"
                )

            chunks_data = chunks_response.json()
            chunks = chunks_data.get("chunks", [])

            # Also fetch source metadata
            sources_response = await client.get(f"{CHATBOT_API_URL}/sources")
            source_meta = None
            if sources_response.status_code == 200:
                sources_data = sources_response.json()
                for src in sources_data.get("sources", []):
                    if src.get("id") == source_id:
                        source_meta = src
                        break

            # Sort chunks by timestamp (audio) or page number (pdf)
            sorted_chunks = sorted(
                chunks,
                key=lambda c: c.get("start_time") or c.get("page_num") or 0
            )

            # Merge chunks by removing overlapping text between consecutive chunks
            # RAG chunking often includes overlap for context preservation
            def find_overlap(prev_text: str, curr_text: str, max_overlap: int = 300) -> int:
                """Find how many chars of prev_text's end appear at curr_text's start."""
                if not prev_text or not curr_text:
                    return 0
                # Check decreasing overlap sizes to find the longest match
                for overlap_size in range(min(max_overlap, len(prev_text), len(curr_text)), 20, -10):
                    if prev_text[-overlap_size:] == curr_text[:overlap_size]:
                        return overlap_size
                # Try smaller increments for precise match
                for overlap_size in range(min(200, len(prev_text), len(curr_text)), 0, -1):
                    if prev_text[-overlap_size:] == curr_text[:overlap_size]:
                        return overlap_size
                return 0

            # Build merged text by removing overlaps
            full_text_parts = []
            chunk_positions = []
            current_pos = 0
            prev_text = ""

            for chunk in sorted_chunks:
                chunk_text = chunk.get("text", "")

                # Find and remove overlap with previous chunk
                if prev_text:
                    overlap = find_overlap(prev_text, chunk_text)
                    if overlap > 0:
                        chunk_text = chunk_text[overlap:]  # Remove overlapping prefix

                if not chunk_text.strip():
                    continue  # Skip if nothing left after removing overlap

                chunk_len = len(chunk_text)

                chunk_positions.append(ChunkPosition(
                    id=chunk.get("id", ""),
                    start_char=current_pos,
                    end_char=current_pos + chunk_len,
                    start_time=chunk.get("start_time"),
                    end_time=chunk.get("end_time"),
                    page_num=chunk.get("page_num"),
                ))

                full_text_parts.append(chunk_text)
                current_pos += chunk_len + 1  # +1 for single space separator
                prev_text = chunk.get("text", "")  # Keep original for overlap detection

            # Join with single space for continuous reading
            full_text = " ".join(full_text_parts)

            return SourceFullTextResponse(
                source_id=source_id,
                full_text=full_text,
                chunk_positions=chunk_positions,
                chunk_count=len(sorted_chunks),
                source_type=source_meta.get("source_type") if source_meta else None,
                title=source_meta.get("title") if source_meta else None,
                doctors=source_meta.get("doctors") if source_meta else None,
                youtube_url=source_meta.get("youtube_url") if source_meta else None,
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chatbot API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Chatbot API unavailable: {str(e)}")
