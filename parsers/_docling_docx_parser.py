from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import uuid
import re
from collections import defaultdict

# Haystack 2.x
from haystack import Document

# Docling
from docling.document_converter import DocumentConverter
from docling_core.types.doc import TextItem, SectionHeaderItem, TableItem, PictureItem


class DocxParser:
    """
    Docling-only parser cho DOCX:
    - Text: gộp theo Heading (H1/H2/…); nếu không có heading -> fallback gộp theo N đoạn.
    - Table: content = <văn cảnh ngay trước> + Markdown; meta.table_html giữ HTML gốc.
    - Image: lưu file vào images_root/<filename_wo_ext>/img_{i}.png; content = context trước; meta.filepath trỏ tới ảnh.
    - Metadata: category, source, filename, document_id, trace = "Mục {heading_path}" hoặc "Mục ROOT · Nhóm {i}" (fallback).
    """

    # -------------------------
    # Khởi tạo & cấu hình
    # -------------------------
    def __init__(
        self,
        images_root: str | Path = "images",
        context_sentences: int = 3,
        buffer_max_sentences: int = 6,
        fallback_n_paragraphs: int = 10,
    ) -> None:
        self.images_root = Path(images_root)
        self.context_sentences = int(context_sentences)
        self.buffer_max_sentences = int(buffer_max_sentences)
        self.fallback_n_paragraphs = int(fallback_n_paragraphs)
        self.converter = DocumentConverter()  # DOCX không cần PdfPipelineOptions

    # -------------------------
    # Helpers (đưa vào class theo yêu cầu)
    # -------------------------
    _SENT_SPLIT = re.compile(
        r"(?<=[\.!?])\s+(?=[A-ZÀ-Ỵ])|(?<=[\.!\?])\s+(?=\d+)|\n{2,}"
    )

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sents = [
            s.strip() for s in DocxParser._SENT_SPLIT.split(text or "") if s.strip()
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

    @staticmethod
    def _file_document_id(path: Path) -> str:
        st = path.stat()
        seed = f"{path.resolve()}:{st.st_size}:{st.st_mtime_ns}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    # ---- heading helpers ----
    @staticmethod
    def _heading_level(el: SectionHeaderItem) -> int:
        for attr in ("level", "depth", "rank"):
            v = getattr(el, attr, None)
            if isinstance(v, int):
                return v
        return 1

    @staticmethod
    def _push_heading(stack: List[Tuple[int, str]], level: int, text: str) -> None:
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, text.strip()))

    @staticmethod
    def _heading_path(stack: List[Tuple[int, str]]) -> str:
        return " > ".join(h[1] for h in stack) if stack else "ROOT"

    # ---- context & text accumulation ----
    def _context(self, key: str, buffers: Dict[str, List[str]]) -> str:
        buf = buffers.get(key, [])
        return " ".join(buf[-self.context_sentences :]).strip()

    def _push_text(
        self,
        key: str,
        raw_text: str,
        texts: Dict[str, List[str]],
        buffers: Dict[str, List[str]],
    ) -> None:
        text = self._normalize_text(str(raw_text) or "")
        if not text:
            return
        texts.setdefault(key, []).append(text)
        for s in self._split_sentences(text):
            if s:
                buffers.setdefault(key, []).append(s)
        if len(buffers.get(key, [])) > self.buffer_max_sentences:
            buffers[key] = buffers[key][-self.buffer_max_sentences :]

    # ---- table & image helpers ----
    @staticmethod
    def _export_table(el, d) -> tuple[str, str]:
        try:
            md = el.export_to_markdown(doc=d)
        except TypeError:
            md = el.export_to_markdown()
        html = el.export_to_html(doc=d)
        return md, html

    # -------------------------
    # Public API
    # -------------------------
    def parse(self, docx_path: str | Path) -> List[Document]:
        docx_path = Path(docx_path)
        source = str(docx_path.resolve())
        filename = docx_path.name
        fname_wo = docx_path.stem
        document_id = self._file_document_id(docx_path)

        images_dir = self.images_root / fname_wo

        conv_res = self.converter.convert(docx_path)
        d = conv_res.document

        # State
        heading_stack: List[Tuple[int, str]] = []
        section_texts: Dict[str, List[str]] = defaultdict(list)  # key = heading_path
        section_buffers: Dict[str, List[str]] = defaultdict(list)  # key = heading_path
        docs: List[Document] = []
        img_counter = 0
        found_any_heading = False

        # Fallback (no headings): gộp theo N đoạn
        fallback_key = "ROOT"
        fallback_para_count = 0
        fallback_bucket_idx = 0

        for el, _lvl in d.iterate_items():
            # Heading
            if isinstance(el, SectionHeaderItem):
                found_any_heading = True
                level = self._heading_level(el)
                text = getattr(el, "text", "") or ""
                self._push_heading(heading_stack, level, text)
                key = self._heading_path(heading_stack)
                if text.strip():
                    self._push_text(key, text.strip(), section_texts, section_buffers)
                continue

            # Determine current key
            key = (
                self._heading_path(heading_stack) if found_any_heading else fallback_key
            )

            # Text
            if isinstance(el, TextItem) and getattr(el, "text", None):
                self._push_text(
                    key, getattr(el, "text", "") or "", section_texts, section_buffers
                )
                if not found_any_heading:
                    fallback_para_count += 1
                    if fallback_para_count >= self.fallback_n_paragraphs:
                        full_text = "\n\n".join(section_texts[key]).strip()
                        if full_text:
                            docs.append(
                                Document(
                                    content=full_text,
                                    meta={
                                        "category": "text",
                                        "source": source,
                                        "filename": filename,
                                        "document_id": document_id,
                                        "trace": f"Mục {key} · Nhóm {fallback_bucket_idx}",
                                    },
                                )
                            )
                        section_texts[key].clear()
                        section_buffers[key].clear()
                        fallback_para_count = 0
                        fallback_bucket_idx += 1
                continue

            # Table
            if isinstance(el, TableItem):
                ctx = self._context(key, section_buffers)
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
                            "trace": f"Mục {key}",
                            "table_html": html or "",
                        },
                    )
                )
                continue

            # Image
            if isinstance(el, PictureItem):
                try:
                    pil = el.get_image(d)
                except Exception:
                    pil = None
                if pil is None:
                    continue
                # Chỉ tạo thư mục khi thực sự có ảnh để lưu
                images_dir.mkdir(parents=True, exist_ok=True)
                # Chỉ tăng counter sau khi lưu thành công
                next_idx = img_counter + 1
                img_name = f"img_{next_idx}.png"
                img_path = images_dir / img_name
                try:
                    pil.save(img_path, "PNG")
                except Exception:
                    continue
                img_counter = next_idx
                ctx = self._context(key, section_buffers)
                
                # Only create image document if there is meaningful content
                if ctx and ctx.strip():
                    docs.append(
                        Document(
                            content=ctx,
                            meta={
                                "category": "image",
                                "source": source,
                                "filename": filename,
                                "document_id": document_id,
                                "trace": f"Mục {key}",
                                "filepath": str(img_path.resolve()),
                            },
                        )
                    )
                continue

        # Emit remaining text
        if found_any_heading:
            for key in list(section_texts.keys()):
                full_text = "\n\n".join(section_texts[key]).strip()
                if not full_text:
                    continue
                docs.append(
                    Document(
                        content=full_text,
                        meta={
                            "category": "text",
                            "source": source,
                            "filename": filename,
                            "document_id": document_id,
                            "trace": f"Mục {key}",
                        },
                    )
                )
        else:
            if section_texts[fallback_key]:
                full_text = "\n\n".join(section_texts[fallback_key]).strip()
                if full_text:
                    docs.append(
                        Document(
                            content=full_text,
                            meta={
                                "category": "text",
                                "source": source,
                                "filename": filename,
                                "document_id": document_id,
                                "trace": f"Mục {fallback_key} · Nhóm {fallback_bucket_idx}",
                            },
                        )
                    )

        return docs


if __name__ == "__main__":
    import config as cf

    file_path = cf.DATA_PATH / "Đô Thị Hóa.docx"
    parser = DocxParser(images_root=str(cf.IMAGES_PATH))
    docs = parser.parse(str(file_path))
    print(f"Generated {len(docs)} Documents")
    for d in docs:
        print("==========" * 20)
        print("source:\t", d.meta.get("source"))
        print("trace:\t", d.meta.get("trace"))
        print("category:", d.meta.get("category"))
        print("filepath:\t", d.meta.get("filepath"))
        print("content:\n", d.content)
