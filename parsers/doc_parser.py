import base64
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Set, Any, Tuple
from bs4 import BeautifulSoup
from haystack import Document
from haystack_integrations.components.converters.unstructured import UnstructuredFileConverter
from config import API_URL_UNSTRUCTURED

class DocParser:
    """
    Bộ parser trích xuất text, image, table từ file (PDF, DOCX, XLSX, ...).
    Tự động lưu ảnh ra local và tạo document_id riêng cho mỗi file.
    """
    def __init__(
            self,
            api_url: str = API_URL_UNSTRUCTURED,
            images_root: Path = Path("images"),
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
            "skip_infer_table_types": [],
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
            unstructured_kwargs=self.unstructured_kwargs
        )
        self.file_stats: Dict[str, Dict[str, int]] = {}

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
        headers, rows = [], []
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        tbody = table.find("tbody")
        target_rows = tbody.find_all("tr") if tbody else table.find_all("tr")
        for tr in target_rows:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td"])]
            rows.append(cells)
        rows = [r for r in rows if any(cell for cell in r)]
        if not headers and rows:  # Nếu không có thead, lấy hàng đầu tiên làm header
            headers = rows.pop(0)
        md_lines = []
        if headers:
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in rows:
            # Đảm bảo số cột khớp với header
            r.extend([""] * (len(headers) - len(r)))
            md_lines.append("| " + " | ".join(r) + " |")
        return "\n".join(md_lines).strip()

    def process_table_block(self, blocks: List[Document], idx: int, file_path: Path, file_document_id: str,
        is_in_image: bool = False) -> Document:
        d = blocks[idx]
        md = self.html_table_to_markdown(d.meta.get("text_as_html", d.content or ""))
        prev_txt = self.nearest_text(blocks, idx, -1)
        if prev_txt:
            md = f"{prev_txt}\n\n{md}"
        return Document(
            content=md,
            meta={
                "category": "table",
                "source": str(file_path),
                "filename": file_path.name,
                "document_id": file_document_id,
                "page_number": d.meta.get("page_number"),
                "element_index": d.meta.get("element_index"),
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
    def parse_file(self, file_path: Path) -> Tuple[List[Document], Dict[str, int]]:
        file_document_id = str(uuid.uuid4())
        result = self.converter.run(paths=[file_path])
        blocks = result["documents"]
        final_docs: List[Document] = []
        for idx, d in enumerate(blocks):
            category = d.meta.get("category")
            # 1) Xử lý Text
            if self.is_text_block(d) and d.content:
                # Logic bỏ qua text từ file Excel
                if file_path.suffix.lower() not in [".xls", ".xlsx"]:
                    final_docs.append(Document(
                        content=d.content.strip(),
                        meta={
                            "category": "text",
                            "source": str(file_path),
                            "filename": file_path.name,
                            "document_id": file_document_id,
                            "page_number": d.meta.get("page_number"),
                            "element_index": d.meta.get("element_index"),
                        }
                    ))
            # 2) Xử lý Image
            elif category == "Image" and "image_base64" in d.meta:
                images_dir = self.images_root / file_path.stem
                mime = d.meta.get("image_mime_type", "image/png")
                ext = ".jpg" if "jpeg" in mime or "jpg" in mime else ".png"
                page = d.meta.get("page_number", "x")
                img_path = images_dir / f"page_{page}_idx_{idx}{ext}"
                if self.save_image(d.meta["image_base64"], img_path):
                    prev_txt = self.nearest_text(blocks, idx, -1)
                    next_txt = self.nearest_text(blocks, idx, 1)
                    context = (f"{prev_txt}\n\n{next_txt}" if prev_txt and next_txt else prev_txt or next_txt).strip()
                    final_docs.append(Document(
                        content=f"Hình ảnh: {context}" if context else "Hình ảnh.",
                        meta={
                            "category": "image",
                            "file_path": str(img_path),
                            "source": str(file_path),
                            "filename": file_path.name,
                            "document_id": file_document_id,
                            "page_number": d.meta.get("page_number"),
                            "element_index": d.meta.get("element_index"),
                        },
                    ))
                # Xử lý trường hợp table nằm bên trong ảnh
                if "text_as_html" in d.meta:
                    final_docs.append(
                        self.process_table_block(blocks, idx, file_path, file_document_id, is_in_image=True)
                    )
            # 3) Xử lý Table
            elif category == "Table":
                final_docs.append(
                    self.process_table_block(blocks, idx, file_path, file_document_id)
                )
        # Thống kê
        stats = {
            "text": sum(1 for d in final_docs if d.meta.get("category") == "text"),
            "image": sum(1 for d in final_docs if d.meta.get("category") == "image"),
            "table": sum(1 for d in final_docs if d.meta.get("category") == "table"),
        }
        return final_docs, stats

    def parse_folder(self, folder_path: Path) -> List[Document]:
        all_docs = []
        self.file_stats = {}
        # Lọc chỉ lấy file, bỏ qua thư mục con hoặc file ẩn như .DS_Store
        files = [f for f in folder_path.iterdir() if f.is_file() and not f.name.startswith('.')]

        for file_path in files:
            try:
                # print(f"Parsing file: {file_path.name}") # Bỏ comment để debug
                docs, stats = self.parse_file(file_path)
                self.file_stats[file_path.name] = stats
                all_docs.extend(docs)
            except Exception as e:
                print(f"Lỗi khi xử lý file {file_path.name}: {e}")
        return all_docs