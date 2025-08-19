import uuid
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
import pdfplumber
from haystack import Document
import re


class PDFParser:
    def __init__(self, images_root: Path = Path("images")):
        self.images_root = images_root
        self.images_root.mkdir(exist_ok=True)
        self.text_categories = {"Title", "NarrativeText"}

    @staticmethod
    def _save_image(pix: fitz.Pixmap, out_path: Path) -> bool:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if pix.n < 5:
                pix.save(str(out_path))
            else:
                pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(str(out_path))
            return True
        except Exception as e:
            print(f"Failed to save image: {e}")
            return False

    @staticmethod
    def extract_captions(text: str) -> Tuple[str, List[str], List[str]]:
        """
        Tách các dòng caption (ví dụ: 'Hình 1:', 'Bảng 2:', 'Image 1:', 'Table 2:')
        Trả về:
        - text đã loại bỏ caption
        - danh sách caption hình
        - danh sách caption bảng
        """
        image_captions = []
        table_captions = []
        cleaned_lines = []

        # Regex hỗ trợ cả tiếng Việt và tiếng Anh
        image_pattern = re.compile(r"^(Hình|Image)\s*\d+[:.\-]?\s*(.*)$", re.IGNORECASE)
        table_pattern = re.compile(r"^(Bảng|Table)\s*\d+[:.\-]?\s*(.*)$", re.IGNORECASE)

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            if image_match := image_pattern.match(stripped):
                caption = image_match.group(0)
                image_captions.append(caption)
            elif table_match := table_pattern.match(stripped):
                caption = table_match.group(0)
                table_captions.append(caption)
            else:
                cleaned_lines.append(stripped)

        cleaned_text = "\n".join(cleaned_lines)
        return cleaned_text, image_captions, table_captions

    def is_text_block(self, doc: Document) -> bool:
        return doc.meta.get("category") in self.text_categories

    def nearest_text(self, blocks: List[Document], idx: int, direction: int) -> str:
        j = idx + direction
        while 0 <= j < len(blocks):
            if self.is_text_block(blocks[j]):
                return (blocks[j].content or "").strip()
            j += direction
        return ""

    @staticmethod
    def generate_markdown_table(table: List[List[str]]) -> str:
        def clean_cell(cell: str) -> str:
            return cell.replace("\n", " ").replace("|", "\\|").strip()

        if not table:
            return ""

        headers = table[0]
        md_lines = []
        md_lines.append("| " + " | ".join(clean_cell(h) for h in headers) + " |")
        md_lines.append("| " + " | ".join("---" for _ in headers) + " |")

        for row in table[1:]:
            row += [""] * (len(headers) - len(row))
            md_lines.append("| " + " | ".join(clean_cell(c) for c in row) + " |")

        return "\n".join(md_lines)

    def parse_file(self, file_path: Path) -> List[Document]:
        file_document_id = str(uuid.uuid4())
        docs: List[Document] = []

        # --- Parse tables (get bbox) ---
        table_bboxes_by_page = {}
        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                bboxes = []
                for table in page.find_tables():
                    if table.bbox:
                        bboxes.append(table.bbox)
                if bboxes:
                    table_bboxes_by_page[page_number] = bboxes

        # --- Parse text with PyMuPDF ---
        captions_by_page = {}  # lưu caption tách ra theo page
        doc = fitz.open(file_path)
        for page_number, page in enumerate(doc, start=1):
            table_bboxes = table_bboxes_by_page.get(page_number, [])
            text_blocks = page.get_text("blocks")
            cleaned_texts = []

            for b in text_blocks:
                bbox = b[:4]
                text = b[4].strip()
                if not text:
                    continue

                # Bỏ block nằm trong bảng
                in_table = False
                for tbbox in table_bboxes:
                    if (
                        bbox[0] >= tbbox[0]
                        and bbox[1] >= tbbox[1]
                        and bbox[2] <= tbbox[2]
                        and bbox[3] <= tbbox[3]
                    ):
                        in_table = True
                        break
                if not in_table:
                    cleaned_texts.append(text)

            merged_text = "\n".join(cleaned_texts).strip()
            merged_text, image_captions, table_captions = self.extract_captions(
                merged_text
            )
            captions_by_page[page_number] = {
                "image": image_captions,
                "table": table_captions,
            }

            if merged_text:
                docs.append(
                    Document(
                        content=merged_text,
                        meta={
                            "category": "text",
                            "source": str(file_path),
                            "filename": file_path.name,
                            "document_id": file_document_id,
                            "trace": f"Trang {page_number}",
                        },
                    )
                )

            # --- Parse image ---
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                ext = ".jpg" if pix.n < 5 else ".png"
                img_path = (
                    self.images_root
                    / file_path.stem
                    / f"page_{page_number}_idx_{img_idx}{ext}"
                )

                if self.save_image(pix, img_path):
                    captions = captions_by_page.get(page_number, {}).get("image", [])
                    caption = captions[img_idx] if img_idx < len(captions) else ""
                    context = caption.strip()
                    content = f"Hình ảnh: {img_path.name}"
                    if context:
                        content = f"{content}\n\nContext:\n{context}"
                    docs.append(
                        Document(
                            content=content,
                            meta={
                                "category": "image",
                                "source": str(file_path),
                                "filename": file_path.name,
                                "document_id": file_document_id,
                                "trace": f"Trang {page_number}, Hình ảnh #{img_idx}",
                                "file_path": str(img_path),
                            },
                        )
                    )

        # --- Parse table content ---
        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for idx, table in enumerate(tables):
                    if not table:
                        continue

                    md_content = self.generate_markdown_table(table)
                    captions = captions_by_page.get(page_number, {}).get("table", [])
                    caption = captions[idx] if idx < len(captions) else ""
                    full_content = md_content
                    if caption:
                        full_content = f"{caption}\n\n{md_content}"

                    docs.append(
                        Document(
                            content=full_content,
                            meta={
                                "category": "table",
                                "source": str(file_path),
                                "filename": file_path.name,
                                "document_id": file_document_id,
                                "trace": f"Table page {page_number} idx {idx}",
                            },
                        )
                    )

        return docs


# --- TEST ---
if __name__ == "__main__":
    import config as cf

    file_path = (
        cf.DATA_PATH / "Tác động của Biến đổi Khí hậu đến Nông nghiệp Việt Nam.pdf"
    )
    parser = PDFParser(images_root=cf.IMAGES_PATH)

    docs = parser.parse_file(file_path)

    for idx, doc in enumerate(docs):
        print("=" * 20)
        print(f"{idx}. category: {doc.meta['category']}")
        print(f"trace: {doc.meta['trace']}")
        print(f"content preview: {doc.content}")
        if doc.meta["category"] == "image":
            print(f"image path: {doc.meta.get('file_path')}")
