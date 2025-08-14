from parsers.doc_parser import DocParser
import os
from pathlib import Path
from utils.logger import setup_colored_logger

logger = setup_colored_logger()

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
        print(f"trace: {doc.meta.get('trace')}")
        print(doc.content)

if __name__ == "__main__":
    main()
