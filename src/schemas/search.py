"""
Search Pydantic Schemas
"""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result schema"""

    chunk_id: str
    metadata_id: str
    chunk_text: str
    score: float
    section: str | None


class HybridSearchResponse(BaseModel):
    """Hybrid search response schema"""

    query: str
    results: list[SearchResult]
    total_results: int
    search_time_ms: float
