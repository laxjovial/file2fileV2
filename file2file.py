import streamlit as st
import pandas as pd
from io import BytesIO
import os
from docx import Document
from pdf2docx import Converter
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pypandoc
import requests # For making HTTP requests to the FastAPI backend
import json # For handling JSON responses

# Import cloud storage functions
from cloud_storage.google_drive import upload_to_google_drive
from cloud_storage.dropbox_api import upload_to_dropbox

st.set_page_config(page_title="File2File Converter SaaS", layout="centered")
st.title("📁 File2File Converter SaaS")
st.markdown("Convert between PDF, DOCX, TXT, CSV, XLS, XLSX. Batch uploads supported. Real PDF export. Now with Cloud Storage & Editing!")

# --- Configuration (from Streamlit Secrets) ---
# Ensure you have .streamlit/secrets.toml with FASTAPI_BACKEND_URL, DROPBOX_ACCESS_TOKEN
FASTAPI_BACKEND_URL = st.secrets.get("FASTAPI_BACKEND_URL", "http://localhost:8000") # Default for local testing
DROPBOX_ACCESS_TOKEN = st.secrets.get("DROPBOX_ACCESS_TOKEN", "YOUR_DROPBOX_TOKEN_HERE")

# Supported formats
doc_types = ["pdf", "docx", "txt"]
sheet_types = ["csv", "xls", "xlsx"]
all_types = doc_types + sheet_types

# --- UI for Format Selection and Upload ---
st.subheader("Conversion Settings")
col1, col2 = st.columns(2)
with col1:
    source_format = st.selectbox("From format", all_types)
with col2:
    target_format = st.selectbox("To format", [f for f in all_types if f != source_format])

uploaded_files = st.file_uploader(
    "Upload files",
    type=[source_format],
    accept_multiple_files=True
)

custom_name = st.text_input("Optional: base name for output file(s)", "converted")

# --- Preview Section ---
def preview_file(file, file_type):
    st.subheader("🔍 Preview")
    file.seek(0) # Reset file pointer for preview

    if file_type == "txt":
        text = file.read().decode("utf-8")
        st.text(text[:1000] + ("..." if len(text) > 1000 else ""))
    elif file_type == "csv":
        df = pd.read_csv(file)
        st.dataframe(df.head())
    elif file_type in ["xls", "xlsx"]:
        df = pd.read_excel(file)
        st.dataframe(df.head())
    elif file_type == "docx":
        try:
            doc_bytes = BytesIO(file.read())
            doc = Document(doc_bytes)
            text = "\n".join([p.text for p in doc.paragraphs])
            st.text(text[:1000] + ("..." if len(text) > 1000 else ""))
        except Exception as e:
            st.warning(f"Could not preview DOCX file. It might be corrupted or in an unsupported format. Error: {e}")
    elif file_type == "pdf":
        try:
            pdf_bytes = BytesIO(file.read())
            with pdfplumber.open(pdf_bytes) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                st.text(text[:1000] + ("..." if len(text) > 1000 else ""))
        except Exception as e:
            st.warning(f"Could not preview PDF file. It might be corrupted or in an unsupported format. Error: {e}")

# --- Content Editing Section ---
def edit_content(file_bytes, file_type):
    st.subheader("✏️ Edit Content (Basic)")
    edited_content = file_bytes # Default to original content

    if file_type == "txt":
        file_bytes.seek(0)
        original_text = file_bytes.read().decode("utf-8")
        
        edited_text = st.text_area("Edit your text here:", original_text, height=300)

        st.markdown("---")
        st.write("Text Styling Options:")
        col_b, col_i, col_s = st.columns(3)
        with col_b:
            bold_text = st.checkbox("Bold All Text")
        with col_i:
            italic_text = st.checkbox("Italicize All Text")
        with col_s:
            font_size = st.slider("Font Size (for PDF/DOCX export)", 8, 36, 12)

        final_text = edited_text
        if bold_text:
            final_text = f"**{final_text}**" # Markdown for bold
        if italic_text:
            final_text = f"*{final_text}*" # Markdown for italic

        # Store font_size in session state to pass it to conversion if needed
        st.session_state['font_size'] = font_size
        
        edited_content = BytesIO(final_text.encode("utf-8"))
        
    elif file_type in ["docx", "pdf", "csv", "xls", "xlsx"]:
        st.info("Direct in-app rich text editing is not supported for these formats in this version. Please convert to TXT for basic text editing, or use external tools for full rich text editing.")
        st.session_state['font_size'] = 12 # Reset to default if not TXT
    
    edited_content.seek(0)
    return edited_content

