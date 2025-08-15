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
        self.text_embedder = get_text_embedder()

    def get_retriever(
        self,
        document_store: Optional[QdrantDocumentStore] = None,
        top_k: int = 5,
        filters: Optional[Union[Dict[str, Any], Filter]] = None,
        score_threshold: float = 0.65,
    ) -> QdrantEmbeddingRetriever:
        return QdrantEmbeddingRetriever(
            document_store=self.document_store,
            top_k=top_k,
            return_embedding=False,
            scale_score=True,
            score_threshold=score_threshold,
            filters=filters
        )

    def semantic_search(self, query: str, top_k: int = 5, filters: Optional[Union[Dict[str, Any], Filter]] = None) -> List[Document]:
        """
            Tìm kiếm semantic dựa trên query text filter metadata (nếu có).
        """
        if not query:
            return []
        embed_result = self.text_embedder.run({"text": query})
        embedded_query = embed_result["embedding"]
        retriever = self.get_retriever(top_k=top_k, filters=filters)
        result = retriever.run(query_embedding=embedded_query)
        docs = result.get("documents", [])
        logger.info(f"[SemanticSearch] Query='{query}' Filter={filters} → {len(docs)} kết quả")
        return docs

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """
        Xây dựng Qdrant Filter từ dict {key: value}.
        """
        if not filters:
            return None
        must_conditions = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in filters.items()
        ]
        return Filter(must=must_conditions)

    def metadata_search(
            self,
            filters: Dict[str, Any],
            limit: int = 100,
            offset: int = 0
    ) -> List[Document]:
        """
        Lấy documents chỉ dựa trên filter metadata (không semantic search).
        """
        qdrant_filter = self._build_filter(filters)
        scroll_resp = self.document_store._client.scroll(
            collection_name=self.document_store.index,
            scroll_filter=qdrant_filter,
            limit=limit,
            offset=offset
        )
        if not scroll_resp or not scroll_resp[0]:
            logger.warning("[MetadataSearch] Không tìm thấy dữ liệu")
            return []
        docs = []
        for d in scroll_resp[0]:
            meta = {k: v for k, v in d.payload.items() if k != "content"}
            doc = Document(
                content = d.payload.get("content", ""),
                meta = meta,
            )
            docs.append(doc)
        logger.info(f"[MetadataSearch] Filter={filters} → {len(docs)} kết quả")
        return docs



