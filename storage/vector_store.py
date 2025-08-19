from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from qdrant_client import models
import config


def get_document_store(recreate_index=False) -> QdrantDocumentStore:
    """
    Khởi tạo và trả về một QdrantDocumentStore đã được tối ưu cho hiệu năng và bộ nhớ.
    """
    quantization_config_object = models.ScalarQuantization(
        scalar=models.ScalarQuantizationConfig(
            type=models.ScalarType.INT8, quantile=1.0, always_ram=True
        )
    )

    document_store = QdrantDocumentStore(
        url=config.VECTOR_DB_URL,
        index=config.VECTOR_DB_COLLECTION,
        embedding_dim=1536,
        similarity="cosine",
        recreate_index=recreate_index,
        hnsw_config={"m": 16, "ef_construct": 64},
        quantization_config=quantization_config_object,  # type: ignore
        on_disk_payload=True,
        write_batch_size=128,
        payload_fields_to_index=[
            {"field_name": "document_id", "field_schema": {"type": "keyword"}},
            {"field_name": "category", "field_schema": {"type": "keyword"}},
            {"field_name": "source", "field_schema": {"type": "keyword"}},
        ],
    )
    return document_store
