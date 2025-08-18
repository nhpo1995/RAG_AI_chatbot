from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from haystack import Document

class BaseParser(ABC):
    """
    Lớp trừu tượng cho các parser file.
    Mọi parser (PDF, Word, TXT, MD, ...) nên kế thừa BaseParser
    và implement các phương thức parse_file và run.
    Trả về danh sách Document của Haystack với metadata chuẩn.
    """

    @abstractmethod
    def parse_file(self, file_path: Path) -> List[Document]:
        """
        Parse một file và trả về danh sách Document.
        Mỗi Document phải có:
            - content (text/markdown)
            - meta: category, source, filename, document_id, trace, ...
        """
        pass

    def run(self, folder_path: Path) -> List[Document]:
        """
        Duyệt folder, parse tất cả file (bỏ qua file ẩn).
        Trả về list các Document từ tất cả file.
        """
        all_docs: List[Document] = []
        files = [f for f in folder_path.iterdir() if f.is_file() and not f.name.startswith('.')]
        files.sort()
        for file_path in files:
            try:
                print(f"Parsing file: {file_path.name}")  # Debug
                docs = self.parse_file(file_path)
                all_docs.extend(docs)
            except Exception as e:
                print(f"Lỗi khi xử lý file {file_path.name}: {e}")
        return all_docs
