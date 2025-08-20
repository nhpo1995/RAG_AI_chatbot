import threading
import gradio as gr
from pathlib import Path
import shutil
import sys
import logging

# Thêm thư mục cha vào path để có thể import config và services
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.rag_service import RAGService
from services.db_service import DBService
from utils.logger import setup_colored_logger

setup_colored_logger()
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = config.DATA_PATH
IMAGES_FOLDER = config.IMAGES_PATH
db_service = DBService()
rag_service = RAGService()


# --- CÁC HÀM CHO TAB QUẢN LÝ FILE --- #
def run_with_status(
    fn_to_run, status_message="Đang thực hiện...", success_message="Hoàn thành!"
):
    """
    Chạy một function bất kỳ, trả về dict để cập nhật Label trong Gradio.
    """
    try:
        # Chạy function trực tiếp thay vì trong thread
        fn_to_run()
        return gr.update(value=success_message, visible=True)
    except Exception as e:
        error_message = f"❌ Lỗi: {str(e)}"
        logger.error(f"Error in run_with_status: {e}")
        return gr.update(value=error_message, visible=True)


def list_files():
    """Trả về danh sách file hiện có trong folder upload"""
    try:
        files = [f.name for f in UPLOAD_FOLDER.iterdir() if f.is_file()]
        return files
    except Exception as e:
        print(f"ERROR in list_files(): {e}")
        return []


def upload_file(file):
    """Upload một file với error handling và status feedback"""
    if not file:
        new_files = list_files()
        return (
            gr.update(choices=new_files, value=[]),
            gr.update(value=None),
            "⚠️ Không có file nào được chọn",
        )
    try:
        source = Path(file)
        dest = UPLOAD_FOLDER / source.name
        # Xử lý tên trùng lặp
        counter = 1
        original_dest = dest
        while dest.exists():
            name_part = original_dest.stem
            ext_part = original_dest.suffix
            dest = UPLOAD_FOLDER / f"{name_part}_{counter}{ext_part}"
            counter += 1
        shutil.copy2(file, dest)
        # Bước 2: Thêm vào database (với rollback nếu thất bại)
        try:
            db_service.add_chunks_from_list_file(list_file_path=[dest])
            status = "✅ File đã được lưu thành công"
        except Exception as db_error:
            # Rollback: xóa file đã copy
            dest.unlink(missing_ok=True)
            raise Exception(f"Lỗi khi thêm vào database: {db_error}")
    except Exception as e:
        status = f"❌ Lỗi upload: {str(e)}"
    new_files = list_files()
    # Clear file input để tránh upload lặp
    return gr.update(choices=new_files, value=[]), gr.update(value=None), status


def delete_selected_files(selected_files):
    """Xóa file được chọn và cập nhật danh sách"""
    # Bắt đầu thao tác xóa
    if not selected_files:
        new_files = list_files()
        return gr.update(choices=new_files, value=[]), "⚠️ Không có file nào được chọn"
    deleted_count = 0
    errors = []
    try:
        for filename in selected_files:
            file_path = UPLOAD_FOLDER / filename
            # Xử lý xóa file
            if file_path.exists():
                file_path.unlink()
                try:
                    db_service.delete_chunks_from_list_file(list_file_path=[file_path])
                    deleted_count += 1
                except Exception as db_error:
                    logger.error(f"Lỗi khi xóa khỏi database: {db_error}")
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
    # Bắt đầu thao tác xóa tất cả
    try:
        files = list(UPLOAD_FOLDER.glob("*"))
        file_count = len([f for f in files if f.is_file()])
        # Tìm thấy file để xóa
        if file_count == 0:
            return gr.update(choices=[], value=[]), "ℹ️ Không có file nào để xóa"
        for f in files:
            if f.is_file():
                # Đang xóa file
                f.unlink()
        try:
            db_service.clear_all_database()
            logger.info("Đã xóa toàn bộ database thành công")
        except Exception as db_error:
            logger.error(f"Lỗi khi xóa database: {db_error}")
            # Vẫn return success vì file đã xóa thành công

        new_files = list_files()
        return (
            gr.update(choices=new_files, value=[]),
            f"✅ Đã xóa tất cả {file_count} file(s) trong database",
        )
    except Exception as e:
        # Lỗi xóa tất cả đã được log
        logger.error(f"Lỗi khi xóa tất cả file: {e}")
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


# --- CÁC HÀM CHO TAB CHAT --- #
def respond(user_message, history):
    """Handle chat responses with proper format for Gradio Chatbot"""
    if not user_message or not user_message.strip():
        return history, ""
    try:
        # Lấy phản hồi từ AI
        ai_answer = rag_service.semantic_query(query=user_message.strip(), top_k=10)
        # Thêm vào lịch sử với định dạng đúng [[user, ai], [user2, ai2]]
        history.append([user_message.strip(), ai_answer])
        # Giới hạn lịch sử để tránh vấn đề về bộ nhớ
        if len(history) > 50:
            history = history[-50:]
    except Exception as e:
        print(f"Error in chat: {e}")
        history.append(
            [user_message.strip(), "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại."]
        )
    return history, ""


def clear_chat():
    """Clear chat history"""
    return [], ""


def reload_database() -> None:
    db_service.rebuild_database_from_folder(folder_path=UPLOAD_FOLDER)
