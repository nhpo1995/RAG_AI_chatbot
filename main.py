from UI.gradio_ui import demo
from config import IMAGES_PATH

if __name__ == "__main__":
    try:
        demo.launch(allowed_paths=[str(IMAGES_PATH)])
    except Exception as e:
        print(f"Lỗi khi chạy Gradio: {e}")