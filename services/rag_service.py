from agent.rag_agent import RAGAssistant
from storage.qdrant_query_manager import QdrantQueryManager
from typing import List
from haystack import Document
import logging
from utils.logger import setup_colored_logger

setup_colored_logger()
logger = logging.getLogger(__file__)

class RAGService:
    def __init__(self, rag_agent: RAGAssistant = None):
        self.rag_agent = rag_agent or RAGAssistant()
        self.query_manager = QdrantQueryManager()

    @staticmethod
    def _docs_to_context(docs: List[Document]) -> str:
        """
        Gộp toàn bộ content của docs thành 1 chuỗi context cho AI.
        Bỏ qua metadata.
        """
        context = []
        if not docs:
            return ""
        for doc in docs:
            if doc.content and doc.content.strip():
                context.append(doc.content.strip())
                if doc.meta.get("category") == "image":
                    context.append(f"file_path: {doc.meta.get('filepath')}")
        return "\n\n".join(context)

    def semantic_query(self, query: str, top_k: int) -> str:
        context = self._docs_to_context(
            self.query_manager.semantic_search(query=query, top_k=top_k, filters=None)
        )
        logger.info(f"Question: {query}")
        logger.info(f"context: {context}")
        answer = self.rag_agent.ask(context=context, question=query)
        logger.info(f"Answer: {answer}")
        return answer


if __name__ == "__main__":
    rag_service = RAGService()
    user_message = "Bui minh Hieu la ai"
    ai_answer = rag_service.semantic_query(query=user_message, top_k=5)
    print(ai_answer)


