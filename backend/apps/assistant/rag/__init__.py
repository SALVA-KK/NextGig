"""
RAG (Retrieval-Augmented Generation) package for the NextGig AI Assistant.
"""

from apps.opportunities.embeddings import (
    OpportunityEmbedding,
    build_opportunity_document,
    compute_content_hash,
    index_opportunity,
)

__all__ = [
    "OpportunityEmbedding",
    "build_opportunity_document",
    "compute_content_hash",
    "index_opportunity",
]
