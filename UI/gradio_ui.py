import gradio as gr
import sys
from pathlib import Path
# Add parent directory to path để có thể import UI package
sys.path.append(str(Path(__file__).parent.parent))

from UI.gradio_func import *

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

        # === EVENT HANDLERS FOR CHAT=== #
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
