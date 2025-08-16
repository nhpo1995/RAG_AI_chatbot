from agent.rag_agent import RAGAssistant
from storage.qdrant_query_manager import QdrantQueryManager
from typing import List
from haystack import Document

class RAGService():
    def __init__(self, rag_agent: RAGAssistant = None):
        self.rag_agent = rag_agent or RAGAssistant()
        self.query_manager = QdrantQueryManager()

    @staticmethod
    def _docs_to_context(docs: List[Document]) -> str:
        """
        Gộp toàn bộ content của docs thành 1 chuỗi context cho AI.
        Bỏ qua metadata.
        """
        return "\n\n".join(
            doc.content.strip()
            for doc in docs
            if doc.content and doc.content.strip()
        )

    def semantic_query(self, query: str) -> str:
        context = self._docs_to_context(
            self.query_manager.semantic_search(query=query, filters=None)
        )
        answer = self.rag_agent.ask(context=context, question=query)
        return answer