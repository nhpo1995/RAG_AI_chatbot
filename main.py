from UI.gradio_ui import demo

if __name__ == "__main__":
    try:
        demo.launch()
    except Exception as e:
        print(f"Lỗi khi chạy Gradio: {e}")