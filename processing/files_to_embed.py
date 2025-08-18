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
        self.embedder = get_document_embedder()
        self.chunker = DocumentChunkerWrapper()

    def _clean_to_embed(self, list_doc: List[Document]) -> List[Document]:
        cleaned_docs = self.cleaner.run(documents=list_doc)
        chunked_docs = self.chunker.run(documents=cleaned_docs)
        embedded_docs = self.embedder.run(documents=chunked_docs)["documents"]
        return embedded_docs

    def process_folder(self, folder_path: Path) -> Dict[str, List[Document]]:
        grouped_docs: Dict[str, List[Document]] = {}
        try:
            parsed_docs = self.parser.parse_folder(folder_path=folder_path)
            embedded_docs = self._clean_to_embed(parsed_docs)
            for doc in embedded_docs:
                file_source = doc.meta["source"]
                grouped_docs.setdefault(file_source, []).append(doc)
            logger.info(f"[process_folder] Hoàn tất: {len(grouped_docs)} file, {len(embedded_docs)} chunks.")
        except Exception as e:
            logger.error(f"[process_folder] Lỗi khi xử lý folder {folder_path}: {e}")
        return grouped_docs

    def process_list_file(self, list_file_path: List[Path]) -> Dict[str, List[Document]]:
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
                logger.info(f"[process_list_file] {file_path.name} → {len(embedded_docs)} chunks")
            except Exception as e:
                logger.error(f"[process_list_file] Lỗi xử lý file {file_path}: {e}")
        logger.info(f"[process_list_file] Hoàn tất: {len(grouped_docs)} file, {total_chunks} chunks.")
        return grouped_docs

    def test_parser(self, folder_path: Path):
        parsed_docs = self.parser.parse_folder(folder_path=folder_path)
        for idx, doc in enumerate(parsed_docs):
            print(f"{idx}. {doc.meta['filename']}")
            print(f"content: {doc.content}")


if __name__ == "__main__":
    pipe = DocToEmbed()
    pipe.test_parser(cf.DATA_PATH)







