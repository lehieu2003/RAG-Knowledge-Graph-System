"""
Prompt templates for extraction and generation
Production-ready with clear instructions and examples
"""

# ============ Triple Extraction (LLM-based) ============

TRIPLE_EXTRACTION_PROMPT = """You are an expert knowledge graph builder. Extract entities and relationships from the text.

**Instructions:**
1. Identify key entities (people, concepts, objects, events)
2. Identify relationships between entities
3. Each relationship should be a triple: (head entity, relation, tail entity)
4. Use clear, canonical names for entities
5. Relations should be verbs or verb phrases
6. Provide a confidence score (0.0-1.0) for each triple

**Text:**
{text}

**Output Format (JSON):**
{{
  "triples": [
    {{
      "head": "Entity 1",
      "relation": "relation_type",
      "tail": "Entity 2",
      "confidence": 0.9,
      "span": "original text span that supports this triple"
    }}
  ]
}}

Respond with valid JSON only."""


# ============ Question Answering with Grounding ============

QA_WITH_EVIDENCE_PROMPT = """You are a helpful research assistant. Answer the question using ONLY the provided evidence.

**Question:**
{question}

**Evidence:**
{evidence_blocks}

**Instructions:**
1. Answer the question based ONLY on the evidence provided
2. Do not use external knowledge
3. If evidence is insufficient, say "I cannot answer based on the provided evidence"
4. Cite which evidence pieces you used by referencing their IDs (e.g., [E1], [E2])
5. Be concise and factual

**Output Format (JSON):**
{{
  "answer": "Your answer here with citations [E1][E2]",
  "evidence_used": ["E1", "E2"],
  "confidence": 0.85
}}

Respond with valid JSON only."""


def build_evidence_blocks(evidence_list) -> str:
    """
    Build evidence blocks for QA prompt
    Format: [E1] Page 5: <text>
    """
    blocks = []
    for i, evidence in enumerate(evidence_list, start=1):
        eid = f"E{i}"
        page_info = f"Page {evidence.page_start}"
        if evidence.page_end != evidence.page_start:
            page_info += f"-{evidence.page_end}"
        
        block = f"[{eid}] {page_info}:\n{evidence.snippet}"
        blocks.append(block)
    
    return "\n\n".join(blocks)


# ============ Entity Canonicalization (optional LLM-based) ============

ENTITY_CANONICALIZATION_PROMPT = """You are an entity resolution expert. Given a list of entity names, group them into canonical clusters.

**Entity Names:**
{entity_names}

**Instructions:**
1. Group similar entities that refer to the same real-world concept
2. Choose the best canonical name for each group
3. Handle variations, abbreviations, typos

**Output Format (JSON):**
{{
  "clusters": [
    {{
      "canonical": "Canonical Name",
      "members": ["variation 1", "variation 2"]
    }}
  ]
}}

Respond with valid JSON only."""


# ============ Graph-based Answer Generation ============

GRAPH_QA_PROMPT = """You are a research assistant specializing in knowledge graphs. Answer the question using the graph paths provided.

**Question:**
{question}

**Graph Paths:**
{graph_paths}

**Additional Context:**
{text_evidence}

**Instructions:**
1. Synthesize information from the graph paths and context
2. Use the relationships and entities to build a coherent answer
3. Reference source documents with [DocID, Page X]
4. Be precise about relationships and connections

**Output Format (JSON):**
{{
  "answer": "Your answer with document citations",
  "evidence_used": ["path_1", "doc_2_chunk_5"],
  "confidence": 0.9
}}

Respond with valid JSON only."""


def build_graph_paths_text(paths) -> str:
    """Format graph paths for prompt"""
    path_texts = []
    
    for i, path in enumerate(paths, start=1):
        entities_str = " -> ".join(path.entities)
        relations_str = " -> ".join(path.relations)
        
        prov_str = ", ".join([
            f"Doc {p['doc_id']} Page {p['page_start']}"
            for p in path.provenance[:3]  # limit provenance
        ])
        
        path_text = f"Path {i} (confidence: {path.confidence:.2f}):\n"
        path_text += f"  Entities: {entities_str}\n"
        path_text += f"  Relations: {relations_str}\n"
        path_text += f"  Sources: {prov_str}"
        
        path_texts.append(path_text)
    
    return "\n\n".join(path_texts)
