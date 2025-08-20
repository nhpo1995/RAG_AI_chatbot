from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from typing import List, Dict
from haystack import Document
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector
from qdrant_client.http import models
from qdrant_client import QdrantClient
from utils.logger import setup_colored_logger
from storage.vector_store import get_document_store
import logging

setup_colored_logger()
logger = logging.getLogger(__name__)


class QdrantManager:
    """
    Manager thao tác Add / Update / Delete chunks trong Qdrant
    """

    def __init__(self, document_store: QdrantDocumentStore):
        self.store: QdrantDocumentStore = document_store or get_document_store()
        # Khởi tạo client trực tiếp nếu store._client là None
        if hasattr(self.store, "_client") and self.store._client is not None:
            self.client: QdrantClient = self.store._client
        else:
            # Tạo client trực tiếp sử dụng cấu hình của store
            from config import VECTOR_DB_URL

            self.client = QdrantClient(url=VECTOR_DB_URL)
        # Test kết nối
        try:
            self.client.get_collections()
        except Exception as e:
            raise ConnectionError(
                f"Không thể kết nối đến Qdrant server: {e}\n"
                "Hãy đảm bảo Qdrant server đang chạy trên http://localhost:6333\n"
                "Chạy: docker run -p 6333:6333 qdrant/qdrant"
            )

    def add_chunks(self, docs_dict: Dict[str, List[Document]]):
        """
        Thêm nhiều file cùng lúc, docs_dict {file_source: List[Document]}
        Chỉ được dùng cho logic reload database. Không dùng để add riêng lẻ
        """
        for file_source, docs in docs_dict.items():
            if not docs:
                logger.warning(f"Không có chunk nào để thêm cho file: {file_source}")
                continue
            logger.info(f"Thêm {len(docs)} chunks cho file: {file_source}")
            self.store.write_documents(docs)
        return self.store

    def update_chunks(self, docs_dict: Dict[str, List[Document]]):
        """
        Update toàn bộ chunks của mỗi file theo file_source.
        Logic: xóa chunks cũ → thêm chunks mới. Nếu source không tồn tại thì chỉ thêm mới
        """
        for file_source, docs in docs_dict.items():
            logger.info(f"Đang update file: {file_source}")
            result = self.delete_file(file_source)
            if result:
                logger.warning(
                    f"file chưa tồn tại trong database, tiến hành thêm mới: {file_source}"
                )
            else:
                logger.info(
                    f"Đã xóa tất cả chunks của file: {file_source}, tiến hành update lại file mới"
                )
            self.store.write_documents(docs)
            logger.info(f"Update thành công file: {file_source}")
        return self.store

    def delete_file(self, file_source: str):
        """
        Xóa tất cả chunks thuộc 1 file theo metadata 'source'.
        """
        if not file_source:
            raise ValueError("file_source không được để trống")
        chunks = self.get_all_chunks(file_source, limit=1)
        if not chunks:
            logger.warning(f"Không tìm thấy chunks nào cho file: {file_source}")
            return None
        total_chunks = len(self.get_all_chunks(file_source))
        logger.info(f"Bắt đầu xóa {total_chunks} chunks cho file: {file_source}")
        try:
            result = self.client.delete(
                collection_name=self.store.index,
                points_selector=models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="source", match=MatchValue(value=file_source)
                            )
                        ]
                    )
                ),
            )
            if hasattr(result, "status") and result.status == "ok":
                logger.info(
                    f"Xóa thành công {total_chunks} chunks cho file: {file_source}"
                )
            else:
                logger.warning(
                    f"Xóa file {file_source} có thể không thành công, result: {result}"
                )
            return result
        except Exception as e:
            logger.error(f"Lỗi khi xóa file {file_source}: {e}")
            raise e

    def get_all_chunks(
        self, file_source: str, limit: int = 100, offset: int = 0
    ) -> List[Document]:
        """
        Lấy tất cả chunks của 1 file theo metadata 'source'.
        Có hỗ trợ phân trang qua limit và offset.
        """
        documents = []
        next_offset = offset
        while True:
            scroll_resp = self.client.scroll(
                collection_name=self.store.index,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source", match=MatchValue(value=file_source)
                        )
                    ]
                ),
                limit=limit,
                offset=next_offset,
            )
            if not scroll_resp or not scroll_resp[0]:
                break
            for d in scroll_resp[0]:
                payload = d.payload or {}
                doc = Document(content=payload.get("content", ""), meta=payload)
                documents.append(doc)
            next_offset += limit
        logger.info(f"Lấy {len(documents)} chunks cho file: {file_source}")
        return documents

    def clear_all_vectors(self):
        """
        Xóa toàn bộ vectors trong collection.
        """
        if self.client is None:
            raise ConnectionError("Qdrant client is not initialized")

        try:
            collection_info = self.client.get_collection(self.store.index)
            if collection_info.points_count and collection_info.points_count > 0:
                # Xóa tất cả points bằng cách delete với filter trống
                result = self.client.delete(
                    collection_name=self.store.index,
                    points_selector=models.FilterSelector(
                        filter=models.Filter()  # Filter trống = tất cả points
                    ),
                )
                if hasattr(result, "status") and result.status == "ok":
                    logger.info(
                        f"Đã xóa toàn bộ {collection_info.points_count} vectors trong collection: {self.store.index}"
                    )
                else:
                    raise Exception("Delete operation failed")
            else:
                logger.info(f"Collection {self.store.index} đã trống")
        except Exception as e:
            logger.warning(f"Không thể xóa points, thử xóa và tạo lại collection: {e}")
            # Fallback: xóa collection và tạo lại
            try:
                self.client.delete_collection(self.store.index)
                logger.info(f"Đã xóa collection: {self.store.index}")
                from storage.vector_store import get_document_store

                new_store = get_document_store(recreate_index=True)
                self.store = new_store
                logger.info(f"Đã tạo lại collection: {self.store.index}")
            except Exception as e2:
                logger.error(f"Lỗi khi tạo lại collection: {e2}")
                raise e2

    def rebuild_from_folder(self, folder_path):
        """
        Xóa toàn bộ vectors và rebuild từ folder.
        """
        from processing.files_to_embed import DocToEmbed

        logger.info("Bắt đầu rebuild database...")
        # 1. Xóa toàn bộ vectors
        self.clear_all_vectors()
        # 2. Process folder và add chunks
        processor = DocToEmbed()
        embedded_docs = processor.process_folder(folder_path)
        # 3. Add chunks vào DB
        if embedded_docs:
            self.add_chunks(embedded_docs)
            total_chunks = sum(len(docs) for docs in embedded_docs.values())
            logger.info(
                f"Rebuild hoàn tất: {len(embedded_docs)} files, {total_chunks} chunks"
            )
        else:
            logger.warning("Không có documents nào được process")
        return embedded_docs
