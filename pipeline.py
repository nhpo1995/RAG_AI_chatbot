from haystack import Pipeline

from processing import files_to_embed
from processing.embedder import get_text_embedder
from storage.vector_store import get_document_store
# from utils.logger import setup_colored_logger
from storage.retriever import get_retriever

# logger = setup_colored_logger()


def get_answer():
    document_store = get_document_store(recreate_index=False)
    query = "1. Bảng Doanh Thu Bán Hàng"
    pipe = Pipeline()
    pipe.add_component("embedder", get_text_embedder())
    pipe.add_component("retriever", get_retriever(top_k=10, document_store=document_store))
    pipe.connect("embedder.embedding", "retriever.query_embedding")
    result = pipe.run({"embedder": {"text": query}})
    documents = result['retriever']['documents']
    print(f"🔍 Số lượng documents được tìm thấy: {len(documents)}")
    for doc in documents:
        print("------------------------------------------")
        print(f"ID: {doc.id}")
        print(f"Score: {doc.score}")
        print(f"Content:\n{doc.content}")
        print(f"doc_type: {doc.meta['category']}")
        print(f"source: {doc.meta['source']}")
        print(f"file_path: {doc.meta.get('file_path')}")

def debug_list_documents(document_store):
    print("🧪 Kiểm tra dữ liệu trong collection:", document_store.index)
    scroll_result = document_store._client.scroll(
        collection_name=document_store.index,
        limit=10  # kiểm tra vài doc trước
    )[0]

    if not scroll_result:
        print("❌ Không có document nào trong collection.")
        return

    for point in scroll_result:
        content = point.payload.get("content", "")
        print("📄", content[:200].replace("\n", " "), "...\n")


if __name__ == "__main__":
    document_store = get_document_store()
    debug_list_documents(document_store)
    get_answer()