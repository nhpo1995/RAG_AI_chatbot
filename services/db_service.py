from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from storage.qdrant_store_manager import QdrantManager
from processing.files_to_embed import DocToEmbed
from storage.vector_store import get_document_store
from pathlib import Path
from typing import List


class DBService:
    def __init__(self):
        self.document_store: QdrantDocumentStore = get_document_store()
        self.dbmanager = QdrantManager(document_store=self.document_store)
        self.processor = DocToEmbed()

    def add_chunks_from_folder(self, folder_path: Path) -> None:
        embedded_docs = self.processor.process_folder(folder_path=folder_path)
        self.dbmanager.add_chunks(embedded_docs)

    def add_chunks_from_list_file(self, list_file_path: List[Path]) -> None:
        embedded_docs = self.processor.process_list_file(list_file_path=list_file_path)
        self.dbmanager.add_chunks(embedded_docs)

    def update_chunks_from_list_file(self, list_file_path: List[Path]) -> None:
        embedded_docs = self.processor.process_list_file(list_file_path=list_file_path)
        self.dbmanager.update_chunks(embedded_docs)

    def delete_chunks_from_list_file(self, list_file_path: List[Path]) -> None:
        for file_path in list_file_path:
            file_path_str = str(file_path)
            self.dbmanager.delete_file(file_path_str)

    def rebuild_database_from_folder(self, folder_path: Path):
        """
        Xóa toàn bộ database và rebuild từ folder.
        """
        return self.dbmanager.rebuild_from_folder(folder_path)

    def clear_all_database(self):
        """
        Xóa toàn bộ vectors trong database.
        """
        return self.dbmanager.clear_all_vectors()
