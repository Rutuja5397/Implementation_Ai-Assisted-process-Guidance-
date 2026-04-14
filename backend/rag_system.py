"""
RAG System: loads crane maintenance knowledge base into ChromaDB,
then retrieves relevant chunks for a given query.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Component → file mapping
COMPONENT_FILE_MAP = {
    "Hoist Motor":      "hoist_motor.txt",
    "Hoist Brake":      "hoist_brake.txt",
    "Wire Rope":        "wire_rope.txt",
    "Hook Block":       "hook_block.txt",
    "Trolley Motor":    "trolley_bridge_motor.txt",
    "Bridge Motor":     "trolley_bridge_motor.txt",
    "Gearbox":          "gearbox.txt",
    "Limit Switch":     "limit_switch.txt",
    "Control System":   "control_system.txt",
    "Power Supply":     "power_supply.txt",
}


class RAGSystem:
    """Manages the ChromaDB vector store and retrieval pipeline."""

    COLLECTION_NAME = "crane_knowledge"
    CHUNK_SIZE = 500      # characters per chunk
    CHUNK_OVERLAP = 100

    def __init__(self):
        chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
        kb_path = os.getenv("KNOWLEDGE_BASE_PATH", "./data/knowledge_base")

        self.kb_path = Path(kb_path)
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        # Embedding model (small, fast, good quality)
        logger.info("Loading embedding model...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        # ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )

    def initialize(self):
        """Load all knowledge base documents into ChromaDB (idempotent)."""
        collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        # Check if already populated
        existing = collection.count()
        if existing > 0:
            logger.info(f"Knowledge base already loaded ({existing} chunks). Skipping.")
            return

        logger.info("Indexing knowledge base...")
        all_docs, all_ids, all_metas, all_embeds = [], [], [], []
        doc_idx = 0

        for txt_file in self.kb_path.glob("*.txt"):
            component = self._filename_to_component(txt_file.stem)
            raw_text = txt_file.read_text(encoding="utf-8")
            chunks = self._chunk_text(raw_text)

            for chunk in chunks:
                chunk_id = f"doc_{doc_idx}"
                embedding = self.embedder.encode(chunk).tolist()

                all_docs.append(chunk)
                all_ids.append(chunk_id)
                all_metas.append({
                    "source": txt_file.name,
                    "component": component,
                })
                all_embeds.append(embedding)
                doc_idx += 1

        if all_docs:
            # ChromaDB has a max batch size; upsert in batches of 100
            batch_size = 100
            for i in range(0, len(all_docs), batch_size):
                collection.upsert(
                    documents=all_docs[i:i+batch_size],
                    ids=all_ids[i:i+batch_size],
                    metadatas=all_metas[i:i+batch_size],
                    embeddings=all_embeds[i:i+batch_size],
                )
            logger.info(f"Indexed {doc_idx} chunks into ChromaDB.")

    def retrieve(
        self,
        query: str,
        component: str = None,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-n relevant chunks for a query.
        Optionally filter by component to get more targeted results.
        """
        collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        if collection.count() == 0:
            self.initialize()

        query_embedding = self.embedder.encode(query).tolist()

        # First: component-specific retrieval (if component given)
        results_list = []

        if component and component in COMPONENT_FILE_MAP:
            source_file = COMPONENT_FILE_MAP[component]
            try:
                component_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(3, n_results),
                    where={"source": source_file},
                )
                results_list.extend(
                    self._format_results(component_results)
                )
            except Exception:
                pass  # Filter may fail if no docs match; fall through

        # Then: general retrieval (broader context)
        remaining = n_results - len(results_list)
        if remaining > 0:
            general_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=remaining + len(results_list),  # over-fetch to de-dup
            )
            for r in self._format_results(general_results):
                if r["id"] not in {x["id"] for x in results_list}:
                    results_list.append(r)
                    if len(results_list) >= n_results:
                        break

        return results_list[:n_results]

    def _format_results(self, query_result: dict) -> List[Dict[str, Any]]:
        formatted = []
        if not query_result["documents"] or not query_result["documents"][0]:
            return formatted

        for doc, meta, dist, doc_id in zip(
            query_result["documents"][0],
            query_result["metadatas"][0],
            query_result["distances"][0],
            query_result["ids"][0],
        ):
            formatted.append({
                "id": doc_id,
                "content": doc,
                "component": meta.get("component", "General"),
                "source": meta.get("source", "unknown"),
                "relevance_score": round(1 - dist, 3),  # cosine similarity
            })
        return formatted

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        # Split on double newlines first (paragraphs/sections)
        paragraphs = re.split(r"\n\n+", text)
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) < self.CHUNK_SIZE:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                # Start new chunk with overlap from previous
                overlap_start = max(0, len(current) - self.CHUNK_OVERLAP)
                current = current[overlap_start:] + "\n\n" + para if current else para

        if current:
            chunks.append(current)

        return [c for c in chunks if len(c) > 50]

    def _filename_to_component(self, stem: str) -> str:
        mapping = {
            "hoist_motor": "Hoist Motor",
            "hoist_brake": "Hoist Brake",
            "wire_rope": "Wire Rope",
            "hook_block": "Hook Block",
            "trolley_bridge_motor": "Trolley/Bridge Motor",
            "gearbox": "Gearbox",
            "limit_switch": "Limit Switch",
            "control_system": "Control System",
            "power_supply": "Power Supply",
            "general_procedures": "General",
        }
        return mapping.get(stem, stem.replace("_", " ").title())
