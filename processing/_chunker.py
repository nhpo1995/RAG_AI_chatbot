from typing import List, Optional, Dict, Any
from haystack import Document
from haystack.components.preprocessors import DocumentSplitter


class DocumentChunkerWrapper:
    def __init__(self, chunker: Optional[DocumentSplitter] = None):
        if chunker is None:
            self.chunker = DocumentSplitter(
                split_by="word",
                split_length=350,
                split_overlap=45,
                respect_sentence_boundary=True,
            )
            self.chunker.warm_up()
        else:
            self.chunker = chunker
            self.chunker.warm_up()

    def chunk_table(self, doc: Document) -> List[Document]:
        """
        Chunk bảng theo header + nhóm row (ví dụ: 15 hàng một chunk)
        """
        lines = doc.content.strip().split("\n")
        if not lines:
            return [doc]
        header = lines[0]
        rows = lines[1:]
        chunk_size = 15
        table_chunks = []
        for i in range(0, len(rows), chunk_size):
            chunk_rows = rows[i:i + chunk_size]
            chunk_content = header + "\n" + "\n".join(chunk_rows)
            table_chunks.append(
                Document(content=chunk_content, meta=doc.meta.copy())
            )
        return table_chunks

    def run(self, documents: List[Document]) -> List[Document]:
        """
        Đối với text: Split bình thường
        Đối với table: Tách table theo cụm row + header
        Đối với image và loại khác: Giữ nguyên
        """
        final_chunks = []
        text_docs_to_split = []
        for doc in documents:
            category = doc.meta.get("category")
            if category == "text":
                text_docs_to_split.append(doc)
            elif category == "table":
                final_chunks.extend(self.chunk_table(doc))
            else:  # Image và các loại khác
                final_chunks.append(doc)
        # Chunk tất cả các text doc cùng lúc để tối ưu
        if text_docs_to_split:
            result = self.chunker.run(documents=text_docs_to_split)
            final_chunks.extend(result["documents"])

        return final_chunks