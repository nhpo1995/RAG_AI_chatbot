from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from dotenv import load_dotenv

load_dotenv()

def get_document_embedder():
    """Lấy component để tạo embedding cho Haystack Document."""
    embedder = OpenAIDocumentEmbedder(
        model="text-embedding-3-small",
    )
    return embedder



def get_text_embedder():
    """Lấy component để tạo embedding cho câu hỏi (dạng text)."""
    embedder = OpenAITextEmbedder(
        model="text-embedding-3-small",
    )
    return embedder
