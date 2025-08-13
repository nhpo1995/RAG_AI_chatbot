from pathlib import Path

# API URL của unstructured service
API_URL_UNSTRUCTURED = "http://localhost:8000/general/v0/general"

# Đường dẫn thư mục data
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data"

# Model embedding
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Qdrant / Weaviate config
VECTOR_DB_URL = "http://localhost:6333"
VECTOR_DB_COLLECTION = "documents"
