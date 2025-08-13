from haystack import Document
from haystack.components.preprocessors import DocumentSplitter
from typing import List, Optional, Literal
from nltk.corpus import reuters


class DocumentChunkerWrapper:
    def __init__(self, chunker: Optional[DocumentSplitter] = None):
        if chunker is None:
            self.chunker = DocumentSplitter(
                split_by="word",
                split_length=350,
                split_overlap=45,
                split_threshold=0,
                respect_sentence_boundary=True,
                skip_empty_documents=True,
            )
        else:
            self.chunker = chunker

    def chunk_table(self, doc: Document) -> List[Document]:
        """
        Chunk bảng theo header + nhóm row (ví dụ: 20 hàng một chunk)
        """
        lines = doc.content.strip().split("\n")
        if not lines:
            return [doc]

        header = lines[0]
        rows = lines[1:]

        chunk_size = 15  # số hàng mỗi chunk
        table_chunks = []

        for i in range(0, len(rows), chunk_size):
            chunk_rows = rows[i:i + chunk_size]
            chunk_content = header + "\n" + "\n".join(chunk_rows)
            table_chunks.append(
                Document(content=chunk_content, meta=doc.meta.copy())
            )

        return table_chunks

    def run(self, documents: List[Document] = None) -> List[Document]:
        """
            Đối với text: Split bình thường,
            Đối với image: bỏ qua
            Đối với table:
             - Tách table theo cụm row + header
        :param documents:
        :return:
        """
        final_chunks = []
        for doc in documents:
            category = doc.meta.get("category")
            if category == "text":
                # Chunk text bình thường
                result = self.text_splitter.run(documents=[doc])
                final_chunks.extend(result["documents"])
            elif category == "table":
                # Chunk bảng
                final_chunks.extend(self.chunk_table(doc))
            elif category == "image":
                # Giữ nguyên ảnh
                final_chunks.append(doc)
            else:
                # Loại khác → giữ nguyên
                final_chunks.append(doc)
        return final_chunks

