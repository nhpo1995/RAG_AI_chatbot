from processing import files_to_embed
from storage.vector_store import get_document_store
import config as c
from utils.logger import setup_colored_logger
from storage.retriever import get_retriever
from pprint import pprint

logger = setup_colored_logger()

def run_indexing_pipeline():
    """
    Chạy pipeline hoàn chỉnh để xử lý và lưu trữ tài liệu.
    """
    print("🚀 Khởi động Indexing Pipeline...")
    document_store = get_document_store(recreate_index=True)
    parser = DocParser(images_root=c.IMAGES_PATH)
    cleaner = DocumentCleanerWrapper()
    chunker = DocumentChunkerWrapper()
    embedder = get_document_embedder()
    print("✅ Đã khởi tạo xong các component.")


def get_answer():
    document_store = get_document_store(recreate_index=False)
    query = "1. Bảng Doanh Thu Bán Hàng"
    pipe = Pipeline()
    pipe.add_component("embedder", get_text_embedder())
    pipe.add_component("retriever", get_retriever(top_k=10, document_store=document_store))
    pipe.connect("embedder.embedding", "retriever.query_embedding")
    result = pipe.run({"embedder": {"text": query}})
    documents = result['retriever']['documents']
    for doc in documents:
        print("------------------------------------------")
        print(f"ID: {doc.id}")
        print(f"Score: {doc.score}")
        print(f"Content:\n{doc.content}")
        print(f"doc_type: {doc.meta['category']}")
        print(f"source: {doc.meta['source']}")
        print(f"file_path: {doc.meta.get('file_path')}")

if __name__ == "__main__":
    run_indexing_pipeline()
    get_answer()