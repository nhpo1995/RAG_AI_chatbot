# from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
# from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

# from storage.vector_store import get_document_store
# from typing import Dict

# def get_retriever(top_k: int = 5, filters: Dict = None, document_store: QdrantDocumentStore = None):
#     """
#     Khởi tạo và trả về một QdrantEmbeddingRetriever.
#     Hàm này sẽ lấy document store đã được cấu hình và sử dụng nó
#     để khởi tạo retriever.
#     """
#     return QdrantEmbeddingRetriever(
#         document_store=document_store,
#         top_k=top_k,
#         return_embedding=False,
#         scale_score=True,
#         score_threshold=0.6,
#         filters=filters,
#     )