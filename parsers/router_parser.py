from pathlib import Path
from typing import List
from haystack import Document
from _docling_docx_parser import DocxParser
from _docling_pdf_parser import PdfParser
from _docling_md_parser import MdParser
from _docling_txt_parser import TxtParser

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
        if ext == "docx":
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

    def parse(self, folder_path: Path) -> List[Document]:
        result_list: List[Document] = []
        for f in folder_path.iterdir():
            pass


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
