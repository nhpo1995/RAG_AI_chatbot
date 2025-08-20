from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack import Document
from dotenv import load_dotenv
import config
import logging

load_dotenv()
logger = logging.getLogger(__name__)


def _validate_documents(documents):
    """Validate documents before embedding to prevent API errors"""
    valid_docs = []
    for doc in documents:
        if not isinstance(doc, Document):
            logger.warning(f"Skipping non-Document object: {type(doc)}")
            continue
        if not doc.content or not str(doc.content).strip():
            logger.warning(
                f"Skipping document with empty content: {doc.meta.get('filename', 'unknown')}"
            )
            continue
        # Đảm bảo content là string hợp lệ
        try:
            content_str = str(doc.content).strip()
            if len(content_str) > 0:
                # Tạo document sạch với content đã được xác thực
                clean_doc = Document(content=content_str, meta=doc.meta)
                valid_docs.append(clean_doc)
            else:
                logger.warning(
                    f"Skipping document with empty content after cleaning: {doc.meta.get('filename', 'unknown')}"
                )
        except Exception as e:
            logger.error(
                f"Error processing document {doc.meta.get('filename', 'unknown')}: {e}"
            )
            continue
    logger.info(f"Validated {len(valid_docs)}/{len(documents)} documents for embedding")
    return valid_docs


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


def safe_embed_documents(documents, batch_size: int = 10):
    """Safely embed documents with validation and error handling"""
    if not documents:
        logger.warning("No documents provided for embedding")
        return []

    logger.info(
        f"Starting embedding process for {len(documents)} documents with batch_size={batch_size}"
    )

    # Xác thực documents trước
    valid_docs = _validate_documents(documents)
    if not valid_docs:
        logger.warning("No valid documents to embed after validation")
        return []

    try:
        logger.info(f"Calling OpenAI embedding API for {len(valid_docs)} documents")
        embedder = get_document_embedder(batch_size=batch_size)
        result = embedder.run(documents=valid_docs)
        embedded_docs = result.get("documents", [])
        logger.info(f"Successfully embedded {len(embedded_docs)} documents")

        # Log một số chi tiết về documents đã được embed
        if embedded_docs:
            first_doc = embedded_docs[0]
            logger.debug(
                f"First embedded document: {first_doc.meta.get('filename', 'unknown')} - content length: {len(first_doc.content) if first_doc.content else 0}"
            )

        return embedded_docs
    except Exception as e:
        logger.error(f"Embedding failed with error: {e}")
        logger.error(f"Error type: {type(e).__name__}")

        # Thử với batch size nhỏ hơn làm fallback
        if batch_size > 1:
            logger.info(f"Retrying with batch_size=1")
            return safe_embed_documents(valid_docs, batch_size=1)

        logger.error("All embedding attempts failed")
        return []
