"""
EcoPulse AI - RAG Knowledge Retrieval Tool
Retrieves grounded appliance efficiency guidelines, circuit specifications, and
conservation math from indexed domain literature (energy.txt and JETIR1405001.pdf).
"""

import logging
from typing import Dict, Any, Optional, List
from src.rag_indexer import rag_indexer

logger = logging.getLogger("ecopulse.rag_tool")

class RAGTool:
    def __init__(self):
        pass

    def retrieve_energy_knowledge(
        self,
        query: str,
        category: Optional[str] = "all",
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Queries the hybrid knowledge index and returns structured chunks with source citations.
        """
        results = rag_indexer.search(query=query, category=category, top_k=top_k)
        
        if not results:
            return {
                "status": "empty",
                "query": query,
                "category": category,
                "chunks": [],
                "message": "No direct knowledge chunks matched your query. Using general thermodynamic conservation principles."
            }

        formatted_chunks = []
        for r in results:
            formatted_chunks.append({
                "title": r["title"],
                "source": r["source"],
                "reference": r["reference"],
                "category": r["category"],
                "relevance_score": r["score"],
                "content": r["content"]
            })

        return {
            "status": "success",
            "query": query,
            "category": category,
            "retrieved_count": len(formatted_chunks),
            "chunks": formatted_chunks
        }

# Global singleton instance
rag_tool = RAGTool()
