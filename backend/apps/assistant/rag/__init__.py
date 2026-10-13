"""
RAG (Retrieval-Augmented Generation) package for the NextGig AI Assistant.
"""

from apps.opportunities.embeddings import (
    OpportunityEmbedding,
    build_opportunity_document,
    compute_content_hash,
    index_opportunity,
)
from apps.assistant.rag.retrieval import (
    build_query_text,
    retrieve_candidate_opportunities,
    retrieve_with_source,
)

__all__ = [
    "OpportunityEmbedding",
    "build_opportunity_document",
    "compute_content_hash",
    "index_opportunity",
    "build_query_text",
    "retrieve_candidate_opportunities",
    "retrieve_with_source",
]

