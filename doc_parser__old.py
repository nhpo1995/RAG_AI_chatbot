# doc_parser.py
import base64
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from bs4 import BeautifulSoup
from haystack import Document
from haystack_integrations.components.converters.unstructured import UnstructuredFileConverter

class DocParser:
    def __init__(
        self,
        api_url="http://localhost:8000/general/v0/general",
        images_root=Path("images"),
        text_categories:Set[str]=None,
        unstructured_kwargs: Optional[Dict[str, Any]]=None
    ):
        self.api_url = api_url
        self.images_root = Path(images_root)
        self.images_root.mkdir(exist_ok=True)
        self.text_categories = text_categories or {"Title", "NarrativeText"}
        self.stats: Optional[Dict[str, int]] = None
        self.file_stats: Dict[str, Dict[str, int]] = None
        self.unstructured_kwargs = unstructured_kwargs or {
            "encoding": "utf-8",
            "extract_image_block_types": ["Image", "Table"],
            "languages": ["vie", "eng"],
            "skip_infer_table_types": [],
            "strategy": "hi_res",
        }

    # ---------------- Helpers ----------------
    def is_text_block(self, doc: Document) -> bool:
        return doc.meta.get("category") in self.text_categories

    def nearest_text(self, blocks, idx, direction: int) -> str:
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
        if table is None:
            return soup.get_text(separator=" ").strip()
        headers, rows = [], []
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        tbody = table.find("tbody")
        target_rows = tbody.find_all("tr") if tbody else table.find_all("tr")
        for tr in target_rows:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            rows.append(cells)
        md_lines = []
        if headers:
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in rows:
            if headers and len(r) < len(headers):
                r += [""] * (len(headers) - len(r))
            md_lines.append("| " + " | ".join(r) + " |")
        return "\n".join(md_lines).strip()

    def process_table_block(self,
                            blocks,
                            idx,
                            file_path: Path,
                            is_in_image=False,
                            file_document_id=None,
                            ) -> Document:
        d = blocks[idx]
        if "text_as_html" in d.meta:
            md = self.html_table_to_markdown(d.meta["text_as_html"])
        else:
            md = (d.content or "").strip()

        prev_txt = self.nearest_text(blocks, idx, -1)
        if prev_txt:
            md = prev_txt + md

        return Document(
            content=md,
            meta={
                "category": "table",
                "source": str(file_path),
                "filename": file_path.name,
                "document_id": file_document_id,
                "page_number": d.meta.get("page_number"),
                "element_index": d.meta.get("element_index"),
                "from_image": is_in_image
            },
        )

    # ---------------- Core ----------------
    def parse_file(self, file_path: Path) -> List[Document]:
        file_document_id = str(uuid.uuid4())
        converter = UnstructuredFileConverter(
            api_url=self.api_url,
            document_creation_mode="one-doc-per-element",
            separator="\n\n",
            progress_bar=False,
            unstructured_kwargs= self.unstructured_kwargs
        )

        result = converter.run(paths=[file_path])
        blocks = result["documents"]

        # 1) Text
        all_text_parts = [d.content.strip() for d in blocks if self.is_text_block(d) and d.content]
        merged_text_content = "\n\n".join(all_text_parts).strip()
        text_doc = Document(
            content=merged_text_content,
            meta={
                "category": "text",
                "source": str(file_path),
                "filename": file_path.name,
                "document_id": file_document_id,
            }
        )

        # 2) Image
        image_docs = []
        for idx, d in enumerate(blocks):
            if d.meta.get("category") == "Image" and "image_base64" in d.meta:
                images_dir = self.images_root / file_path.stem
                images_dir.mkdir(exist_ok=True)

                mime = d.meta.get("image_mime_type") or "image/png"
                ext = ".jpg" if "jpeg" in mime or "jpg" in mime else ".png"
                page = d.meta.get("page_number", "x")
                elidx = d.meta.get("element_index", idx)
                img_path = images_dir / f"page_{page}_idx_{elidx}{ext}"

                try:
                    img_bytes = base64.b64decode(d.meta["image_base64"])
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                except Exception:
                    img_path = Path("")

                prev_txt = self.nearest_text(blocks, idx, -1)
                next_txt = self.nearest_text(blocks, idx, +1)
                context = (prev_txt + ("\n\n" if prev_txt and next_txt else "") + next_txt).strip()

                image_docs.append(
                    Document(
                        content=f"Hình ảnh: {context}" if context else "Hình ảnh:",
                        meta={
                            "category": "image",
                            "file_path": str(img_path) if img_path else "",
                            "source": str(file_path),
                            "filename": file_path.name,
                            "document_id": file_document_id,
                            "page_number": d.meta.get("page_number"),
                            "element_index": d.meta.get("element_index"),
                        },
                    )
                )

        # 3) Table
        table_docs = []
        for idx, d in enumerate(blocks):
            if d.meta.get("category") == "Table":
                table_docs.append(self.process_table_block(blocks, idx, file_path, file_document_id=file_document_id))
            elif d.meta.get("category") == "Image" and "text_as_html" in d.meta:
                table_docs.append(self.process_table_block(blocks, idx, file_path,file_document_id=file_document_id, is_in_image=True))

        # Merge
        final_docs = []
        if merged_text_content and file_path.suffix.lower() not in [".xls", ".xlsx"]:
            final_docs.append(text_doc)
        final_docs.extend(image_docs)
        final_docs.extend(table_docs)
        # Thống kê
        stats = {
            "text": sum(1 for d in final_docs if d.meta.get("category") == "text"),
            "image": sum(1 for d in final_docs if d.meta.get("category") == "image"),
            "table": sum(1 for d in final_docs if d.meta.get("category") == "table"),
        }
        self.stats = stats
        return final_docs

    def parse_folder(self, folder_path: Path) -> List[Document]:
        all_docs = []
        self.file_stats = {}
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                docs = self.parse_file(file_path)
                self.file_stats[file_path.name] = self.stats
                all_docs.extend(docs)
        return all_docs
