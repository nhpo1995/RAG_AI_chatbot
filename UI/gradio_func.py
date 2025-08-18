import threading
import time
import gradio as gr
from pathlib import Path
import shutil
import sys
# Add parent directory to path để có thể import config và services
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.rag_service import RAGService
from services.db_service import DBService

UPLOAD_FOLDER = config.DATA_PATH
IMAGES_FOLDER = config.IMAGES_PATH
db_service = DBService()
rag_service = RAGService()

# --- FUNCTIONS FOR FILE MANAGEMENT TAB--- #
def run_with_status(
        fn_to_run, status_message="Đang thực hiện...", success_message="Hoàn thành!"
):
    """
    Chạy một function bất kỳ, trả về dict để cập nhật Label trong Gradio.
    """
    def task():
        fn_to_run()
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
    except Exception as e:
        errors.append(f"Lỗi upload: {str(e)}")
    status = f"✅ Đã upload {uploaded_count} file(s)"
    if errors:
        status += f"\n❌ {'; '.join(errors)}"
    new_files = list_files()
    return gr.update(choices=new_files, value=[]), status


def delete_selected_files(selected_files):
    """Xóa file được chọn và cập nhật danh sách"""
    # Delete operation starting
    if not selected_files:
        new_files = list_files()
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
            else:
                errors.append(f"File không tồn tại: {filename}")
    except Exception as e:
        errors.append(f"Lỗi khi xóa: {str(e)}")
    status = f"✅ Đã xóa {deleted_count} file(s)"
    if errors:
        status += f"\n❌ Lỗi: {'; '.join(errors)}"
    new_files = list_files()
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


def refresh_with_status():
    """Refresh file list và return status message"""
    files = list_files()
    status = f"🔄 Refreshed - Found {len(files)} file(s)"
    return gr.update(choices=files, value=[]), status


def refresh_file_list():
    """Refresh file list với proper update"""
    files = list_files()
    return gr.update(choices=files, value=[])


# --- FUNCTIONS FOR CHAT TAB--- #
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
    db_service.add_chunks_from_list_folder(list_folder_path=[UPLOAD_FOLDER])





