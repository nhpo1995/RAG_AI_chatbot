from pathlib import Path

# Đường dẫn thư mục data
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data"
IMAGES_PATH = BASE_PATH / "images"

# Models
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"


# docker run -p 6333:6333 qdrant/qdrant
VECTOR_DB_URL = "http://localhost:6333"
VECTOR_DB_COLLECTION = "Document"
RECREATE_INDEX = True  # Ghi de
