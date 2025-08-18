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

    def task():
        fn_to_run()
        time.sleep(3)  # Optional delay for visibility

    threading.Thread(target=task).start()
    return gr.update(value=status_message, visible=True)


def list_files():
    """Trả về danh sách file hiện có trong folder upload"""
    try:
        files = [f.name for f in UPLOAD_FOLDER.iterdir() if f.is_file()]
        return files
    except Exception as e:
        print(f"ERROR in list_files(): {e}")
        return []


def upload_files(files):
    """Upload files với error handling và status feedback"""
    if not files:
        new_files = list_files()
        # No files selected
        return gr.update(choices=new_files, value=[]), "⚠️ Không có file nào được chọn"

    uploaded_count = 0
    errors = []

    try:
        for file_path in files:
            if not file_path:
                continue

            source = Path(file_path)
            dest = UPLOAD_FOLDER / source.name

            # Handle duplicate names
            counter = 1
            original_dest = dest
            while dest.exists():
                name_part = original_dest.stem
                ext_part = original_dest.suffix
                dest = UPLOAD_FOLDER / f"{name_part}_{counter}{ext_part}"
                counter += 1

            shutil.copy2(file_path, dest)
            uploaded_count += 1
            # File uploaded successfully

    except Exception as e:
        errors.append(f"Lỗi upload: {str(e)}")
        # Upload error logged

    # Tạo status message
    status = f"✅ Đã upload {uploaded_count} file(s)"
    if errors:
        status += f"\n❌ {'; '.join(errors)}"

    new_files = list_files()
    # Upload completed
    return gr.update(choices=new_files, value=[]), status


def delete_selected_files(selected_files):
    """Xóa file được chọn và cập nhật danh sách"""
    # Delete operation starting
    if not selected_files:
        new_files = list_files()
        # No files selected for deletion
        return gr.update(choices=new_files, value=[]), "⚠️ Không có file nào được chọn"

    deleted_count = 0
    errors = []

    try:
        for filename in selected_files:
            file_path = UPLOAD_FOLDER / filename
            # Processing file deletion
            if file_path.exists():
                file_path.unlink()
                deleted_count += 1
                # File deleted successfully
            else:
                errors.append(f"File không tồn tại: {filename}")
                # File not found
    except Exception as e:
        errors.append(f"Lỗi khi xóa: {str(e)}")
        # Delete error logged

    # Tạo thông báo status
    status = f"✅ Đã xóa {deleted_count} file(s)"
    if errors:
        status += f"\n❌ Lỗi: {'; '.join(errors)}"

    new_files = list_files()
    # Delete operation completed
    return gr.update(choices=new_files, value=[]), status


def delete_all_files():
    """Xóa tất cả file và cập nhật danh sách"""
    # Delete all operation starting
    try:
        files = list(UPLOAD_FOLDER.glob('*'))
        file_count = len([f for f in files if f.is_file()])
        # Files found for deletion

        if file_count == 0:
            return gr.update(choices=[], value=[]), "ℹ️ Không có file nào để xóa"

        for f in files:
            if f.is_file():
                # Deleting file
                f.unlink()

        new_files = list_files()  # Should be empty now
        # Delete all completed
        return gr.update(choices=new_files, value=[]), f"✅ Đã xóa tất cả {file_count} file(s)"
    except Exception as e:
        # Delete all error logged
        new_files = list_files()
        return gr.update(choices=new_files, value=[]), f"❌ Lỗi khi xóa: {str(e)}"


# --- CHAT AI --- #
def respond(user_message, history):
    """Handle chat responses with proper format for Gradio Chatbot"""
    if not user_message or not user_message.strip():
        return history, ""

    try:
        # Get AI response
        ai_answer = rag_service.semantic_query(
            query=user_message.strip(), top_k=10)

        # Add to history in correct format [[user, ai], [user2, ai2]]
        history.append([user_message.strip(), ai_answer])

        # Limit history to prevent memory issues
        if len(history) > 50:
            history = history[-50:]

    except Exception as e:
        print(f"Error in chat: {e}")
        history.append(
            [user_message.strip(), "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại."])

    return history, ""


def clear_chat():
    """Clear chat history"""
    return [], ""


def reload_database() -> None:
    db_service.reload_vector_db()


def refresh_file_list():
    """Refresh file list với proper update"""
    files = list_files()
    # File list refreshed
    return gr.update(choices=files, value=[])


def refresh_with_status():
    """Refresh file list và return status message"""
    files = list_files()
    # Refresh with status completed
    status = f"🔄 Refreshed - Found {len(files)} file(s)"
    return gr.update(choices=files, value=[]), status


