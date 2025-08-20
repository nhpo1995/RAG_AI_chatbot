#!/usr/bin/env python3
"""
Script debug để test chức năng embedding và xác định lỗi API
"""
import sys
from pathlib import Path

# Thêm thư mục cha vào path
sys.path.append(str(Path(__file__).parent))

from processing.embedder import safe_embed_documents, _validate_documents
from processing.files_to_embed import DocToEmbed
from haystack import Document
import config
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_document_validation():
    """Test hàm xác thực document"""
    print("=== Testing Document Validation ===")

    # Test với document hợp lệ
    valid_doc = Document(
        content="This is a valid document with content",
        meta={"filename": "test.txt", "category": "text"},
    )

    # Test với nội dung trống
    empty_doc = Document(content="", meta={"filename": "empty.txt", "category": "text"})

    # Test với nội dung None
    none_doc = Document(content=None, meta={"filename": "none.txt", "category": "text"})

    # Test với chỉ khoảng trắng
    whitespace_doc = Document(
        content="   \n\t   ", meta={"filename": "whitespace.txt", "category": "text"}
    )

    test_docs = [valid_doc, empty_doc, none_doc, whitespace_doc]
    print(f"Testing {len(test_docs)} documents...")

    valid_docs = _validate_documents(test_docs)
    print(f"Valid documents: {len(valid_docs)}/{len(test_docs)}")

    for i, doc in enumerate(valid_docs):
        print(f"  {i+1}. {doc.meta.get('filename')}: '{doc.content[:50]}...'")


def test_safe_embedding():
    """Test embedding an toàn với document đơn giản"""
    print("\n=== Testing Safe Embedding ===")

    test_doc = Document(
        content="This is a test document for embedding. It should work without issues.",
        meta={"filename": "test_embed.txt", "category": "text"},
    )

    try:
        embedded_docs = safe_embed_documents([test_doc], batch_size=1)
        print(f"Embedding successful: {len(embedded_docs)} documents")

        if embedded_docs:
            doc = embedded_docs[0]
            print(f"  Content: {doc.content}")
            print(f"  Has embedding: {'embedding' in doc.meta}")
            if "embedding" in doc.meta:
                print(f"  Embedding shape: {len(doc.meta['embedding'])} dimensions")

    except Exception as e:
        print(f"Embedding failed: {e}")
        import traceback

        traceback.print_exc()


def test_file_processing():
    """Test xử lý file nhỏ để xem lỗi xảy ra ở đâu"""
    print("\n=== Testing File Processing ===")

    try:
        processor = DocToEmbed()

        # Kiểm tra thư mục data có tồn tại và có file không
        data_path = config.DATA_PATH
        if not data_path.exists():
            print(f"Data directory does not exist: {data_path}")
            return

        files = list(data_path.glob("*"))
        if not files:
            print(f"No files found in data directory: {data_path}")
            return

        print(f"Found {len(files)} files in data directory")

        # Thử xử lý file đầu tiên
        first_file = files[0]
        print(f"Testing with file: {first_file.name}")

        # Parse file
        parsed_docs = processor.parser.parse_list_file([first_file])
        print(f"Parsed {len(parsed_docs)} documents")

        if parsed_docs:
            # Hiển thị chi tiết document đầu tiên
            doc = parsed_docs[0]
            print(f"First document:")
            print(f"  Content length: {len(doc.content) if doc.content else 0}")
            print(
                f"  Content preview: {doc.content[:100] if doc.content else 'None'}..."
            )
            print(f"  Meta: {doc.meta}")

            # Thử làm sạch và chia nhỏ
            cleaned_docs = processor.cleaner.run(documents=parsed_docs)
            print(f"Cleaned {len(cleaned_docs)} documents")

            chunked_docs = processor.chunker.run(documents=cleaned_docs)
            print(f"Chunked {len(chunked_docs)} documents")

            if chunked_docs:
                # Thử embedding với chunk đầu tiên
                first_chunk = chunked_docs[0]
                print(f"Testing embedding with first chunk:")
                print(f"  Content: {first_chunk.content[:100]}...")

                try:
                    embedded = safe_embed_documents([first_chunk], batch_size=1)
                    print(f"Embedding successful: {len(embedded)} documents")
                except Exception as e:
                    print(f"Embedding failed: {e}")
                    import traceback

                    traceback.print_exc()

    except Exception as e:
        print(f"File processing failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("Starting embedding debug tests...")

    # Test 1: Xác thực document
    test_document_validation()

    # Test 2: Embedding an toàn
    test_safe_embedding()

    # Test 3: Xử lý file
    test_file_processing()

    print("\nDebug tests completed.")
