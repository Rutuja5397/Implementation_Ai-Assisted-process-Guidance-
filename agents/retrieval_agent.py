"""
AGT-03: Retrieval Agent

Queries ChromaDB with a two-stage strategy:
  1. Component-filtered query  → top 3 chunks for the selected component
  2. General corpus query      → top 2 chunks from the full collection
Deduplicates and returns up to 5 ranked evidence chunks.
"""

from typing import Any, Optional
from agents.base_agent import BaseAgent
from backend.rag_system import RAGSystem

# Singleton — RAG system is expensive to initialise (loads embedding model)
_rag_instance: Optional[RAGSystem] = None


def _get_rag() -> RAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystem()
        _rag_instance.initialize()
    return _rag_instance


class RetrievalAgent(BaseAgent):
    AGT_ID = "AGT-03"

    N_COMPONENT = 3   # chunks from component-specific query
    N_GENERAL   = 2   # chunks from general query
    N_TOTAL     = 5   # max chunks returned

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          component_key: str     (component name for ChromaDB filter)
          query_terms:   str     (combined search query)

        Output:
          evidence_chunks: list[dict]   (ranked, deduplicated)
          knowledge_gap_indicator: bool (True if 0 component chunks found)
          retrieval_metadata: dict
        """
        component_key: str = payload.get("component_key", "")
        query_terms:   str = payload.get("query_terms", "")

        if not query_terms.strip():
            return {
                "evidence_chunks": [],
                "knowledge_gap_indicator": True,
                "retrieval_metadata": {"query_used": "", "chunks_returned": 0},
            }

        rag = _get_rag()
        chunks = rag.retrieve(
            query=query_terms,
            component=component_key if component_key else None,
            n_results=self.N_TOTAL,
        )

        # Flag knowledge gap if component-filtered retrieval produced nothing
        component_chunks = [c for c in chunks
                            if c.get("component", "").lower() in component_key.lower()
                            or component_key.lower() in c.get("component", "").lower()]
        gap = len(component_chunks) == 0 and bool(component_key)

        return {
            "evidence_chunks": chunks,
            "knowledge_gap_indicator": gap,
            "retrieval_metadata": {
                "query_used": query_terms,
                "chunks_returned": len(chunks),
                "component_filtered_count": len(component_chunks),
            },
        }
