# import uuid
# from pathlib import Path
# from typing import List
# import fitz  # PyMuPDF
# import pdfplumber
# from haystack import Document
# from _base_parser import BaseParser
# import base64
#
# class PDFParser(BaseParser):
#     """
#     Parser PDF:
#     - Text: PyMuPDF, lưu page_number trong trace
#     - Table: pdfplumber để extract DataFrame → Markdown
#     - Image: PyMuPDF, lưu file, tạo Document
#     """
#
#     def __init__(self, images_root: Path = Path("images")):
#         self.images_root = images_root
#         self.images_root.mkdir(exist_ok=True)
#
#     @staticmethod
#     def save_image(pix: fitz.Pixmap, out_path: Path) -> bool:
#         try:
#             out_path.parent.mkdir(parents=True, exist_ok=True)
#             if pix.n < 5:  # RGB or grayscale
#                 pix.save(str(out_path))
#             else:  # CMYK
#                 pix = fitz.Pixmap(fitz.csRGB, pix)
#                 pix.save(str(out_path))
#             pix = None
#             return True
#         except Exception as e:
#             print(f"Failed to save image: {e}")
#             return False
#
#     def parse_file(self, file_path: Path) -> List[Document]:
#         file_document_id = str(uuid.uuid4())
#         docs: List[Document] = []
#
#         # --- 1) Parse text với PyMuPDF ---
#         doc = fitz.open(file_path)
#         for page_number, page in enumerate(doc, start=1):
#             text = page.get_text("text").strip()
#             if text:
#                 docs.append(Document(
#                     content=text,
#                     meta={
#                         "category": "text",
#                         "source": str(file_path),
#                         "filename": file_path.name,
#                         "document_id": file_document_id,
#                         "trace": f"Trang {page_number}"
#                     }
#                 ))
#
#             # --- 2) Parse image với PyMuPDF ---
#             for img_idx, img in enumerate(page.get_images(full=True)):
#                 xref = img[0]
#                 pix = fitz.Pixmap(doc, xref)
#                 ext = ".jpg" if pix.n < 5 else ".png"
#                 img_path = self.images_root / file_path.stem / f"page_{page_number}_idx_{img_idx}{ext}"
#                 if self.save_image(pix, img_path):
#                     docs.append(Document(
#                         content=f"Hình ảnh: {img_path.name}",
#                         meta={
#                             "category": "image",
#                             "source": str(file_path),
#                             "filename": file_path.name,
#                             "document_id": file_document_id,
#                             "trace": f"Trang {page_number}, Hình ảnh #{img_idx}",
#                             "file_path": str(img_path)
#                         }
#                     ))
#
#         # --- 3) Parse table với pdfplumber ---
#         with pdfplumber.open(file_path) as pdf:
#             for page_number, page in enumerate(pdf.pages, start=1):
#                 tables = page.extract_tables()
#                 for idx, table in enumerate(tables):
#                     if not table:
#                         continue
#                     # Chuyển table thành Markdown
#                     md_lines = []
#                     headers = table[0]
#                     md_lines.append("| " + " | ".join(headers) + " |")
#                     md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
#                     for row in table[1:]:
#                         row += [""] * (len(headers) - len(row))  # đảm bảo đủ cột
#                         md_lines.append("| " + " | ".join(row) + " |")
#                     md_content = "\n".join(md_lines).strip()
#
#                     docs.append(Document(
#                         content=md_content,
#                         meta={
#                             "category": "table",
#                             "source": str(file_path),
#                             "filename": file_path.name,
#                             "document_id": file_document_id,
#                             "trace": f"Table page {page_number} idx {idx}",
#                         }
#                     ))
#
#         return docs
#
# if __name__ == "__main__":
#     import config as cf
#     file_path = cf.DATA_PATH / "Tác động của Biến đổi Khí hậu đến Nông nghiệp Việt Nam.pdf"
#     pdf_path = Path(file_path)
#     images_root = cf.IMAGES_PATH
#     parser = PDFParser(images_root=images_root)
#
#     docs = parser.parse_file(pdf_path)
#
#     for idx, doc in enumerate(docs):
#         print("="*20)
#         print(f"{idx}. category: {doc.meta['category']}")
#         print(f"trace: {doc.meta['trace']}")
#         print(f"content preview: {doc.content}")
#         if doc.meta['category'] == "image":
#             print(f"image path: {doc.meta.get('file_path')}")