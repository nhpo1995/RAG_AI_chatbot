import gradio as gr
from pathlib import Path
import shutil
import time
import config  # chứa DATA_PATH, IMAGES_PATH

# --- SETUP THƯ MỤC --- #
UPLOAD_FOLDER = config.DATA_PATH
UPLOAD_FOLDER.mkdir(exist_ok=True)

# --- FUNCTIONS --- #
def list_files():
    """Trả về danh sách file hiện có trong folder upload"""
    return [f.name for f in UPLOAD_FOLDER.iterdir() if f.is_file()]

def upload_files(files):
    """Upload 1 hoặc nhiều file từ đường dẫn trả về bởi gr.File(type='filepath')"""
    for f in files:
        dest = UPLOAD_FOLDER / Path(f).name
        shutil.copy(f, dest)
    return list_files()

def delete_file(filenames):
    """Xóa file cụ thể (hỗ trợ xóa nhiều file) và cập nhật danh sách"""
    if isinstance(filenames, str):
        filenames = [filenames]
    for fn in filenames:
        path = UPLOAD_FOLDER / fn
        if path.exists():
            path.unlink()
    return list_files()  # Trả về danh sách file mới sau khi xóa

def delete_all_files():
    """Xóa tất cả file và cập nhật danh sách"""
    shutil.rmtree(UPLOAD_FOLDER)
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    return list_files()

# --- CHAT AI --- #
chat_history = []

def respond(user_message):
    """AI trả lời với trạng thái thinking"""
    chat_history.append({"role": "user", "content": user_message})

    # Hiển thị thinking
    temp_history = chat_history + [{"role": "assistant", "content": "thinking..."}]

    # Giả lập delay AI xử lý
    time.sleep(1.5)

    # Ví dụ AI trả lời (thay bằng RAG thực tế)
    ai_answer = (
        f"**AI trả lời:**\n\n"
        f"| Column1 | Column2 |\n"
        f"|---------|---------|\n"
        f"| Data1   | Data2   |\n"
        f"![Ảnh](./user_uploads/example.png)"
    )

    chat_history[-1] = {"role": "assistant", "content": ai_answer}
    return chat_history

# --- BUILD GRADIO UI --- #
with gr.Blocks() as demo:
    # --- MÀN HÌNH 1: File Upload & Manage --- #
    with gr.Tab("File Upload & Manage"):
        gr.Markdown("### Quản lý file người dùng upload")

        # Chọn file nhưng chưa upload
        upload_input = gr.File(
            label="Chọn file để upload",
            file_count="multiple",
            file_types=[".md", ".txt", ".docx", ".pdf"],
            type="filepath"
        )

        btn_upload = gr.Button("Upload")  # Nút upload riêng

        file_list = gr.CheckboxGroup(
            choices=list_files(),  # Hiển thị các file hiện có ngay khi mở tab
            label="Danh sách file hiện có"
        )

        btn_delete_selected = gr.Button("Xóa file đã chọn")
        btn_delete_all = gr.Button("Xóa tất cả file")

        # Event: bấm nút Upload mới trigger upload và update danh sách
        btn_upload.click(upload_files, upload_input, file_list)

        # Event xóa file đã chọn và cập nhật danh sách
        btn_delete_selected.click(delete_file, file_list, file_list)

        # Event xóa tất cả file và cập nhật danh sách
        btn_delete_all.click(delete_all_files, [], file_list)

    # --- MÀN HÌNH 2: Chat với AI (Gemini Style) --- #
    with gr.Tab("Chat with AI"):
        gr.Markdown("### Hỏi đáp với AI")

        with gr.Row():
            chatbox = gr.Chatbot(label="Gemini Chat", type="messages", height=500)

        msg = gr.Textbox(
            label="",
            placeholder="Nhập câu hỏi và nhấn Enter để gửi, Shift+Enter để xuống dòng",
            lines=1,          # Chiều cao ban đầu nhỏ
            max_lines=10,     # Tự động mở rộng tối đa
            show_label=False,
            submit_btn="Send",  # Nút gửi tích hợp trong textbox
        )

        # Event gửi tin nhắn khi Enter hoặc nhấn nút
        msg.submit(respond, msg, chatbox)

demo.launch()
