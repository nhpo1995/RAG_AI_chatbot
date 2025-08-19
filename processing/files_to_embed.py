from pathlib import Path
import sys

# Add parent directory to path để có thể import config và modules khác
sys.path.append(str(Path(__file__).parent.parent))

from processing._chunker import DocumentChunkerWrapper
from processing._cleaner import DocumentCleanerWrapper
from processing.embedder import get_document_embedder
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
        # Note: embedder will be created dynamically with adaptive batch size

    def _get_adaptive_batch_size(self, documents: List[Document]) -> int:
        """Tự động chọn batch size dựa trên số lượng và kích thước documents"""
        total_docs = len(documents)
        if total_docs == 0:
            return 1

        avg_content_length = (
            sum(len(doc.content or "") for doc in documents) / total_docs
        )
        # Dynamic sizing rules - conservative approach
        if total_docs <= 5:
            return total_docs  # Process all at once
        elif avg_content_length < 500:  # Short content
            return min(15, total_docs)
        elif avg_content_length < 2000:  # Medium content
            return min(8, total_docs)
        else:  # Long content
            return min(5, total_docs)

    def _try_embed_with_fallback(
        self, documents: List[Document], initial_batch_size: int
    ) -> List[Document]:
        """Try embedding with progressively smaller batches if failed"""
        strategies = [
            ("optimal", initial_batch_size),
            ("conservative", max(1, initial_batch_size // 2)),
            ("very_safe", 3),
            ("individual", 1),
        ]

        for strategy_name, batch_size in strategies:
            try:
                embedder = get_document_embedder(batch_size=batch_size)
                logger.info(
                    f"Trying {strategy_name} strategy with batch_size={batch_size} for {len(documents)} documents"
                )

                if batch_size >= len(documents):
                    # Process all at once
                    return embedder.run(documents=documents)["documents"]
                else:
                    # Process in batches
                    all_embedded = []
                    for i in range(0, len(documents), batch_size):
                        batch = documents[i : i + batch_size]
                        embedded_batch = embedder.run(documents=batch)["documents"]
                        all_embedded.extend(embedded_batch)
                        logger.debug(
                            f"Processed batch {i//batch_size + 1}: {len(embedded_batch)} documents"
                        )
                    return all_embedded

            except Exception as e:
                logger.warning(
                    f"Strategy {strategy_name} (batch_size={batch_size}) failed: {e}"
                )
                continue

        logger.error(f"All embedding strategies failed for {len(documents)} documents")
        return []

    def _clean_to_embed(self, list_doc: List[Document]) -> List[Document]:
        """Clean, chunk và embed documents với adaptive batching"""
        cleaned_docs = self.cleaner.run(documents=list_doc)
        chunked_docs = self.chunker.run(documents=cleaned_docs)

        if not chunked_docs:
            return []
        # Adaptive batching
        optimal_batch_size = self._get_adaptive_batch_size(chunked_docs)
        logger.info(
            f"Processing {len(chunked_docs)} chunks with optimal batch size: {optimal_batch_size}"
        )
        embedded_docs = self._try_embed_with_fallback(chunked_docs, optimal_batch_size)
        logger.info(
            f"Successfully embedded {len(embedded_docs)}/{len(chunked_docs)} documents"
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

    def test_parser(self, folder_path: Path):
        parsed_docs = self.parser.parse_folder(folder_path=folder_path)
        for idx, doc in enumerate(parsed_docs):
            print(f"{idx}. {doc.meta['filename']}")
            print(f"content: {doc.content}")


if __name__ == "__main__":
    pipe = DocToEmbed()
    pipe.test_parser(cf.DATA_PATH)
