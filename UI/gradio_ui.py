import gradio as gr
import sys
from pathlib import Path

# Thêm thư mục cha vào path để có thể import UI package
sys.path.append(str(Path(__file__).parent.parent))

from UI.gradio_func import (
    respond,
    clear_chat,
    reload_database,
    run_with_status,
    upload_file,
    refresh_with_status,
    delete_selected_files,
    delete_all_files,
    refresh_file_list,
)

# --- XÂY DỰNG GRADIO UI --- #
with gr.Blocks(title="AI Document Assistant") as demo:

    # Header
    gr.Markdown(
        """
    # 🤖 AI Document Assistant
    ### Powered by Haystack RAG System
    Upload documents and chat with AI to get intelligent answers.
    """
    )

    with gr.Tabs():
        # === TAB CHAT === #
        with gr.Tab("💬 Chat with AI"):
            with gr.Row():
                with gr.Column(scale=4):
                    # Giao diện chat
                    chatbox = gr.Chatbot(
                        label="AI Assistant", height=600, show_copy_button=True
                    )

                    # Khu vực nhập liệu
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
                            submit_btn = gr.Button("Send", variant="primary")
                    # Các nút điều khiển
                    with gr.Row():
                        clear_btn = gr.Button("Clear Chat", variant="secondary")

                # Panel bên cạnh cho các thao tác database
                with gr.Column(scale=1, min_width=200):
                    gr.Markdown("### Database Operations")
                    reload_btn = gr.Button("Reload Database", variant="secondary")
                    reload_status = gr.Markdown(value="")
                    gr.Markdown(
                        """
                    **Database Info:**
                    - Status: ✅ Connected  
                    - Documents: Ready for queries  
                    - Last reload: On startup
                    """
                    )

        # === CÁC EVENT HANDLER CHO CHAT === #
        msg.submit(
            fn=respond, inputs=[msg, chatbox], outputs=[chatbox, msg], api_name="chat"
        )

        submit_btn.click(fn=respond, inputs=[msg, chatbox], outputs=[chatbox, msg])

        clear_btn.click(fn=clear_chat, outputs=[chatbox, msg])

        # Reload database
        reload_btn.click(
            fn=lambda: run_with_status(
                reload_database, "🔄 Đang reload DB...", "✅ Reload thành công!"
            ),
            outputs=reload_status,
        )

        # === TAB QUẢN LÝ FILE === #
        with gr.Tab("📁 File Management"):
            with gr.Row():
                # Phần upload
                with gr.Column(scale=1):
                    gr.Markdown("### Upload Documents")

                    upload_input = gr.File(
                        label="Choose one file to upload",
                        file_count="single",
                        file_types=[".pdf", ".docx", ".txt", ".md"],
                        type="filepath",
                    )

                    upload_btn = gr.Button("Upload File", variant="primary")
                    upload_status = gr.Markdown(value="")
                    gr.Markdown(
                        """
                    **Upload Guidelines:**
                    - **Formats:** PDF, DOCX, TXT, MD  
                    - **Max size:** 50MB per file  
                    - **Duplicates:** Auto-renamed
                    """
                    )
                # Phần quản lý file
                with gr.Column(scale=1):
                    gr.Markdown("### Manage Files")
                    file_list = gr.CheckboxGroup(
                        choices=[],  # Bắt đầu trống, sẽ được cập nhật bởi refresh
                        label="Uploaded Files (select to delete)",
                        info="Select files and click delete button",
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("Refresh", variant="secondary")
                        delete_selected_btn = gr.Button(
                            "Delete Selected", variant="secondary"
                        )
                    delete_all_btn = gr.Button("Delete All Files", variant="stop")
                    file_status = gr.Markdown(value="")

    # === CÁC EVENT HANDLER CHO QUẢN LÝ FILE === #

    # Upload files
    upload_btn.click(
        fn=upload_file,
        inputs=upload_input,
        outputs=[file_list, upload_input, upload_status],
    )

    # Refresh file list với phản hồi trạng thái
    refresh_btn.click(fn=refresh_with_status, outputs=[file_list, file_status])

    # Xóa file được chọn - FIX CHÍNH: Sử dụng function mới và output đúng
    delete_selected_btn.click(
        fn=delete_selected_files, inputs=file_list, outputs=[file_list, file_status]
    )

    # Xóa tất cả file
    delete_all_btn.click(fn=delete_all_files, outputs=[file_list, file_status])

    # Tự động refresh file list khi app khởi động
    demo.load(fn=refresh_file_list, outputs=file_list)

demo.launch()
