"""
PDF text extraction utilities
Robust extraction with page tracking
"""
import io
from typing import List, Dict, Any
from pathlib import Path
import pypdf
import pdfplumber

from app.core.logging import get_logger
from app.core.exceptions import InvalidDocumentError

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract text from PDF with page-level granularity
    
    Returns:
        {
            "pages": [{"page_num": 1, "text": "..."}],
            "full_text": "...",
            "metadata": {...}
        }
    """
    try:
        pages = []
        
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({
                    "page_num": i,
                    "text": text.strip()
                })
            
            # Get metadata
            metadata = {
                "page_count": len(pdf.pages),
                "metadata": pdf.metadata or {}
            }
        
        full_text = "\n\n".join(p["text"] for p in pages if p["text"])
        
        logger.info("pdf_extracted", pages=len(pages), file=file_path)
        
        return {
            "pages": pages,
            "full_text": full_text,
            "metadata": metadata
        }
    
    except Exception as e:
        logger.error("pdf_extraction_failed", file=file_path, error=str(e))
        raise InvalidDocumentError(f"PDF extraction failed: {e}")


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Extract text from PDF bytes"""
    try:
        pages = []
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({
                    "page_num": i,
                    "text": text.strip()
                })
            
            metadata = {
                "page_count": len(pdf.pages),
                "metadata": pdf.metadata or {}
            }
        
        full_text = "\n\n".join(p["text"] for p in pages if p["text"])
        
        logger.info("pdf_extracted_from_bytes", pages=len(pages), filename=filename)
        
        return {
            "pages": pages,
            "full_text": full_text,
            "metadata": metadata
        }
    
    except Exception as e:
        logger.error("pdf_extraction_failed", filename=filename, error=str(e))
        raise InvalidDocumentError(f"PDF extraction failed: {e}")


def validate_pdf(file_bytes: bytes) -> bool:
    """Validate that bytes represent a valid PDF"""
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return len(pdf_reader.pages) > 0
    except Exception:
        return False
