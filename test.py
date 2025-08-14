# test_minimal.py

from haystack import Document
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from sentence_transformers import SentenceTransformer

# 1. Khởi tạo Document Store
#    Kết nối tới Qdrant đang chạy trên Docker của bạn
try:
    document_store = QdrantDocumentStore(
        url="http://localhost:6333",
        index="test_index",
        embedding_dim=384,  # Kích thước của model 'all-MiniLM-L6-v2'
        recreate_index=True,
    )
    print("✅ Kết nối tới Qdrant và tạo index 'test_index' thành công.")
except Exception as e:
    print(f"❌ Lỗi khi kết nối tới Qdrant: {e}")
    exit()

# 2. Tạo một tài liệu đơn giản
doc = Document(content="Đây là một tài liệu thử nghiệm.")
print("✅ Đã tạo document thử nghiệm.")


# 3. Tạo embedding cho tài liệu
#    (Trong pipeline thật, đây là việc của Embedder component)
try:
    encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    doc.embedding = encoder.encode([doc.content])[0].tolist()
    print("✅ Đã tạo embedding cho document.")
except Exception as e:
    print(f"❌ Lỗi khi tạo embedding: {e}")
    exit()


# 4. Ghi tài liệu vào Document Store
#    Đây là cách gọi trực tiếp, không qua pipeline
try:
    count = document_store.write_documents([doc])
    print(f"🎉 Ghi thành công {count} tài liệu vào Qdrant!")
except Exception as e:
    print(f"❌ Lỗi khi ghi tài liệu: {e}")
    exit()

# 5. Kiểm tra lại bằng cách đếm
try:
    total_docs = document_store.count_documents()
    print(f"📈 Hiện có tổng cộng {total_docs} tài liệu trong index 'test_index'.")
except Exception as e:
    print(f"❌ Lỗi khi đếm tài liệu: {e}")