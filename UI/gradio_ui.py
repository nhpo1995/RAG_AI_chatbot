import gradio as gr
import time
from typing import List
from haystack import Document
from pathlib import Path
import shutil
import config
from agent.rag_agent import RAGAssistant
from storage.qdrant_query_manager import QdrantQueryManager

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
    return list_files()

def delete_all_files():
    """Xóa tất cả file và cập nhật danh sách"""
    shutil.rmtree(UPLOAD_FOLDER)
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    return list_files()

def docs_to_context(docs: List[Document]) -> str:
    """
    Gộp toàn bộ content của docs thành 1 chuỗi context cho AI.
    Bỏ qua metadata.
    """
    return "\n\n".join(
        doc.content.strip()
        for doc in docs
        if doc.content and doc.content.strip()
    )
# --- CHAT AI --- #
rag_agent = RAGAssistant()
query_manager = QdrantQueryManager()
chat_history = []
def respond(user_message):
    chat_history.append({"role": "user", "content": user_message})
    temp_history = chat_history + [{"role": "assistant", "content": "thinking..."}]
    query = user_message
    context = docs_to_context(query_manager.semantic_search(query=query, filters=None))
    ai_answer = rag_agent.ask(context=context, question=query)
    chat_history.append({"role": "assistant", "content": ai_answer})
    # chat_history[-1] = {"role": "assistant", "content": ai_answer}
    return chat_history, ""

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
            lines=1,  # Chiều cao ban đầu nhỏ
            max_lines=10,  # Tự động mở rộng tối đa
            show_label=False,
            submit_btn="Send",  # Nút gửi tích hợp trong textbox
        )

        # Event gửi tin nhắn khi Enter hoặc nhấn nút
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
