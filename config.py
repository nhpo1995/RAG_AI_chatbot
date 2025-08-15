from pathlib import Path

# API URL của unstructured service
API_URL_UNSTRUCTURED = "http://localhost:8000/general/v0/general"

# Đường dẫn thư mục data
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data"
IMAGES_PATH = BASE_PATH / "images"


# Models
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "gpt-4o-mini"

# Qdrant config
# docker run -p 6333:6333 qdrant/qdrant
VECTOR_DB_URL = "http://localhost:6333"
VECTOR_DB_COLLECTION = "Document"
RECREATE_INDEX=True #Ghi de


