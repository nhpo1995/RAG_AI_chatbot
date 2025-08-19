import base64
import uuid
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional, Set, Any, Tuple
from bs4 import BeautifulSoup
from haystack import Document
from haystack_integrations.components.converters.unstructured import (
    UnstructuredFileConverter,
)
from config import API_URL_UNSTRUCTURED, IMAGES_PATH, DATA_PATH


class DocParser:
    """
    Bộ parser trích xuất text, image, table từ file (PDF, DOCX, XLSX, ...).
    Tự động lưu ảnh ra local và tạo document_id riêng cho mỗi file.
    """

    def __init__(
        self,
        api_url: str = API_URL_UNSTRUCTURED,
        images_root: Path = IMAGES_PATH,
        text_categories: Set[str] = None,
        unstructured_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.api_url = api_url
        self.images_root = images_root
        self.images_root.mkdir(exist_ok=True)
        self.text_categories = text_categories or {"Title", "NarrativeText"}
        default_unstructured_kwargs = {
            "encoding": "utf-8",
            "extract_image_block_types": ["Image", "Table"],
            "languages": ["vie", "eng"],
            "skip_infer_table_types": ["html"],
            "strategy": "hi_res",
        }
        if unstructured_kwargs:
            default_unstructured_kwargs.update(unstructured_kwargs)
        self.unstructured_kwargs = default_unstructured_kwargs
        self.converter = UnstructuredFileConverter(
            api_url=self.api_url,
            document_creation_mode="one-doc-per-element",
            separator="\n\n",
            progress_bar=False,
            unstructured_kwargs=self.unstructured_kwargs,
        )

    # ---------------- commons ----------------
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
    def html_table_to_markdown(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return soup.get_text(separator=" ").strip()
        rows = []
        thead = table.find("thead")
        headers = (
            [th.get_text(strip=True) for th in thead.find_all("th")] if thead else []
        )
        tbody = table.find("tbody")
        trs = tbody.find_all("tr") if tbody else table.find_all("tr")

        for i, tr in enumerate(trs):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if not headers and i == 0:
                headers = cells  # lấy hàng đầu tiên làm header
                continue
            rows.append(cells)
        md_lines = []
        if headers:
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in rows:
            r += [""] * (len(headers) - len(r))  # đảm bảo đủ cột
            md_lines.append("| " + " | ".join(r) + " |")

        return "\n".join(md_lines).strip()

    def process_table_block(
        self,
        blocks: List[Document],
        idx: int,
        file_path: Path,
        file_document_id: str,
        is_in_image: bool = False,
    ) -> Document:
        d = blocks[idx]
        if "text_as_html" in d.meta:
            md = self.html_table_to_markdown(d.meta["text_as_html"])
        else:
            md = (d.content or "").strip()
        prev_txt = self.nearest_text(blocks, idx, -1)
        if prev_txt:
            md = f"{prev_txt}\n\n{md}"
        sheet_name = d.meta.get("sheet_name")
        index = d.meta.get("element_index")
        page_num = d.meta.get("page_number")
        if sheet_name:
            trace = f"Table in sheet {sheet_name} with index {index}"
        else:
            trace = f"Table in page {page_num} with index {index}"
        return Document(
            content=md,
            meta={
                "category": "table",
                "source": str(file_path),
                "filename": file_path.name,
                "document_id": file_document_id,
                "trace": trace,
                "from_image": is_in_image,
            },
        )

    @staticmethod
    def save_image(image_base64: str, out_path: Path) -> bool:
        try:
            img_bytes = base64.b64decode(image_base64)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(img_bytes)
            return True
        except Exception:
            return False

    # ---------------- Core ----------------
    def parse_file(self, file_path: Path) -> List[Document]:
        file_document_id = str(uuid.uuid4())
        result = self.converter.run(paths=[str(file_path)])
        blocks = result["documents"]
        # 1) Xử lý Text với 'trace'
        text_docs = []
        # Tách riêng text có page_number và text không có page_number (như file Word)
        paged_texts = defaultdict(list)
        unpaged_texts = []

        for d in blocks:
            if self.is_text_block(d) and d.content:
                page_number = d.meta.get("page_number")
                if page_number is not None:
                    paged_texts[page_number].append(d.content.strip())
                else:
                    unpaged_texts.append(d.content.strip())

        # Tạo doc cho text có phân trang (PDF)
        for page_number, page_texts in paged_texts.items():
            merged_page_content = "\n\n".join(page_texts).strip()
            if merged_page_content:
                text_docs.append(
                    Document(
                        content=merged_page_content,
                        meta={
                            "category": "text",
                            "source": str(file_path),
                            "filename": file_path.name,
                            "document_id": file_document_id,
                            "trace": f"Trang {page_number}",  # <-- Thay thế page_number bằng trace
                        },
                    )
                )
        # Tạo một doc duy nhất cho text không phân trang (Word, TXT...)
        if unpaged_texts:
            merged_unpaged_content = "\n\n".join(unpaged_texts).strip()
            if merged_unpaged_content:
                text_docs.append(
                    Document(
                        content=merged_unpaged_content,
                        meta={
                            "category": "text",
                            "source": str(file_path),
                            "filename": file_path.name,
                            "document_id": file_document_id,
                            "trace": "Nội dung văn bản",  # <-- Trace chung cho file không có trang
                        },
                    )
                )
        # 2) Xử lý Image
        image_docs = []
        for idx, d in enumerate(blocks):
            if d.meta.get("category") == "Image" and "image_base64" in d.meta:
                images_dir = self.images_root / file_path.stem
                mime = d.meta.get("image_mime_type", "image/png")
                ext = ".jpg" if "jpeg" in mime or "jpg" in mime else ".png"
                page = d.meta.get("page_number", "x")
                trace = f"Trang {page}, Hình ảnh #{idx}" if page else f"Hình ảnh #{idx}"
                img_path = images_dir / f"page_{page}_idx_{idx}{ext}"
                if self.save_image(d.meta["image_base64"], img_path):
                    prev_txt = self.nearest_text(blocks, idx, -1)
                    next_txt = self.nearest_text(blocks, idx, 1)
                    context = (
                        f"{prev_txt}\n\n{next_txt}"
                        if prev_txt and next_txt
                        else prev_txt or next_txt
                    ).strip()

                    image_docs.append(
                        Document(
                            content=f"Hình ảnh: {context}" if context else "Hình ảnh:",
                            meta={
                                "category": "image",
                                "file_path": str(img_path),
                                "source": str(file_path),
                                "filename": file_path.name,
                                "document_id": file_document_id,
                                "trace": trace,
                            },
                        )
                    )
        # 3) Xử lý Table
        table_docs = []
        for idx, d in enumerate(blocks):
            category = d.meta.get("category")
            if category == "Table":
                table_doc = self.process_table_block(
                    blocks, idx, file_path, file_document_id
                )
                table_docs.append(table_doc)
            elif category == "Image" and "text_as_html" in d.meta:
                table_doc = self.process_table_block(
                    blocks, idx, file_path, file_document_id, is_in_image=True
                )
                table_docs.append(table_doc)
        # 4) Gộp tất cả kết quả và thống kê
        final_docs = []
        final_docs.extend(text_docs)
        final_docs.extend(image_docs)
        final_docs.extend(table_docs)
        stats = {
            "text": len(text_docs),
            "image": len(image_docs),
            "table": len(table_docs),
        }
        return final_docs

    def run(self, folder_path: Path) -> List[Document]:
        all_docs = []
        # Lọc chỉ lấy file, bỏ qua thư mục con hoặc file ẩn như .DS_Store
        files = [
            f
            for f in folder_path.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
        files.sort()
        for file_path in files:
            try:
                print(f"Parsing file: {file_path.name}")  # For debug
                docs = self.parse_file(file_path)
                all_docs.extend(docs)
            except Exception as e:
                print(f"Lỗi khi xử lý file {file_path.name}: {e}")
        return all_docs


if __name__ == "__main__":
    import config as cf

    parser = DocParser()
    file_path = cf.DATA_PATH / "Đô Thị Hóa.docx"
    all_docs = parser.parse_file(file_path)
    for idx, doc in enumerate(all_docs):
        print(20 * "===")
        print(f"{idx}. filename= {doc.meta['filename']}")
        print(f"content: {doc.content}")
        print(f"Page number: {doc.meta['trace']}")
