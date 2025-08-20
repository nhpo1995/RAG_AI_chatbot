# 🤖 AI Document Assistant

**AI Document Assistant** là một hệ thống RAG (Retrieval-Augmented Generation) mạnh mẽ được xây dựng trên nền tảng Haystack, cho phép bạn tải lên tài liệu và trò chuyện với AI để nhận câu trả lời thông minh dựa trên nội dung tài liệu.

## ✨ Tính năng chính

-   📚 **Hỗ trợ đa định dạng**: PDF, DOCX, TXT, MD
-   🖼️ **Xử lý hình ảnh thông minh**: Tự động trích xuất và phân tích hình ảnh với Docling
-   💬 **Chat AI thông minh**: Trả lời câu hỏi dựa trên nội dung tài liệu
-   🔍 **Tìm kiếm vector**: Sử dụng Qdrant để lưu trữ và tìm kiếm embeddings
-   🎯 **Giao diện thân thiện**: Web UI với Gradio
-   🚀 **Xử lý batch**: Hỗ trợ xử lý nhiều tài liệu cùng lúc

## 🛠️ Yêu cầu hệ thống

### Hệ điều hành

-   **Windows 10/11** (đã test)
-   **Linux** (Ubuntu 18.04+)
-   **macOS** (10.15+)

### Phần mềm cần thiết

-   **Python 3.11.x** (chính xác: 3.11.13)
-   **Docker Desktop** (để chạy Qdrant)
-   **Git** (để clone repository)

### Cấu hình tối thiểu

-   **RAM**: 8GB (khuyến nghị 16GB)
-   **Storage**: 10GB trống
-   **CPU**: 4 cores (khuyến nghị 8 cores)

## 🚀 Cài đặt và thiết lập

### Bước 1: Clone repository

```bash
git clone https://github.com/your-username/haystack_data_convertor.git
cd haystack_data_convertor
```

### Bước 2: Cài đặt Python dependencies

#### Sử dụng uv (khuyến nghị)

```bash
# Cài đặt uv nếu chưa có
pip install uv

# Tạo virtual environment với Python 3.11.13
uv venv --python 3.11.13

# Kích hoạt virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Cài đặt dependencies
uv sync
```

### Bước 3: Thiết lập biến môi trường

Tạo file `.env` trong thư mục gốc của dự án:

```bash
# Tạo file .env
touch .env  # Linux/macOS
# hoặc
echo. > .env  # Windows
```

Thêm các biến môi trường sau vào file `.env`:

```env
# OpenAI API Key (bắt buộc)
OPENAI_API_KEY=your_openai_api_key_here

```

### Bước 4: Khởi động Qdrant Database

```bash
# Sử dụng Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Hoặc sử dụng docker-compose
docker-compose up -d qdrant
```

**🔍 Kiểm tra Database**: Sau khi khởi động Qdrant, bạn có thể truy cập dashboard tại:
`http://localhost:6333/dashboard#/collections/Document#points`

#### Kiểm tra services

```bash
# Kiểm tra Qdrant
curl http://localhost:6333/health

# Kiểm tra Docling
python -c "import docling; print('Docling version:', docling.__version__)"
```

### Bước 5: Chạy ứng dụng

```bash
# Đảm bảo virtual environment đã được kích hoạt
python main.py
```

Ứng dụng sẽ chạy tại: `http://localhost:7860`

## 📁 Cấu trúc dự án

```
haystack_data_convertor/
├── agent/                 # RAG Agent và AI logic
├── data/                  # Thư mục chứa tài liệu upload
├── images/                # Thư mục chứa hình ảnh trích xuất
├── parsers/               # Các parser cho từng định dạng file
├── processing/            # Xử lý tài liệu và embedding
├── services/              # Database và RAG services
├── storage/               # Vector store và Qdrant management
├── UI/                    # Gradio web interface
├── utils/                 # Utilities và logging
├── config.py              # Cấu hình chính
├── main.py                # Entry point
├── docker-compose.yml     # Docker services
└── pyproject.toml         # Dependencies
```

## 🔧 Cấu hình

### Models và Database

Chỉnh sửa `config.py` để thay đổi:

-   OpenAI models (embedding, LLM)
-   Qdrant connection (URL, collection name)
-   Index settings

### Ports

-   **Gradio UI**: 7860
-   **Qdrant**: 6333

## 📖 Hướng dẫn sử dụng

1. **Upload tài liệu**: Tab "📁 File Management" → Chọn file → Upload
2. **Chat với AI**: Tab "💬 Chat with AI" → Nhập câu hỏi
3. **Quản lý DB**: Reload Database, xóa file, kiểm tra trạng thái

## 🐛 Xử lý lỗi thường gặp

| Lỗi            | Giải pháp                                            |
| -------------- | ---------------------------------------------------- |
| **OpenAI API** | Kiểm tra `OPENAI_API_KEY` trong `.env`               |
| **Qdrant**     | `docker ps \| grep qdrant` → `docker restart qdrant` |
| **Docling**    | Kích hoạt venv → `uv sync`                           |
| **Memory**     | Tăng RAM Docker, giảm batch size                     |

## 🔒 Bảo mật & Monitoring

-   **Không commit `.env`** chứa API keys
-   **Logs**: `utils/logger.py`, `docker logs qdrant`
-   **Performance**: Monitor Docker containers, OpenAI API dashboard
