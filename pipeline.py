from haystack import Pipeline

from parsers.doc_parser import DocParser
from processing.cleaner import DocumentCleanerWrapper
from processing.chunker import DocumentChunkerWrapper
from processing.embedder import get_document_embedder, get_text_embedder
from storage.vector_store import get_document_store
import config as c
from utils.logger import setup_colored_logger
from qdrant_client import QdrantClient
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
    parsed_docs = parser.run(folder_path=c.DATA_PATH)
    cleaned_docs = cleaner.run(documents=parsed_docs)
    chunked_docs = chunker.run(documents=cleaned_docs)
    for idx, doc in enumerate(chunked_docs):
        print(f"chunk {idx + 1} of {len(chunked_docs)}")
        pprint(f"chunk content: {doc.content}")
    # embedded_docs = embedder.run(documents=chunked_docs)["documents"]
    # document_store.write_documents(embedded_docs)
    # print(f"all documents written to {c.DATA_PATH} with {len(chunked_docs)} chunks.")

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
    # run_indexing_pipeline()
    get_answer()