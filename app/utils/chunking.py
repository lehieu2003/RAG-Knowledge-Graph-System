"""
Text chunking utilities with overlap and page tracking
Production-ready with hash-based deduplication
"""
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkResult:
    """Chunk with metadata"""
    text: str
    page_start: int
    page_end: int
    position: int
    chunk_hash: str


def chunk_text_by_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[ChunkResult]:
    """
    Chunk text with page tracking and overlap
    
    Strategy:
    - Concatenate pages with page markers
    - Sliding window chunking
    - Track which pages each chunk spans
    
    Args:
        pages: List of {"page_num": int, "text": str}
        chunk_size: Target chunk size in tokens (approx)
        chunk_overlap: Overlap size
    
    Returns:
        List of ChunkResult with page_start/page_end
    """
    chunks = []
    
    # Build continuous text with page boundaries
    page_texts = []
    page_boundaries = [0]  # character positions where pages start
    current_pos = 0
    
    for page in pages:
        if not page["text"]:
            continue
        text = page["text"]
        page_texts.append(text)
        current_pos += len(text) + 2  # +2 for "\n\n"
        page_boundaries.append(current_pos)
    
    if not page_texts:
        return []
    
    full_text = "\n\n".join(page_texts)
    
    # Simple word-based chunking (can upgrade to token-based)
    words = full_text.split()
    
    position = 0
    start_idx = 0
    
    while start_idx < len(words):
        end_idx = min(start_idx + chunk_size, len(words))
        chunk_words = words[start_idx:end_idx]
        chunk_text = " ".join(chunk_words)
        
        # Find character span
        char_start = len(" ".join(words[:start_idx]))
        if start_idx > 0:
            char_start += 1  # space before
        char_end = char_start + len(chunk_text)
        
        # Determine page range
        page_start = _find_page_for_position(char_start, page_boundaries, pages)
        page_end = _find_page_for_position(char_end, page_boundaries, pages)
        
        # Generate chunk hash (for idempotency)
        chunk_hash = _generate_chunk_hash(chunk_text, page_start, page_end, position)
        
        chunks.append(ChunkResult(
            text=chunk_text,
            page_start=page_start,
            page_end=page_end,
            position=position,
            chunk_hash=chunk_hash,
        ))
        
        position += 1
        start_idx += (chunk_size - chunk_overlap)
    
    logger.info("text_chunked", chunks=len(chunks), chunk_size=chunk_size)
    return chunks


def _find_page_for_position(
    char_pos: int,
    page_boundaries: List[int],
    pages: List[Dict[str, Any]]
) -> int:
    """Find which page a character position belongs to"""
    for i in range(len(page_boundaries) - 1):
        if page_boundaries[i] <= char_pos < page_boundaries[i + 1]:
            # Return the actual page number from pages list
            return pages[i]["page_num"] if i < len(pages) else pages[-1]["page_num"]
    return pages[-1]["page_num"] if pages else 1


def _generate_chunk_hash(text: str, page_start: int, page_end: int, position: int) -> str:
    """Generate deterministic hash for chunk (for deduplication)"""
    content = f"{text}|{page_start}|{page_end}|{position}"
    return hashlib.sha256(content.encode()).hexdigest()
