import gradio as gr


# Dummy functions since we are only creating the interface, not the functionality
def dummy_process(files, chunk_strategy, embedding_model, vector_db):
    return "Documents processed successfully (dummy response)."


def dummy_query(question):
    return "This is a dummy answer based on the question.", "Citations: Dummy source from document X, page Y."


with gr.Blocks(title="RAG Application") as demo:
    gr.Markdown("# RAG-based AI Application")
    gr.Markdown(
        "An AI system for reading, understanding, and extracting information from documents using Retrieval-Augmented Generation (RAG).")

    with gr.Tab("Admin - Document Ingestion"):
        gr.Markdown("### Upload and Process Documents (Admin Only)")
        file_upload = gr.File(
            label="Upload Documents",
            file_types=[".pdf", ".docx", ".txt", ".md"],
            file_count="multiple"
        )
        chunk_strategy = gr.Dropdown(
            choices=["character", "token", "recursive"],
            label="Chunking Strategy",
            value="recursive"
        )
        embedding_model = gr.Dropdown(
            choices=["sentence-transformers", "text-embedding-ada-002"],
            label="Embedding Model",
            value="sentence-transformers"
        )
        vector_db = gr.Dropdown(
            choices=["FAISS", "Pinecone", "Chroma"],
            label="Vector Database",
            value="FAISS"
        )
        process_btn = gr.Button("Process Documents")
        status_output = gr.Textbox(label="Processing Status", interactive=False)

        process_btn.click(
            fn=dummy_process,
            inputs=[file_upload, chunk_strategy, embedding_model, vector_db],
            outputs=status_output
        )

    with gr.Tab("User - Ask Questions"):
        gr.Markdown("### Ask Questions and Get Answers")
        question_input = gr.Textbox(
            label="Enter your question in natural language",
            placeholder="e.g., What is the policy on data privacy?"
        )
        submit_btn = gr.Button("Submit Question")
        answer_output = gr.Textbox(label="Generated Answer", interactive=False)
        citations_output = gr.Textbox(label="Citations/Sources", interactive=False)

        submit_btn.click(
            fn=dummy_query,
            inputs=question_input,
            outputs=[answer_output, citations_output]
        )
    
demo.launch()