import threading
import time
import gradio as gr
from pathlib import Path
import shutil
import config
from services.rag_service import RAGService
from services.db_service import DBService

# --- CONSTANT --- #
UPLOAD_FOLDER = config.DATA_PATH
UPLOAD_FOLDER.mkdir(exist_ok=True)
db_service = DBService()
rag_service = RAGService()

# --- FUNCTIONS --- #
def run_with_status(
    fn_to_run, status_message="Đang thực hiện...", success_message="Hoàn thành!"
):
    """
    Chạy một function bất kỳ, trả về dict để cập nhật Label trong Gradio.
    """
    status = gr.update(value=status_message, visible=True)
    def task():
        fn_to_run()
        status_after = gr.update(value=success_message, visible=True)
        time.sleep(3)
        status_after = gr.update(visible=False)
        return status_after
    threading.Thread(target=task).start()
    return status

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
    return list_files()

def delete_all_files():
    """Xóa tất cả file và cập nhật danh sách"""
    shutil.rmtree(UPLOAD_FOLDER)
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    return list_files()

# --- CHAT AI --- #
chat_history = []
def respond(user_message):
    chat_history.append({"role": "user", "content": user_message})
    temp_history = chat_history + [{"role": "assistant", "content": "thinking..."}]
    ai_answer = rag_service.semantic_query(query=user_message, top_k=10)
    # chat_history.append({"role": "assistant", "content": ai_answer})
    chat_history[-1] = {"role": "assistant", "content": ai_answer}
    return chat_history, ""
def reload_database() ->None:
    db_service.reload_vector_db()
# --- BUILD GRADIO UI --- #
with gr.Blocks() as demo:
# =============================================================================================
    # --- MÀN HÌNH 1: Chat với AI () --- #
    with gr.Tab("Chat with AI"):
        gr.Markdown("### Hỏi đáp với AI")
        radio = gr.Radio(
            ["Admin", "manager", "staff"],
            label="Select your permission"
        )
        with gr.Row():
            chatbox = gr.Chatbot(label="Chatbot", type="messages", height=500)
        msg = gr.Textbox(
            label="",
            placeholder="Nhập câu hỏi và nhấn Enter để gửi, Shift+Enter để xuống dòng",
            lines=1,
            max_lines=10,
            show_label=False,
            submit_btn="Send",  # Nút gửi tích hợp trong textbox
        )
        # Label hiển thị trạng thái reload
        reload_status = gr.Label(value="", visible=False)
        reload_btn = gr.Button("Reload Database")
        reload_btn.click(
            fn=lambda: run_with_status(
                reload_database, "Đang reload DB...", "Reload thành công!"
            ),
            inputs=None,
            outputs=reload_status,
        )
        msg.submit(fn=respond, inputs=msg, outputs=[chatbox, msg], api_name="/ask")
# ==============================================================================================
    # --- MÀN HÌNH 2: File Upload & Manage --- #
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



demo.launch()
