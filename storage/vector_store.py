# storage/vector_store.py

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from qdrant_client import models
import config


def get_document_store() -> QdrantDocumentStore:
    """
    Khởi tạo và trả về một QdrantDocumentStore đã được tối ưu cho hiệu năng và bộ nhớ.
    """
    # 1. Tạo object cấu hình HNSW từ qdrant_client
    hnsw_config_object = models.HnswConfigDiff(m=16, ef_construct=100)

    # 2. Tạo object cấu hình lượng tử hóa từ qdrant_client
    quantization_config_object = models.ScalarQuantization(
        type=models.ScalarType.INT8, always_ram=True
    )

    document_store = QdrantDocumentStore(
        url=config.VECTOR_DB_URL,
        index=config.VECTOR_DB_COLLECTION,
        embedding_dim=384,
        similarity="cosine",
        recreate_index=False,
        hnsw_config=hnsw_config_object.dict(),
        quantization_config=quantization_config_object.dict(),
        on_disk_payload=True,
        write_batch_size=128,
        payload_fields_to_index=[
            {"key": "permission", "type": "keyword"},
            {"key": "source", "type": "keyword"},
            {"key": "filename", "type": "keyword"},
        ],
    )
    return document_store
