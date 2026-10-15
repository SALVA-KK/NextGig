"""
LangChain BaseRetriever wrapper for NextGig student assistant RAG retrieval.
"""
from typing import Any, Dict, List, Optional
from pydantic import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

from apps.assistant.rag.retrieval import retrieve_with_source


class OpportunityRetriever(BaseRetriever):
    """
    A per-request BaseRetriever wrapping retrieve_with_source.
    Holds the student_profile_data for the requesting student only.
    """
    student_profile_data: Dict[str, Any] = Field(default_factory=dict)
    candidate_dict: Dict[int, Any] = Field(default_factory=dict)
    candidate_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = Field(default="vector")
    retrieve_fn: Optional[Any] = Field(default=None)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[Any] = None,
    ) -> List[Document]:
        fn = self.retrieve_fn or retrieve_with_source
        cand_dict, cand_opps, src = fn(
            query_text=query,
            student_profile_data=self.student_profile_data,
        )
        self.candidate_dict = cand_dict
        self.candidate_opportunities = cand_opps
        self.source = src

        documents: List[Document] = []
        for opp in cand_opps:
            title = opp.get("title", "")
            cat = opp.get("category", "")
            content = f"{title} ({cat})".strip() if cat else title
            documents.append(Document(page_content=content, metadata=opp))
        return documents
