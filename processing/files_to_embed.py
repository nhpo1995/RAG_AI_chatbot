from pathlib import Path
import sys

# Thêm thư mục cha vào path để có thể import config và các modules khác
sys.path.append(str(Path(__file__).parent.parent))

from processing._chunker import DocumentChunkerWrapper
from processing._cleaner import DocumentCleanerWrapper
from processing.embedder import safe_embed_documents
from parsers.router_parser import RouterParser
from haystack import Document
from typing import List, Dict
from utils.logger import setup_colored_logger
import logging
import config as cf

setup_colored_logger()
logger = logging.getLogger(__name__)


class DocToEmbed:
    def __init__(self):
        self.parser = RouterParser(images_root=cf.IMAGES_PATH)
        self.cleaner = DocumentCleanerWrapper()
        self.chunker = DocumentChunkerWrapper()
        # Lưu ý: embedder sẽ được tạo động với kích thước batch thích ứng

    def _get_adaptive_batch_size(self, documents: List[Document]) -> int:
        """Tự động chọn kích thước batch dựa trên số lượng và kích thước documents"""
        total_docs = len(documents)
        if total_docs == 0:
            return 1

        avg_content_length = (
            sum(len(doc.content or "") for doc in documents) / total_docs
        )
        if total_docs <= 5:
            return total_docs
        elif avg_content_length < 500:
            return min(15, total_docs)
        elif avg_content_length < 2000:
            return min(8, total_docs)
        else:
            return min(5, total_docs)

    def _try_embed_with_fallback(
        self, documents: List[Document], initial_batch_size: int
    ) -> List[Document]:
        """Thử embedding với các batch nhỏ dần nếu thất bại"""
        strategies = [
            ("optimal", initial_batch_size),
            ("conservative", max(1, initial_batch_size // 2)),
            ("very_safe", 3),
            ("individual", 1),
        ]

        for strategy_name, batch_size in strategies:
            try:
                logger.info(
                    f"Thử chiến lược {strategy_name} với batch_size={batch_size} cho {len(documents)} documents"
                )
                embedded_docs = safe_embed_documents(documents, batch_size)
                if embedded_docs:
                    logger.info(
                        f"Chiến lược {strategy_name} thành công với {len(embedded_docs)} documents"
                    )
                    return embedded_docs
                else:
                    logger.warning(
                        f"Chiến lược {strategy_name} không trả về documents nào"
                    )
                    continue
            except Exception as e:
                logger.warning(
                    f"Chiến lược {strategy_name} (batch_size={batch_size}) thất bại: {e}"
                )
                continue
        logger.error(
            f"Tất cả các chiến lược embedding đều thất bại cho {len(documents)} documents"
        )
        return []

    def _clean_to_embed(self, list_doc: List[Document]) -> List[Document]:
        """Làm sạch, chia nhỏ và embed documents với batching thích ứng"""
        # Lọc trước: Loại bỏ documents có nội dung trống trước khi xử lý
        valid_docs = [
            doc for doc in list_doc if doc.content and str(doc.content).strip()
        ]
        if len(valid_docs) < len(list_doc):
            logger.info(
                f"Đã lọc ra {len(list_doc) - len(valid_docs)} documents có nội dung trống"
            )
        if not valid_docs:
            logger.warning("Không có documents hợp lệ để xử lý sau khi lọc nội dung")
            return []
        cleaned_docs = self.cleaner.run(documents=valid_docs)
        chunked_docs = self.chunker.run(documents=cleaned_docs)
        if not chunked_docs:
            return []
        # Batching thích ứng
        optimal_batch_size = self._get_adaptive_batch_size(chunked_docs)
        logger.info(
            f"Xử lý {len(chunked_docs)} chunks với kích thước batch tối ưu: {optimal_batch_size}"
        )
        embedded_docs = self._try_embed_with_fallback(chunked_docs, optimal_batch_size)
        logger.info(
            f"Đã embed thành công {len(embedded_docs)}/{len(chunked_docs)} documents"
        )
        return embedded_docs

    def process_folder(self, folder_path: Path) -> Dict[str, List[Document]]:
        grouped_docs: Dict[str, List[Document]] = {}
        try:
            parsed_docs = self.parser.parse_folder(folder_path=folder_path)
            embedded_docs = self._clean_to_embed(parsed_docs)
            for doc in embedded_docs:
                file_source = doc.meta["source"]
                grouped_docs.setdefault(file_source, []).append(doc)
            logger.info(
                f"[process_folder] Hoàn tất: {len(grouped_docs)} file, {len(embedded_docs)} chunks."
            )
        except Exception as e:
            logger.error(f"[process_folder] Lỗi khi xử lý folder {folder_path}: {e}")
        return grouped_docs

    def process_list_file(
        self, list_file_path: List[Path]
    ) -> Dict[str, List[Document]]:
        grouped_docs: Dict[str, List[Document]] = {}
        total_chunks = 0
        for file_path in list_file_path:
            try:
                parsed_docs = self.parser.parse_list_file(list_file=[file_path])
                embedded_docs = self._clean_to_embed(parsed_docs)
                for doc in embedded_docs:
                    file_source = doc.meta["source"]
                    grouped_docs.setdefault(file_source, []).append(doc)
                total_chunks += len(embedded_docs)
                logger.info(
                    f"[process_list_file] {file_path.name} → {len(embedded_docs)} chunks"
                )
            except Exception as e:
                logger.error(f"[process_list_file] Lỗi xử lý file {file_path}: {e}")
        logger.info(
            f"[process_list_file] Hoàn tất: {len(grouped_docs)} file, {total_chunks} chunks."
        )
        return grouped_docs

    # Hàm này chỉ để test parser
    def _test_parser(self, folder_path: Path):
        parsed_docs = self.parser.parse_folder(folder_path=folder_path)
        for idx, doc in enumerate(parsed_docs):
            print(f"{idx}. {doc.meta['filename']}")
            print(f"content: {doc.content}")


if __name__ == "__main__":
    pipe = DocToEmbed()
    pipe._test_parser(cf.DATA_PATH)
