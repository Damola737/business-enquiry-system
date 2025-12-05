"""
Enhanced Retrieval Module with Hybrid Search and Reranking.

Phase 5 Implementation:
- Contextual chunking with metadata
- Hybrid search (keyword + semantic)
- Cross-encoder reranking
- Result fusion and deduplication
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Chunk:
    """
    A contextual chunk from a document.
    
    Includes metadata for better retrieval:
    - Parent document reference
    - Position in document
    - Contextual summary
    - Entity mentions
    """
    chunk_id: str
    content: str
    doc_id: str
    
    # Position metadata
    start_pos: int = 0
    end_pos: int = 0
    chunk_index: int = 0
    total_chunks: int = 1
    
    # Contextual metadata
    section_title: Optional[str] = None
    context_summary: Optional[str] = None
    
    # Entity metadata
    entities: Dict[str, List[str]] = field(default_factory=dict)
    
    # Document metadata
    domain: Optional[str] = None
    tenant_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "doc_id": self.doc_id,
            "section_title": self.section_title,
            "context_summary": self.context_summary,
            "domain": self.domain,
            "entities": self.entities,
        }


@dataclass
class RetrievalResult:
    """Result from retrieval with scoring breakdown."""
    chunk: Chunk
    
    # Scoring
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    
    # Provenance
    retrieval_method: str = "hybrid"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk": self.chunk.to_dict(),
            "scores": {
                "keyword": self.keyword_score,
                "semantic": self.semantic_score,
                "rerank": self.rerank_score,
                "final": self.final_score,
            },
            "method": self.retrieval_method,
        }


class ContextualChunker:
    """
    Intelligent document chunker with context preservation.
    
    Features:
    - Respects document structure (headings, sections)
    - Maintains context across chunks
    - Extracts entities and metadata
    - Generates contextual summaries
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 50,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_document(
        self,
        content: str,
        doc_id: str,
        domain: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Chunk]:
        """Chunk a document into contextual pieces."""
        chunks = []
        
        # Split by sections first (markdown headers)
        sections = self._split_by_sections(content)
        
        chunk_index = 0
        for section_title, section_content in sections:
            # Skip empty sections
            if len(section_content.strip()) < self.min_chunk_size:
                continue
            
            # Chunk the section
            section_chunks = self._chunk_text(section_content)
            
            for i, chunk_text in enumerate(section_chunks):
                # Generate chunk ID
                chunk_id = self._generate_chunk_id(doc_id, chunk_index)
                
                # Extract entities
                entities = self._extract_entities(chunk_text)
                
                # Generate context summary
                context_summary = self._generate_context_summary(
                    section_title, chunk_text, i, len(section_chunks)
                )
                
                chunk = Chunk(
                    chunk_id=chunk_id,
                    content=chunk_text,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    section_title=section_title,
                    context_summary=context_summary,
                    entities=entities,
                    domain=domain,
                    tenant_id=tenant_id,
                    tags=tags or [],
                )
                chunks.append(chunk)
                chunk_index += 1
        
        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _split_by_sections(self, content: str) -> List[Tuple[Optional[str], str]]:
        """Split content by markdown sections."""
        sections = []
        current_title = None
        current_content = []
        
        for line in content.split('\n'):
            # Check for markdown header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                current_title = header_match.group(2)
                current_content = []
            else:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))
        
        return sections if sections else [(None, content)]
    
    def _chunk_text(self, text: str) -> List[str]:
        """Chunk text with overlap."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            if current_length + para_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                
                # Keep last paragraph for overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-1]
                    if len(overlap_text) <= self.chunk_overlap:
                        current_chunk = [overlap_text]
                        current_length = len(overlap_text)
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(para)
            current_length += para_length
        
        # Add remaining
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _generate_chunk_id(self, doc_id: str, index: int) -> str:
        """Generate unique chunk ID."""
        data = f"{doc_id}:{index}"
        hash_suffix = hashlib.md5(data.encode()).hexdigest()[:8]
        return f"{doc_id}:chunk:{index}:{hash_suffix}"
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from chunk text."""
        entities: Dict[str, List[str]] = {
            "phone_numbers": [],
            "amounts": [],
            "networks": [],
            "discos": [],
        }
        
        # Phone numbers (Nigerian format)
        phones = re.findall(r'(?:\+?234|0)[789]\d{9}', text)
        entities["phone_numbers"] = list(set(phones))
        
        # Amounts (Naira)
        amounts = re.findall(r'₦?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|N\d+', text, re.IGNORECASE)
        entities["amounts"] = list(set(amounts))
        
        # Networks
        networks = re.findall(r'\b(MTN|Glo|Airtel|9Mobile|Etisalat)\b', text, re.IGNORECASE)
        entities["networks"] = list(set(n.upper() if n.lower() in ['mtn', 'glo'] else n.title() for n in networks))
        
        # Discos
        discos = re.findall(r'\b(IKEDC|EKEDC|AEDC|PHED|EEDC|KEDCO|BEDC|YEDC|JEDC|KAEDCO|IBEDC)\b', text, re.IGNORECASE)
        entities["discos"] = list(set(d.upper() for d in discos))
        
        return {k: v for k, v in entities.items() if v}
    
    def _generate_context_summary(
        self,
        section_title: Optional[str],
        chunk_text: str,
        chunk_num: int,
        total_in_section: int,
    ) -> str:
        """Generate a contextual summary for the chunk."""
        parts = []
        
        if section_title:
            parts.append(f"From section: {section_title}")
        
        if total_in_section > 1:
            parts.append(f"Part {chunk_num + 1} of {total_in_section}")
        
        # Add first sentence as summary
        first_sentence = chunk_text.split('.')[0].strip()
        if first_sentence and len(first_sentence) < 100:
            parts.append(f"Starts with: {first_sentence}")
        
        return " | ".join(parts) if parts else ""


