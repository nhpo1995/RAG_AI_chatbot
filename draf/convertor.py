# import base64
# from haystack_integrations.components.converters.unstructured import UnstructuredFileConverter
# from haystack import Document
# from pathlib import Path
# from bs4 import BeautifulSoup
# import os
#
# current_dir = Path(os.getcwd())
# data_dir = current_dir / "data"
# file_path = data_dir / "file-excelt-test - Trang tính1.csv"
#
# images_root = current_dir / "images"
# images_root.mkdir(exist_ok=True)
#
# converter = UnstructuredFileConverter(
#     api_url="http://localhost:8000/general/v0/general",
#     document_creation_mode="one-doc-per-element",
#     separator="\n\n",
#     progress_bar=True,
#     unstructured_kwargs={
#         "encoding": "utf-8",
#         "extract_image_block_types": ["Image", "Table"],
#         "languages": ["vie", "eng"],
#         "skip_infer_table_types": [],
#         "strategy": "hi_res",
#     }
# )
#
# result  = converter.run(paths=[file_path])
# blocks  = result["documents"]
# # ---------- Helpers ----------
# TEXT_CATS = {"Title", "NarrativeText"}
#
# def is_text_block(doc: Document) -> bool:
#     return doc.meta.get("category") in TEXT_CATS
#
# def nearest_text(blocks, idx, direction: int) -> str:
#     """
#     direction = -1 (lùi lại tìm 'trước'),  +1 (tiến tới tìm 'sau')
#     Trả về content của block text gần nhất theo hướng chỉ định.
#     """
#     j = idx + direction
#     while 0 <= j < len(blocks):
#         if is_text_block(blocks[j]):
#             return (blocks[j].content or "").strip()
#         j += direction
#     return ""
#
#
# def process_table_block(blocks, idx, file_path, is_in_image=False):
#     d = blocks[idx]
#
#     # 1. Lấy nội dung bảng ở dạng Markdown
#     if "text_as_html" in d.meta:
#         md = html_table_to_markdown(d.meta["text_as_html"])
#     else:
#         md = (d.content or "").strip()
#
#     # 2. Lấy context trước/sau
#     prev_txt = nearest_text(blocks, idx, -1)
#     context = (prev_txt + "\n\n" if prev_txt else "").strip()
#
#     # 3. Ghép context vào trước bảng
#     if context:
#         md = context + "\n\n" + md
#
#     # 4. Tạo Document cho bảng
#     return Document(
#         content=md,
#         meta={
#             "category": "table",
#             "source": str(file_path),
#             "filename": file_path.name,
#             "page_number": d.meta.get("page_number"),
#             "element_index": d.meta.get("element_index"),
#             "from_image": is_in_image
#         },
#     )
#
# def html_table_to_markdown(html: str) -> str:
#     """Chuyển table HTML (từ text_as_html) sang Markdown đơn giản."""
#     soup = BeautifulSoup(html, "html.parser")
#     table = soup.find("table")
#     if table is None:
#         # Không có <table>, trả về plain text đã làm sạch
#         return soup.get_text(separator=" ").strip()
#
#     # Header
#     headers = []
#     thead = table.find("thead")
#     if thead:
#         ths = thead.find_all("th")
#         headers = [th.get_text(strip=True) for th in ths]
#     # Body rows
#     rows = []
#     tbody = table.find("tbody")
#     if tbody:
#         for tr in tbody.find_all("tr"):
#             cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
#             rows.append(cells)
#     else:
#         # Fallback nếu không có tbody
#         for tr in table.find_all("tr"):
#             cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
#             rows.append(cells)
#
#     # Build markdown
#     md_lines = []
#     if headers:
#         md_lines.append("| " + " | ".join(headers) + " |")
#         md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
#
#     for r in rows:
#         # Căn số cột theo header nếu có
#         if headers and len(r) < len(headers):
#             r = r + [""] * (len(headers) - len(r))
#         md_lines.append("| " + " | ".join(r) + " |")
#
#     return "\n".join(md_lines).strip()
#
#
# # ---------- 1) Gom toàn bộ Title + NarrativeText thành 1 Document "text" ----------
# all_text_parts = []
# for d in blocks:
#     if is_text_block(d):
#         if d.content:
#             all_text_parts.append(d.content.strip())
#
# merged_text_content = "\n\n".join(all_text_parts).strip()
# text_doc = Document(
#     content=merged_text_content,
#     meta={
#         "category": "text",
#         "source": str(file_path),
#         "filename": file_path.name,
#     },
# )
#
# # ---------- 2) Tạo các Document cho ảnh (lưu ảnh + thêm ngữ cảnh trước/sau) ----------
# image_docs = []
# for idx, d in enumerate(blocks):
#     if d.meta.get("category") == "Image" and "image_base64" in d.meta:
#         file_stem = file_path.stem
#         images_dir = images_root / file_stem
#         images_dir.mkdir(exist_ok=True)
#         # Lưu ảnh
#         mime = d.meta.get("image_mime_type") or "image/png"
#         ext = ".jpg" if "jpeg" in mime or "jpg" in mime else ".png"
#         page = d.meta.get("page_number", "x")
#         elidx = d.meta.get("element_index", idx)
#         img_name = f"page_{page}_idx_{elidx}{ext}"
#         img_path = images_dir / img_name
#
#         try:
#             img_bytes = base64.b64decode(d.meta["image_base64"])
#             with open(img_path, "wb") as f:
#                 f.write(img_bytes)
#         except Exception as e:
#             # Nếu có lỗi decode, bỏ qua lưu nhưng vẫn tạo doc ảnh với file_path rỗng
#             img_path = Path("")
#
#         # Ghép nội dung văn bản trước & sau gần nhất
#         prev_txt = nearest_text(blocks, idx, -1)
#         next_txt = nearest_text(blocks, idx, +1)
#         context = (prev_txt + ("\n\n" if prev_txt and next_txt else "") + next_txt).strip()
#
#         image_docs.append(
#             Document(
#                 content=f"Hình ảnh: {context}" if context else "Hình ảnh:",
#                 meta={
#                     "category": "image",
#                     "file_path": str(img_path) if str(img_path) else "",
#                     "source": str(file_path),
#                     "filename": file_path.name,
#                     "page_number": d.meta.get("page_number"),
#                     "element_index": d.meta.get("element_index"),
#                 },
#             )
#         )
#
# # ---------- 3) Tạo các Document cho bảng (HTML -> Markdown) ----------
# table_docs = []
# for idx, d in enumerate(blocks):
#     if d.meta.get("category") == "Table":
#         table_docs.append(process_table_block(blocks, idx, file_path))
#     elif d.meta.get("category") == "Image" and "text_as_html" in d.meta:
#         table_docs.append(process_table_block(blocks, idx, file_path, is_in_image=True))
#
# # ---------- Kết quả cuối cùng ----------
# final_docs = []
# # 1 text doc duy nhất (nếu có nội dung)
# if merged_text_content and not file_path.suffix.lower() in [".xls", ".xlsx"]:
#     final_docs.append(text_doc)
#
# # Thêm toàn bộ image docs và table docs
# final_docs.extend(image_docs)
# final_docs.extend(table_docs)
#
# # In thử để bạn kiểm tra nhanh
# print(f"Tạo {len(final_docs)} Documents (text={1 if merged_text_content else 0}, image={len(image_docs)}, table={len(table_docs)})")
# for i, d in enumerate(final_docs, 1):
#     print(f"\n--- DOC #{i} ---")
#     print(d.meta)
#     print("category:", d.meta.get("category"))
#     if d.meta.get("category") == "image":
#         print("file_path:", d.meta.get("file_path"))
#         print("content preview:", (d.content or ""))
#     else:
#         print("content preview:", (d.content or ""))
