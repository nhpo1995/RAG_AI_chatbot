from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from dotenv import load_dotenv
import config

load_dotenv()


def get_document_embedder(batch_size: int = 10):
    """Lấy component để tạo embedding cho Haystack Document với batch size tùy chỉnh."""
    embedder = OpenAIDocumentEmbedder(
        model=config.EMBEDDING_MODEL,
        batch_size=batch_size,
        progress_bar=False,  # Tắt để tránh spam logs
        max_retries=3,
        timeout=120,  # Tăng timeout cho files lớn
    )
    return embedder


def get_text_embedder():
    """Lấy component để tạo embedding cho câu hỏi (dạng text)."""
    embedder = OpenAITextEmbedder(
        model=config.EMBEDDING_MODEL,
    )
    return embedder
