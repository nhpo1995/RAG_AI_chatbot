from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional
import uuid
import re
from collections import defaultdict

# Haystack 2.x
from haystack import Document

# Docling
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import TextItem, SectionHeaderItem, TableItem, PictureItem


class PdfParser:
    """
    Docling-only parser cho PDF sạch (text-based):
    - Text: gộp theo MỖI TRANG -> 1 Document (category="text").
    - Table: content = <văn cảnh ngay trước> + Markdown; HTML gốc vào meta.table_html.
    - Image: lưu ảnh vào images/<filename_wo_ext>/..., content = <văn cảnh ngay trước>; meta.filepath.
    - Metadata: category, source, filename, document_id, trace="Trang {page}" (ảnh thêm filepath).
    """

    # -------------------------
    # Khởi tạo & cấu hình
    # -------------------------
    def __init__(
        self,
        images_root: str | Path = "images",
        context_sentences: int = 3,
        buffer_max_sentences: int = 6,
        image_scale: float = 2.0,
    ) -> None:
        self.images_root = Path(images_root)
        self.context_sentences = int(context_sentences)
        self.buffer_max_sentences = int(buffer_max_sentences)
        self.image_scale = float(image_scale)
        self.converter = self._make_converter()

    # -------------------------
    # Helpers (giảm trùng lặp – KHÔNG có _meta)
    # -------------------------
    _SENT_SPLIT = re.compile(
        r"(?<=[\.!?])\s+(?=[A-ZÀ-Ỵ])|(?<=[\.!\?])\s+(?=\d+)|\n{2,}"
    )

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sents = [
            s.strip() for s in PdfParser._SENT_SPLIT.split(text or "") if s.strip()
        ]
        return sents or [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    @staticmethod
    def _normalize_text(t: str) -> str:
        if not t:
            return ""
        t = re.sub(r"-\s*\n", "", t)  # gỡ ngắt dòng có gạch nối
        t = t.replace("\u00ad", "")  # bỏ soft-hyphen
        t = re.sub(r"\s*\n\s*", " ", t)  # gom dòng
        t = re.sub(r"\s{2,}", " ", t)  # bóp khoảng trắng
        return t.strip()

    def _make_converter(self) -> DocumentConverter:
        pdf_opts = PdfPipelineOptions()
        pdf_opts.images_scale = self.image_scale
        pdf_opts.generate_picture_images = True  # PictureItem.get_image(...)
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts)}
        )

    @staticmethod
    def _file_document_id(path: Path) -> str:
        st = path.stat()
        seed = f"{path.resolve()}:{st.st_size}:{st.st_mtime_ns}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    @staticmethod
    def _resolve_page_no(el, current_page: Optional[int] = None) -> int:
        """
        Best-effort lấy số trang cho element Docling.
        - el.prov thường là LIST các ProvenanceItem => dùng prov[0].page_no
        - Nếu không có, fallback về current_page
        - Chuẩn hoá về 1-based nếu trả 0-based
        """
        prov = getattr(el, "prov", None)
        page: Optional[int] = None
        if isinstance(prov, list) and len(prov) > 0:
            p = getattr(prov[0], "page_no", None)
            if p is None and isinstance(prov[0], dict):
                p = prov[0].get("page_no")
            if isinstance(p, (int, float)):
                page = int(p)
        elif hasattr(prov, "page_no"):
            p = getattr(prov, "page_no")
            if isinstance(p, (int, float)):
                page = int(p)
        if page is not None:
            return page + 1 if page == 0 else page
        return int(current_page) if current_page is not None else 1

    def _context(self, page_no: int, page_buffers: Dict[int, List[str]]) -> str:
        buf = page_buffers.get(page_no, [])
        return " ".join(buf[-self.context_sentences :]).strip()

    @staticmethod
    def _export_table(el, doc) -> tuple[str, str]:
        try:
            md = el.export_to_markdown(doc=doc)
        except TypeError:
            md = el.export_to_markdown()
        html = el.export_to_html(doc=doc)
        return md, html

    @staticmethod
    def _save_picture(
        el, doc, page_no: int, images_dir: Path, picture_counters: Dict[int, int]
    ) -> Optional[str]:
        try:
            pil = el.get_image(doc)  # PIL.Image
            if pil is None:
                return None
            # Chỉ tạo thư mục khi thực sự có ảnh
            images_dir.mkdir(parents=True, exist_ok=True)
            # Chỉ tăng counter sau khi chắc chắn sẽ lưu
            idx = picture_counters.get(page_no, 0) + 1
            img_name = f"page_{page_no}_img_{idx}.png"
            img_path = images_dir / img_name
            pil.save(img_path, "PNG")
            picture_counters[page_no] = idx  # cập nhật sau khi lưu OK

            return str(img_path.resolve())
        except Exception:
            return None

    def _push_text(
        self,
        page_no: int,
        raw_text: str,
        page_texts: Dict[int, List[str]],
        page_buffers: Dict[int, List[str]],
    ) -> None:
        text = self._normalize_text(str(raw_text) or "")
        if not text:
            return
        page_texts.setdefault(page_no, []).append(text)
        for s in self._split_sentences(text):
            if s:
                page_buffers.setdefault(page_no, []).append(s)
        if len(page_buffers.get(page_no, [])) > self.buffer_max_sentences:
            page_buffers[page_no] = page_buffers[page_no][-self.buffer_max_sentences :]

    # -------------------------
    # Public API
    # -------------------------
    def parse(self, pdf_path: str | Path) -> List[Document]:
        """
        Đọc PDF sạch và trả về danh sách haystack.Document:
          - category="text"  : nội dung cả trang (đã gom)
          - category="table" : context trước + Markdown; meta.table_html giữ HTML gốc
          - category="image" : context trước; meta.filepath trỏ tới ảnh đã lưu
        """
        pdf_path = Path(pdf_path)
        source = str(pdf_path.resolve())
        filename = pdf_path.name
        fname_wo = pdf_path.stem
        document_id = self._file_document_id(pdf_path)

        images_dir = self.images_root / fname_wo

        conv_res = self.converter.convert(pdf_path)
        d = conv_res.document

        # Trạng thái tích luỹ
        page_texts: Dict[int, List[str]] = defaultdict(list)
        page_buffers: Dict[int, List[str]] = defaultdict(list)
        picture_counters: Dict[int, int] = defaultdict(int)
        docs: List[Document] = []
        current_page: Optional[int] = None

        # Duyệt theo reading order
        for el, _lvl in d.iterate_items():
            page_no = self._resolve_page_no(el, current_page)
            current_page = page_no

            # TEXT
            if isinstance(el, (TextItem, SectionHeaderItem)) or getattr(
                el, "text", None
            ):
                self._push_text(
                    page_no, getattr(el, "text", "") or "", page_texts, page_buffers
                )

            # TABLE
            elif isinstance(el, TableItem):
                ctx = self._context(page_no, page_buffers)
                md, html = self._export_table(el, d)
                content = (ctx + "\n\n" if ctx else "") + (md or "")
                docs.append(
                    Document(
                        content=content,
                        meta={
                            "category": "table",
                            "source": source,
                            "filename": filename,
                            "document_id": document_id,
                            "trace": f"Trang {page_no}",
                            "table_html": html or "",
                        },
                    )
                )

            # IMAGE
            elif isinstance(el, PictureItem):
                filepath = self._save_picture(
                    el, d, page_no, images_dir, picture_counters
                )
                if not filepath:
                    continue
                ctx = self._context(page_no, page_buffers)
                docs.append(
                    Document(
                        content=ctx,
                        meta={
                            "category": "image",
                            "source": source,
                            "filename": filename,
                            "document_id": document_id,
                            "trace": f"Trang {page_no}",
                            "filepath": filepath,
                        },
                    )
                )

            # các loại phần tử khác: bỏ qua

        # 1 Document "text" cho mỗi trang
        for page_no in sorted(page_texts.keys()):
            full_page_text = "\n\n".join(page_texts[page_no]).strip()
            if not full_page_text:
                continue
            docs.append(
                Document(
                    content=full_page_text,
                    meta={
                        "category": "text",
                        "source": source,
                        "filename": filename,
                        "document_id": document_id,
                        "trace": f"Trang {page_no}",
                    },
                )
            )

        return docs


# --- ví dụ dùng với config (không sys.argv) ---
if __name__ == "__main__":
    import config as cf

    file_path = cf.DATA_PATH / "Market_Insights_AI_Report-2025.pdf"
    parser = PdfParser(images_root=str(cf.IMAGES_PATH))
    docs = parser.parse(str(file_path))
    print(f"Generated {len(docs)} Documents")
    for d in docs:
        print("==========" * 20)
        print("source:\t", d.meta.get("source"))
        print("trace:\t", d.meta.get("trace"))
        print("category:", d.meta.get("category"))
        print("filepath:\t", d.meta.get("filepath"))
        print("content:\n", d.content)
