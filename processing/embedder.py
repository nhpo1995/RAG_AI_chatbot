from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from dotenv import load_dotenv

load_dotenv()

def get_document_embedder():
    """Lấy component để tạo embedding cho Haystack Document."""
    # return SentenceTransformersDocumentEmbedder(
    #     model=config.EMBEDDING_MODEL,
    #     progress_bar=True,
    #     meta_fields_to_embed=["category"]
    # )
    embedder = OpenAIDocumentEmbedder(
        model="text-embedding-3-small",
    )
    return embedder



def get_text_embedder():
    """Lấy component để tạo embedding cho câu hỏi (dạng text)."""
    # return SentenceTransformersDocumentEmbedder(
    #     model=c.EMBEDDING_MODEL,
    #     progress_bar=True,
    #     meta_fields_to_embed=["category"]
    # )
    embedder = OpenAITextEmbedder(
        model="text-embedding-3-small",
    )
    return embedder
