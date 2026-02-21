"""
Extraction Service - Hybrid triple extraction
REBEL (supervised) + LLM (zero-shot) with pooling
"""
from typing import List, Dict, Any
import re

from transformers import pipeline

from app.domain.models import Triple, ExtractorType, Chunk
from app.domain.ports import LLMClient
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import ExtractionError
from app.llm.prompts import TRIPLE_EXTRACTION_PROMPT

logger = get_logger(__name__)
settings = get_settings()


class ExtractionService:
    """Hybrid extraction: REBEL + LLM"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.rebel_extractor = None  # Lazy load
    
    def _load_rebel(self):
        """Lazy load REBEL model"""
        if self.rebel_extractor is None:
            logger.info("loading_rebel_model", model=settings.rebel_model)
            self.rebel_extractor = pipeline(
                "text2text-generation",
                model=settings.rebel_model,
                device=settings.rebel_device
            )
            logger.info("rebel_model_loaded")
    
    async def extract_triples_hybrid(
        self,
        chunks: List[Chunk],
        doc_id: str,
        use_rebel: bool = True,
        use_llm: bool = True
    ) -> List[Triple]:
        """
        Hybrid extraction: combine REBEL and LLM
        
        Returns:
            Union of triples from both extractors with provenance
        """
        all_triples = []
        
        # REBEL extraction (supervised)
        if use_rebel:
            try:
                logger.info("rebel_extraction_started", chunks=len(chunks), doc_id=doc_id)
                rebel_triples = await self._extract_with_rebel(chunks, doc_id)
                all_triples.extend(rebel_triples)
                logger.info("rebel_extraction_completed", triples=len(rebel_triples))
            except Exception as e:
                logger.error("rebel_extraction_failed", error=str(e))
                # Continue with LLM if REBEL fails
        
        # LLM extraction (zero-shot)
        if use_llm:
            try:
                logger.info("llm_extraction_started", chunks=len(chunks), doc_id=doc_id)
                llm_triples = await self._extract_with_llm(chunks, doc_id)
                all_triples.extend(llm_triples)
                logger.info("llm_extraction_completed", triples=len(llm_triples))
            except Exception as e:
                logger.error("llm_extraction_failed", error=str(e))
        
        # Deduplicate by fingerprint
        unique_triples = self._deduplicate_triples(all_triples)
        
        logger.info("hybrid_extraction_completed", total=len(unique_triples), doc_id=doc_id)
        return unique_triples
    
    async def _extract_with_rebel(self, chunks: List[Chunk], doc_id: str) -> List[Triple]:
        """Extract triples using REBEL model"""
        self._load_rebel()
        
        triples = []
        
        for chunk in chunks:
            try:
                # REBEL expects shorter text
                text = chunk.text[:512]
                
                # Run extraction
                outputs = self.rebel_extractor(text, max_length=256)
                
                # Parse REBEL output format: "head <relation> tail"
                for output in outputs:
                    generated = output.get("generated_text", "")
                    parsed = self._parse_rebel_output(generated)
                    
                    for head, relation, tail in parsed:
                        triples.append(Triple(
                            head=head,
                            relation=relation,
                            tail=tail,
                            confidence=0.8,  # REBEL baseline confidence
                            extractor=ExtractorType.REBEL,
                            doc_id=doc_id,
                            chunk_id=chunk.id,
                            page_start=chunk.page_start,
                            page_end=chunk.page_end,
                            span=None,
                        ))
            except Exception as e:
                logger.warning("rebel_chunk_extraction_failed", chunk_id=chunk.id, error=str(e))
                continue
        
        return triples
    
    async def _extract_with_llm(self, chunks: List[Chunk], doc_id: str) -> List[Triple]:
        """Extract triples using LLM"""
        triples = []
        
        for chunk in chunks:
            try:
                # Build prompt
                prompt = TRIPLE_EXTRACTION_PROMPT.format(text=chunk.text)
                
                # Call LLM
                response = await self.llm_client.extract_structured(
                    prompt,
                    schema={"triples": "list"}
                )
                
                # Parse response
                for triple_data in response.get("triples", []):
                    triples.append(Triple(
                        head=triple_data["head"],
                        relation=triple_data["relation"],
                        tail=triple_data["tail"],
                        confidence=triple_data.get("confidence", 0.7),
                        extractor=ExtractorType.LLM,
                        doc_id=doc_id,
                        chunk_id=chunk.id,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        span=triple_data.get("span"),
                    ))
            except Exception as e:
                logger.warning("llm_chunk_extraction_failed", chunk_id=chunk.id, error=str(e))
                continue
        
        return triples
    
    def _parse_rebel_output(self, text: str) -> List[tuple]:
        """
        Parse REBEL output format
        Format: "head <relation> tail | head2 <relation2> tail2"
        """
        triples = []
        
        # Split by |
        parts = text.split("|")
        
        for part in parts:
            # Match pattern: entity1 <relation> entity2
            match = re.search(r'(.+?)\s*<(.+?)>\s*(.+)', part.strip())
            if match:
                head, relation, tail = match.groups()
                triples.append((
                    head.strip(),
                    relation.strip(),
                    tail.strip()
                ))
        
        return triples
    
    def _deduplicate_triples(self, triples: List[Triple]) -> List[Triple]:
        """Deduplicate triples by fingerprint"""
        seen = set()
        unique = []
        
        for triple in triples:
            fp = triple.fingerprint()
            if fp not in seen:
                seen.add(fp)
                unique.append(triple)
        
        return unique
