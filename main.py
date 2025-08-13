from doc_parser__old import DocParser
import os
from pathlib import Path
current_dir = Path(os.getcwd())
images_root = current_dir / "images"
folder_path = current_dir / "data"

def main():
    parser = DocParser(images_root=images_root)
    docs = parser.parse_folder(Path("data"))

    print(f"Tổng {len(docs)} docs")
    for doc in docs:
        print("======" * 20)
        print(f"source: {doc.meta['source']}")
        print(f"category: {doc.meta.get('category')}")
        print(f"file_path: {doc.meta.get('file_path')}")
        print(f"document_id: {doc.meta.get('document_id')}")
        print(doc.content)

if __name__ == "__main__":
    main()
