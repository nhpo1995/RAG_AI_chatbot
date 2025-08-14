from typing import List, Dict, Any
from haystack import Document


class QdrantWriter:
    def __init__(self, document_store):
        self.document_store = document_store

    def run(self, documents: List[Document]) -> Dict[str, Any]:
        if documents:
            self.document_store.write_documents(documents)
        return {}