# --- Conversion Logic (Calls FastAPI Backend) ---
def convert_file_via_api(file_bytes, original_filename, source_fmt, target_fmt):
    st.info(f"Sending {original_filename} to backend for conversion from {source_fmt} to {target_fmt}...")
    
    files = {'file': (original_filename, file_bytes.getvalue(), 'application/octet-stream')}
    data = {
        'from_format': source_fmt,
        'to_format': target_fmt,
        'font_size': st.session_state.get('font_size', 12) # Pass font size from editing
    }

    try:
        response = requests.post(f"{FASTAPI_BACKEND_URL}/convert", files=files, data=data)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        # FastAPI returns the file directly as response content
        converted_file_bytes = BytesIO(response.content)
        st.success("Conversion successful!")
        return converted_file_bytes
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Could not connect to the backend API at {FASTAPI_BACKEND_URL}. Please ensure it is running.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API conversion failed: {e}")
        if response is not None and response.content:
            try:
                error_detail = response.json().get("detail", "No specific error detail from API.")
                st.error(f"API Error Detail: {error_detail}")
            except json.JSONDecodeError:
                st.error(f"API returned non-JSON error: {response.text}")
        return None

# --- Main Conversion and Download Section ---
if uploaded_files:
    for idx, uploaded_file in enumerate(uploaded_files):
        st.divider()
        st.subheader(f"📄 File {idx + 1}: {uploaded_file.name}")
        
        # 1. Preview the file content
        preview_file(uploaded_file, source_format)

        # 2. Allow editing (if applicable)
        # Pass a copy of the uploaded file's BytesIO to editing to avoid pointer issues
        uploaded_file_copy_for_editing = BytesIO(uploaded_file.getvalue())
        edited_file_content = edit_content(uploaded_file_copy_for_editing, source_format)

        # 3. Perform conversion via backend API
        output = None
        if source_format in doc_types and target_format in doc_types:
            with st.spinner("Converting document file..."):
                output = convert_file_via_api(edited_file_content, uploaded_file.name, source_format, target_format)
        elif source_format in sheet_types and target_format in sheet_types:
            with st.spinner("Converting spreadsheet file..."):
                output = convert_file_via_api(edited_file_content, uploaded_file.name, source_format, target_format)
        else:
            st.error("❌ Cross-type conversions (e.g., DOCX → CSV) not supported.")
            continue

        # 4. Provide download and cloud save options
        if output:
            file_base = custom_name if custom_name else os.path.splitext(uploaded_file.name)[0]
            download_name = f"{file_base}_{idx + 1}.{target_format}" if len(uploaded_files) > 1 else f"{file_base}.{target_format}"

            st.success(f"✅ Conversion Done: {download_name}")
            
            col_dl, col_gdrive, col_dropbox = st.columns(3)
            with col_dl:
                st.download_button("⬇️ Download", data=output.getvalue(), file_name=download_name)
            
            # Cloud Storage Buttons
            with col_gdrive:
                if st.button("☁️ Save to Google Drive", key=f"gdrive_btn_{idx}"):
                    with st.spinner("Uploading to Google Drive..."):
                        try:
                            upload_to_google_drive(output.getvalue(), download_name)
                            st.success("Uploaded to Google Drive!")
                        except Exception as e:
                            st.error(f"Google Drive upload failed: {e}")
            
            with col_dropbox:
                if st.button("☁️ Save to Dropbox", key=f"dropbox_btn_{idx}"):
                    with st.spinner("Uploading to Dropbox..."):
                        try:
                            # Dropbox API expects bytes
                            upload_to_dropbox(DROPBOX_ACCESS_TOKEN, output.getvalue(), f"/{download_name}")
                            st.success("Uploaded to Dropbox!")
                        except Exception as e:
                            st.error(f"Dropbox upload failed: {e}")

 
