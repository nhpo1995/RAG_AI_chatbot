from __future__ import annotations
from pathlib import Path
from typing import List
import uuid
import re

# Haystack 2.x
from haystack import Document


class TxtParser:
    """
    Parser cho .txt (plain text):
    - Gộp text theo khối (N đoạn hoặc max ký tự).
    - Không có table/image.
    - Metadata: category="text", source, filename, document_id, trace="Khối {i}".
    """

    def __init__(
        self,
        group_max_paragraphs: int = 10,
        group_max_chars: int = 4000,
        encoding_candidates: List[str] | None = None,
    ) -> None:
        self.group_max_paragraphs = int(group_max_paragraphs)
        self.group_max_chars = int(group_max_chars)
        self.encoding_candidates = encoding_candidates or ["utf-8-sig", "utf-8", "utf-16", "cp1258", "latin-1"]

    # --- helpers (đưa vào class) ---
    _PARA_SPLIT = re.compile(r"\n\s*\n+", flags=re.MULTILINE)
    _SENT_SPLIT = re.compile(r"(?<=[\.!?])\s+(?=[A-ZÀ-Ỵ])|(?<=[\.!\?])\s+(?=\d+)|\n{2,}")

    @staticmethod
    def _normalize_text(t: str) -> str:
        if not t:
            return ""
        t = re.sub(r"-\s*\n", "", t)
        t = t.replace("\u00ad", "")
        t = re.sub(r"\s*\n\s*", " ", t)
        t = re.sub(r"\s{2,}", " ", t)
        return t.strip()

    @staticmethod
    def _file_document_id(path: Path) -> str:
        st = path.stat()
        seed = f"{path.resolve()}:{st.st_size}:{st.st_mtime_ns}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    def _read_text(self, path: Path) -> str:
        last_err = None
        for enc in self.encoding_candidates:
            try:
                return path.read_text(encoding=enc)
            except Exception as e:
                last_err = e
        # cuối cùng đọc binary rồi decode lỗi bỏ qua
        data = path.read_bytes()
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            if last_err:
                raise last_err
            return data.decode(errors="ignore")

    # --- public API ---
    def parse(self, txt_path: str | Path) -> List[Document]:
        txt_path = Path(txt_path)
        source = str(txt_path.resolve())
        filename = txt_path.name
        document_id = self._file_document_id(txt_path)

        raw = self._read_text(txt_path)
        # tách đoạn — coi 1+ dòng trống là ranh giới
        paras = [self._normalize_text(p) for p in self._PARA_SPLIT.split(raw) if self._normalize_text(p)]
        if not paras:
            return []

        docs: List[Document] = []
        bucket, bucket_chars, bucket_idx = [], 0, 0

        def flush():
            nonlocal bucket, bucket_chars, bucket_idx
            if not bucket:
                return
            content = "\n\n".join(bucket).strip()
            if content:
                docs.append(Document(
                    content=content,
                    meta={
                        "category": "text",
                        "source": source,
                        "filename": filename,
                        "document_id": document_id,
                        "trace": f"Khối {bucket_idx + 1}",
                    },
                ))
            bucket, bucket_chars = [], 0
            bucket_idx += 1

        for p in paras:
            if (len(bucket) >= self.group_max_paragraphs) or (bucket_chars + len(p) > self.group_max_chars):
                flush()
            bucket.append(p)
            bucket_chars += len(p)

        flush()
        return docs


if __name__ == "__main__":
    import config as cf
    file_path = cf.DATA_PATH / "kinh-te-vi-mo-vn-2025.txt"
    parser = TxtParser()
    docs = parser.parse(str(file_path))
    print(f"Generated {len(docs)} Documents")
    for d in docs:
        print("==========" * 20)
        print("source:\t", d.meta.get("source"))
        print("trace:\t", d.meta.get("trace"))
        print("category:", d.meta.get("category"))
        print("content:\n", d.content)