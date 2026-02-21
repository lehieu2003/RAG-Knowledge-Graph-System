"""
Text processing utilities
"""
import re
from typing import List


def normalize_text(text: str) -> str:
    """Normalize text for processing"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip
    text = text.strip()
    return text


def normalize_entity_name(name: str) -> str:
    """Normalize entity name for canonicalization"""
    # Lowercase
    name = name.lower()
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def split_into_sentences(text: str) -> List[str]:
    """Simple sentence splitter"""
    # Basic split on .!?
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def compute_text_similarity(text1: str, text2: str) -> float:
    """Simple Jaccard similarity for text"""
    set1 = set(text1.lower().split())
    set2 = set(text2.lower().split())
    
    if not set1 or not set2:
        return 0.0
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union)
