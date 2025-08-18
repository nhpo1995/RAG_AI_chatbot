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
        self.client: QdrantClient = self.store._client #type: ignore

    def add_chunks(self, docs_dict: Dict[str, List[Document]]):
        """
        Thêm nhiều file cùng lúc, docs_dict {file_source: List[Document]}
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
        Logic: xóa chunks cũ → thêm chunks mới.
        """
        for file_source, docs in docs_dict.items():
            logger.info(f"Đang update file: {file_source}")
            self.delete_file(file_source)
            self.store.write_documents(docs)
            logger.info(f"Update thành công file: {file_source}")
        return self.store

    def delete_file(self, file_source: str):
        """
        Xóa tất cả chunks thuộc 1 file theo metadata 'source'.
        """
        result = self.client.delete(
            collection_name=self.store.index,
            filter=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=file_source)
                    )
                ]
            )
        )
        if result.status != "ok":
            logger.error(f"Lỗi khi xóa file: {file_source}")
        else:
            logger.info(f"Đã xóa tất cả chunks của file: {file_source}")

    def get_all_chunks(self, file_source: str, limit: int = 100, offset: int = 0) -> List[Document]:
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
                    must=[FieldCondition(key="source", match=MatchValue(value=file_source))]
                ),
                limit=limit,
                offset=next_offset
            )
            if not scroll_resp or not scroll_resp[0]:
                break
            for d in scroll_resp[0]:
                doc = Document(
                    content=d.payload.get("content", ""),
                    meta=d.payload
                )
                documents.append(doc)
            next_offset += limit
        logger.info(f"Lấy {len(documents)} chunks cho file: {file_source}")
        return documents

    def clear_all_vectors(self):
        """
        Xóa toàn bộ vectors trong collection.
        """
        try:
            # Cách 1: Xóa toàn bộ points trong collection (giữ lại collection structure)
            collection_info = self.client.get_collection(self.store.index)
            if collection_info.points_count > 0:
                # Xóa tất cả points bằng cách delete với filter trống
                result = self.client.delete(
                    collection_name=self.store.index,
                    points_selector=models.FilterSelector(
                        filter=models.Filter()  # Empty filter = all points
                    )
                )
                if hasattr(result, 'status') and result.status == "ok":
                    logger.info(f"Đã xóa toàn bộ {collection_info.points_count} vectors trong collection: {self.store.index}")
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
                
                # Tạo lại collection với cùng config
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
            logger.info(f"Rebuild hoàn tất: {len(embedded_docs)} files, {total_chunks} chunks")
        else:
            logger.warning("Không có documents nào được process")
        return embedded_docs