# --- BUILD GRADIO UI --- #
with gr.Blocks(title="AI Document Assistant") as demo:

    # Header
    gr.Markdown("""
    # 🤖 AI Document Assistant
    ### Powered by Haystack RAG System
    Upload documents and chat with AI to get intelligent answers.
    """)

    with gr.Tabs():
        # === CHAT TAB === #
        with gr.Tab("💬 Chat with AI"):
            with gr.Row():
                with gr.Column(scale=4):
                    # Chat interface
                    chatbox = gr.Chatbot(
                        label="AI Assistant",
                        height=600,
                        show_copy_button=True
                    )

                    # Input area
                    with gr.Row():
                        with gr.Column(scale=10):
                            msg = gr.Textbox(
                                label="",
                                placeholder="Ask me anything about your documents... (Press Enter to send)",
                                lines=1,
                                max_lines=5,
                                show_label=False,
                            )
                        with gr.Column(scale=1, min_width=100):
                            submit_btn = gr.Button(
                                "Send",
                                variant="primary"
                            )

                    # Control buttons
                    with gr.Row():
                        clear_btn = gr.Button(
                            "Clear Chat",
                            variant="secondary"
                        )

                # Side panel for database operations
                with gr.Column(scale=1, min_width=200):
                    gr.Markdown("### Database Operations")

                    reload_btn = gr.Button(
                        "Reload Database",
                        variant="secondary"
                    )

                    reload_status = gr.Markdown(value="")

                    gr.Markdown("""
                    **Database Info:**
                    - Status: ✅ Connected  
                    - Documents: Ready for queries  
                    - Last reload: On startup
                    """)

        # Event handlers for chat
        msg.submit(
            fn=respond,
            inputs=[msg, chatbox],
            outputs=[chatbox, msg],
            api_name="chat"
        )

        submit_btn.click(
            fn=respond,
            inputs=[msg, chatbox],
            outputs=[chatbox, msg]
        )

        clear_btn.click(
            fn=clear_chat,
            outputs=[chatbox, msg]
        )

        # Database reload
        reload_btn.click(
            fn=lambda: run_with_status(
                reload_database, "🔄 Đang reload DB...", "✅ Reload thành công!"
            ),
            outputs=reload_status,
        )

        # === FILE MANAGEMENT TAB === #
        with gr.Tab("📁 File Management"):
            with gr.Row():
                # Upload section
                with gr.Column(scale=1):
                    gr.Markdown("### Upload Documents")

                    upload_input = gr.File(
                        label="Choose files to upload",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".txt", ".md"],
                        type="filepath"
                    )

                    upload_btn = gr.Button(
                        "Upload Files",
                        variant="primary"
                    )

                    upload_status = gr.Markdown(value="")

                    gr.Markdown("""
                    **Upload Guidelines:**
                    - **Formats:** PDF, DOCX, TXT, MD  
                    - **Max size:** 50MB per file  
                    - **Duplicates:** Auto-renamed
                    """)

                # File management section
                with gr.Column(scale=1):
                    gr.Markdown("### Manage Files")

                    file_list = gr.CheckboxGroup(
                        choices=[],  # Start empty, will be updated by refresh
                        label="Uploaded Files (select to delete)",
                        info="Select files and click delete button"
                    )

                    with gr.Row():
                        refresh_btn = gr.Button(
                            "Refresh",
                            variant="secondary"
                        )
                        delete_selected_btn = gr.Button(
                            "Delete Selected",
                            variant="secondary"
                        )

                    delete_all_btn = gr.Button(
                        "Delete All Files",
                        variant="stop"
                    )

                    file_status = gr.Markdown(value="")

    # === FILE MANAGEMENT EVENT HANDLERS === #

    # Upload files
    upload_btn.click(
        fn=upload_files,
        inputs=upload_input,
        outputs=[file_list, upload_status]
    )

    # Refresh file list with status feedback
    refresh_btn.click(
        fn=refresh_with_status,
        outputs=[file_list, file_status]
    )

    # Delete selected files - FIX CHÍNH: Sử dụng function mới và output đúng
    delete_selected_btn.click(
        fn=delete_selected_files,
        inputs=file_list,
        outputs=[file_list, file_status]
    )

    # Delete all files
    delete_all_btn.click(
        fn=delete_all_files,
        outputs=[file_list, file_status]
    )

    # Auto-refresh file list when app loads
    demo.load(
        fn=refresh_file_list,
        outputs=file_list
    )

demo.launch()
