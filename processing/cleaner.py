from haystack import Document
from haystack.components.preprocessors import DocumentCleaner
from typing import List, Optional, Literal, Dict, Any

class DocumentCleanerWrapper:
    """
    Wrapper cho DocumentCleaner của Haystack.
    Giữ nguyên bảng (category='table'), chỉ làm sạch các loại tài liệu khác.
    """
    def __init__(self, cleaner: Optional[DocumentCleaner] = None):
        if cleaner is None:
            # Tạo cleaner mặc định
            self.cleaner = DocumentCleaner(
                remove_empty_lines=True,
                remove_extra_whitespaces=True,
                remove_repeated_substrings=False,
                keep_id=True,
            )
        else:
            self.cleaner = cleaner

    def run(self, documents: List[Document]) -> List[Document]:
        """Làm sạch văn bản, giữ nguyên bảng, bảo toàn thứ tự tài liệu."""
        cleaned_docs = []
        other_docs = []
        table_positions = {}

        # Phân loại và ghi nhớ vị trí
        for i, d in enumerate(documents):
            if d.meta.get("category") == "table":
                table_positions[i] = d
            else:
                other_docs.append(d)

        # Làm sạch docs không phải bảng
        cleaned_result = self.cleaner.run(documents=other_docs)
        cleaned_iter = iter(cleaned_result["documents"])

        # Ghép lại đúng thứ tự ban đầu
        for i in range(len(documents)):
            if i in table_positions:
                cleaned_docs.append(table_positions[i])
            else:
                cleaned_docs.append(next(cleaned_iter))

        return cleaned_docs