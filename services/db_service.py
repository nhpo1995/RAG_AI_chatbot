from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from storage.qdrant_store_manager import QdrantManager
from processing.files_to_embed import DocToEmbed
from storage.vector_store import get_document_store
import config as cf
from pathlib import Path
from typing import List

class DBService:
    def __init__(self):
        self.document_store: QdrantDocumentStore = get_document_store()
        self.dbmanager = QdrantManager(document_store=self.document_store)
        self.processor = DocToEmbed()
        self.folder_path: Path = cf.DATA_PATH

    def reload_vector_db(self) ->None:
        embedded_docs = self.processor.process_folder(folder_path=cf.DATA_PATH)
        self.dbmanager.add_chunks(embedded_docs)

    def add_list_doc_to_db(self, list_doc: List[Path]) ->None:
        embedded_docs = self.processor.process_list_file(list_file_path=list_doc)
        self.dbmanager.add_chunks(embedded_docs)





