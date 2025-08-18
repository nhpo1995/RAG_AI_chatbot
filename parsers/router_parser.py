from pathlib import Path
from typing import List
import sys
# Add parent directory to path để có thể import parsers package
sys.path.append(str(Path(__file__).parent.parent))

from haystack import Document
from parsers._docling_docx_parser import DocxParser
from parsers._docling_pdf_parser import PdfParser
from parsers._docling_md_parser import MdParser
from parsers._docling_txt_parser import TxtParser

class RouterParser:
    """
    RouterParser:
        - Gọi parser tương ứng cho từng loại file
    """

    def __init__(self, images_root: Path):
        self.doc_parser = DocxParser(images_root=images_root)
        self.pdf_parser = PdfParser(images_root=images_root)
        self.md_parser = MdParser(images_root=images_root)
        self.txt_parser = TxtParser()

    def convert_file(self, file_path: Path) -> List[Document]:
        ext = file_path.suffix.lower()
        if ext == ".docx":
            print("Dùng docx_parser")
            return self.doc_parser.parse(file_path)
        elif ext == ".pdf":
            print("Dùng pdf_parser")
            return self.pdf_parser.parse(file_path)
        elif ext == ".md":
            print("Dùng md_parser")
            return self.md_parser.parse(file_path)
        elif ext == ".txt":
            print("Dùng txt_parser")
            return self.txt_parser.parse(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def parse_folder(self, folder_path: Path) -> List[Document]:
        result_list: List[Document] = []
        for file_path in folder_path.iterdir():
            try:
                print(f"Parsing file: {file_path}")
                result_list.extend(self.convert_file(file_path))
            except Exception as e:
                print(f"Lỗi khi parse file {file_path.name}: {e}")
        return result_list

    def parse_list_file(self, list_file: List[Path]) -> List[Document]:
        result_list: List[Document] = []
        for file_path in list_file:
            try:
                print(f"Parsing file: {file_path}")
                result_list.extend(self.convert_file(file_path))
            except Exception as e:
                print(f"Lỗi khi parse file {file_path.name}: {e}")
        return result_list



# ----------------- Test nhanh -----------------
if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Add parent directory to path để có thể import config
    sys.path.append(str(Path(__file__).parent.parent))
    import config as cf
    router = RouterParser(images_root=cf.IMAGES_PATH)

    # Test từng file
    file_paths = [
        cf.DATA_PATH / "Đô Thị Hóa.docx",
        cf.DATA_PATH / "Tác động của Biến đổi Khí hậu đến Nông nghiệp Việt Nam.pdf"
    ]

    folder_path = cf.DATA_PATH

    docs = router.parse_folder(folder_path)

    for idx, doc in enumerate(docs):
        print("=" * 20)
        print(f"{idx}. filename: {doc.meta['filename']}")
        print(f"category: {doc.meta['category']}")
        print(f"trace: {doc.meta['trace']}")
        print(f"content preview: {doc.content}")
        if doc.meta["category"] == "image":
            print(f"image path: {doc.meta.get('file_path')}")



