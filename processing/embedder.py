from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
import config

def get_document_embedder():
    """Lấy component để tạo embedding cho Haystack Document."""
    return SentenceTransformersDocumentEmbedder(
        model=config.EMBEDDING_MODEL,
        progress_bar=True,
        meta_fields_to_embed=["category"]
    )

def get_text_embedder():
    """Lấy component để tạo embedding cho câu hỏi (dạng text)."""
    return SentenceTransformersTextEmbedder(
        model=config.EMBEDDING_MODEL,
        progress_bar=False
    )