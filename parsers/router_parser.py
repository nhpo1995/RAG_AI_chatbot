from pathlib import Path
from typing import List
from haystack import Document
from _doc_parser import DocParser
from _pdf_parser import PDFParser

class RouterParser:
    """
    RouterParser:
    - Nếu file là Word, TXT, MD → DocParser
    - Nếu file là PDF → PDFParser
    """

    def __init__(self, images_root: Path):
        self.doc_parser = DocParser(images_root=images_root)
        self.pdf_parser = PDFParser(images_root=images_root)

    def parse_file(self, file_path: Path) -> List[Document]:
        ext = file_path.suffix.lower()
        if ext in {".docx", ".doc", ".txt", ".md"}:
            print("Dùng doc_parser")
            return self.doc_parser.parse_file(file_path)
        elif ext == ".pdf":
            print("Dùng pdf_parser")
            return self.pdf_parser.parse_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

# ----------------- Test nhanh -----------------
if __name__ == "__main__":
    import config as cf
    router = RouterParser(images_root=cf.IMAGES_PATH)

    # Test từng file
    file_paths = [
        cf.DATA_PATH / "Đô Thị Hóa.docx",
        cf.DATA_PATH / "Tác động của Biến đổi Khí hậu đến Nông nghiệp Việt Nam.pdf"
    ]

    for fpath in file_paths:
        print(f"Parsing file: {fpath.name}")
        try:
            docs = router.parse_file(fpath)
            for idx, doc in enumerate(docs):
                print("="*20)
                print(f"{idx}. filename: {doc.meta['filename']}")
                print(f"category: {doc.meta['category']}")
                print(f"trace: {doc.meta['trace']}")
                print(f"content preview: {doc.content}")
                if doc.meta['category'] == "image":
                    print(f"image path: {doc.meta.get('file_path')}")
        except Exception as e:
            print(f"Lỗi khi parse file {fpath.name}: {e}")