class HybridRetriever:
    """
    Hybrid retrieval combining keyword and semantic search.
    
    Features:
    - BM25-style keyword matching
    - Semantic similarity (when embeddings available)
    - Score fusion with configurable weights
    - Domain/tenant filtering
    """
    
    def __init__(
        self,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
        use_semantic: bool = False,  # Set True when embeddings available
    ) -> None:
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        self.use_semantic = use_semantic
        
        # Inverted index for keyword search
        self._index: Dict[str, List[Tuple[str, float]]] = {}
        
        # Chunk storage
        self._chunks: Dict[str, Chunk] = {}
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """Add chunks to the index."""
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._index_chunk(chunk)
    
    def _index_chunk(self, chunk: Chunk) -> None:
        """Add chunk to inverted index."""
        text = chunk.content.lower()
        
        # Tokenize and count
        tokens = re.findall(r'\b\w+\b', text)
        token_counts: Dict[str, int] = {}
        for token in tokens:
            if len(token) > 2:  # Skip very short tokens
                token_counts[token] = token_counts.get(token, 0) + 1
        
        # Add to index with TF scores
        total_tokens = len(tokens) or 1
        for token, count in token_counts.items():
            tf = count / total_tokens
            if token not in self._index:
                self._index[token] = []
            self._index[token].append((chunk.chunk_id, tf))
    
    def search(
        self,
        query: str,
        limit: int = 5,
        domain: Optional[str] = None,
        tenant_id: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[RetrievalResult]:
        """
        Search for relevant chunks.
        
        Args:
            query: Search query
            limit: Maximum results to return
            domain: Optional domain filter
            tenant_id: Optional tenant filter
            min_score: Minimum score threshold
        
        Returns:
            List of RetrievalResult sorted by score
        """
        # Keyword search
        keyword_scores = self._keyword_search(query)
        
        # Semantic search (placeholder - would use embeddings)
        semantic_scores = {}
        if self.use_semantic:
            semantic_scores = self._semantic_search(query)
        
        # Fuse scores
        all_chunk_ids = set(keyword_scores.keys()) | set(semantic_scores.keys())
        results = []
        
        for chunk_id in all_chunk_ids:
            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue
            
            # Apply filters
            if domain and chunk.domain and chunk.domain.upper() != domain.upper():
                continue
            if tenant_id and chunk.tenant_id and chunk.tenant_id != tenant_id:
                continue
            
            # Calculate fused score
            kw_score = keyword_scores.get(chunk_id, 0.0)
            sem_score = semantic_scores.get(chunk_id, 0.0)
            
            if self.use_semantic:
                final_score = (
                    self.keyword_weight * kw_score +
                    self.semantic_weight * sem_score
                )
            else:
                final_score = kw_score
            
            if final_score < min_score:
                continue
            
            result = RetrievalResult(
                chunk=chunk,
                keyword_score=kw_score,
                semantic_score=sem_score,
                final_score=final_score,
                retrieval_method="hybrid" if self.use_semantic else "keyword",
            )
            results.append(result)
        
        # Sort by final score
        results.sort(key=lambda r: r.final_score, reverse=True)
        
        return results[:limit]
    
    def _keyword_search(self, query: str) -> Dict[str, float]:
        """BM25-style keyword search."""
        query_tokens = re.findall(r'\b\w+\b', query.lower())
        scores: Dict[str, float] = {}
        
        for token in query_tokens:
            if token in self._index:
                # IDF approximation
                df = len(self._index[token])
                total_docs = len(self._chunks) or 1
                idf = 1.0 + (total_docs - df + 0.5) / (df + 0.5)
                
                for chunk_id, tf in self._index[token]:
                    # BM25 score component
                    score = tf * idf
                    scores[chunk_id] = scores.get(chunk_id, 0.0) + score
        
        # Normalize
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}
        
        return scores
    
    def _semantic_search(self, query: str) -> Dict[str, float]:
        """Semantic search (placeholder for embedding-based search)."""
        # In a real implementation, this would:
        # 1. Embed the query
        # 2. Compare against pre-computed chunk embeddings
        # 3. Return cosine similarity scores
        return {}


