from haystack import Document
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from typing import List, Dict, Optional, Any, Union
from storage.vector_store import get_document_store
import logging
from utils.logger import setup_colored_logger
from processing.embedder import get_text_embedder


setup_colored_logger()
logger = logging.getLogger(__name__)


class QdrantQueryManager:
    """
    Class quản lý việc truy vấn dữ liệu từ Qdrant.
    Bao gồm cả semantic search (retriever) và metadata search (document_store).
    """

    def __init__(self, document_store: Optional[QdrantDocumentStore] = None):
        self.document_store = document_store or get_document_store()
        logger.info(
            f"[QdrantQueryManager] Truy vấn collection: {self.document_store.index}"
        )
        self.text_embedder = get_text_embedder()

    def get_retriever(
        self,
        document_store: Optional[QdrantDocumentStore] = None,
        top_k: int = 5,
        filters: Optional[Union[Dict[str, Any], Filter]] = None,
        score_threshold: float = 0.4,
    ) -> QdrantEmbeddingRetriever:
        return QdrantEmbeddingRetriever(
            document_store=self.document_store,
            top_k=top_k,
            return_embedding=False,
            scale_score=True,
            score_threshold=score_threshold,
            filters=filters,
        )

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Union[Dict[str, Any], Filter]] = None,
    ) -> List[Document]:
        """
        Tìm kiếm semantic dựa trên query text filter metadata (nếu có).
        """
        if not query:
            return []
        embed_result = self.text_embedder.run(text=query)
        embedded_query = embed_result["embedding"]
        retriever = self.get_retriever(top_k=top_k, filters=filters)
        result = retriever.run(query_embedding=embedded_query)
        docs = result.get("documents", [])
        logger.info(
            f"[SemanticSearch] Query='{query}' Filter={filters} → {len(docs)} kết quả"
        )
        return docs