class CrossEncoderReranker:
    """
    Cross-encoder reranking for improved relevance.
    
    Uses query-document pairs for more accurate relevance scoring.
    Falls back to heuristic scoring when no model available.
    """
    
    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name
        self._model = None  # Would load cross-encoder model
    
    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        Rerank results using cross-encoder.
        
        Args:
            query: Original query
            results: Initial retrieval results
            top_k: Number of results to return after reranking
        
        Returns:
            Reranked list of results
        """
        if not results:
            return results
        
        # Score each result
        for result in results:
            result.rerank_score = self._score_pair(query, result.chunk.content)
            # Update final score with reranking
            result.final_score = (
                0.3 * result.final_score +  # Original score
                0.7 * result.rerank_score   # Rerank score
            )
        
        # Sort by new final score
        results.sort(key=lambda r: r.final_score, reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        return results
    
    def _score_pair(self, query: str, document: str) -> float:
        """
        Score a query-document pair.
        
        Uses heuristics when no model available.
        """
        if self._model:
            # Would use model.predict([(query, document)])
            pass
        
        # Heuristic scoring
        query_lower = query.lower()
        doc_lower = document.lower()
        
        # Exact phrase match bonus
        if query_lower in doc_lower:
            return 1.0
        
        # Word overlap
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        doc_words = set(re.findall(r'\b\w+\b', doc_lower))
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & doc_words) / len(query_words)
        
        # Boost for query words appearing early in document
        early_matches = 0
        first_100_chars = doc_lower[:100]
        for word in query_words:
            if word in first_100_chars:
                early_matches += 1
        
        early_bonus = early_matches / len(query_words) * 0.2
        
        return min(1.0, overlap + early_bonus)


class EnhancedRetriever:
    """
    Complete enhanced retrieval pipeline.
    
    Combines:
    - Contextual chunking
    - Hybrid search
    - Cross-encoder reranking
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        use_semantic: bool = False,
        use_reranking: bool = True,
    ) -> None:
        self.chunker = ContextualChunker(chunk_size=chunk_size)
        self.retriever = HybridRetriever(use_semantic=use_semantic)
        self.reranker = CrossEncoderReranker() if use_reranking else None
    
    def index_document(
        self,
        content: str,
        doc_id: str,
        domain: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """Index a document for retrieval."""
        chunks = self.chunker.chunk_document(
            content=content,
            doc_id=doc_id,
            domain=domain,
            tenant_id=tenant_id,
            tags=tags,
        )
        self.retriever.add_chunks(chunks)
        return len(chunks)
    
    def search(
        self,
        query: str,
        limit: int = 5,
        domain: Optional[str] = None,
        tenant_id: Optional[str] = None,
        rerank: bool = True,
    ) -> List[RetrievalResult]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query
            limit: Maximum results
            domain: Optional domain filter
            tenant_id: Optional tenant filter
            rerank: Whether to apply reranking
        
        Returns:
            List of RetrievalResult
        """
        # Initial retrieval (get more candidates for reranking)
        initial_limit = limit * 3 if rerank and self.reranker else limit
        
        results = self.retriever.search(
            query=query,
            limit=initial_limit,
            domain=domain,
            tenant_id=tenant_id,
        )
        
        # Rerank
        if rerank and self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=limit)
        
        return results[:limit]
    
    def get_context_for_llm(
        self,
        query: str,
        limit: int = 3,
        domain: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> str:
        """
        Get formatted context for LLM consumption.
        
        Returns a formatted string suitable for inclusion in prompts.
        """
        results = self.search(query, limit=limit, domain=domain, tenant_id=tenant_id)
        
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            part = f"[Source {i}]"
            if chunk.section_title:
                part += f" ({chunk.section_title})"
            part += f"\n{chunk.content}"
            
            if chunk.entities:
                entities_str = ", ".join(
                    f"{k}: {', '.join(v)}"
                    for k, v in chunk.entities.items()
                )
                part += f"\nEntities: {entities_str}"
            
            context_parts.append(part)
        
        return "\n\n---\n\n".join(context_parts)
