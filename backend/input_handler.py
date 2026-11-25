"""
input_handler.py
------------------
Module 3: Input Handler

This module takes whatever the user gives us — pasted text, a .txt file,
a .pdf file, or a .docx (Word) file — and turns it into plain text that
Module 2 (prompt_engine.py) can simplify.

Nothing in here calls the AI. This module's ONLY job is:
"Take messy input -> return clean text."
"""

import os
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from pypdf import PdfReader
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


# ---------------------------------------------------------------------------
# HANDLE PASTED TEXT
# The simplest case — user just types/pastes text directly.
# ---------------------------------------------------------------------------

def handle_pasted_text(raw_text: str) -> dict:
    """
    Cleans up pasted text and validates it isn't empty.

    Returns:
        {"success": True/False, "text": "<cleaned text>", "error": None/"message"}
    """
    if raw_text is None:
        return {"success": False, "text": None, "error": "No text was provided."}

    cleaned = raw_text.strip()

    if not cleaned:
        return {"success": False, "text": None, "error": "Pasted text is empty."}

    return {"success": True, "text": cleaned, "error": None}


# ---------------------------------------------------------------------------
# HANDLE .txt FILES
# ---------------------------------------------------------------------------

def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# HANDLE .pdf FILES
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    all_text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            all_text.append(page_text)

    return "\n".join(all_text)


# ---------------------------------------------------------------------------
# HANDLE .docx (Word) FILES
# ---------------------------------------------------------------------------

def extract_text_from_docx(file_path: str) -> str:
    document = Document(file_path)
    blocks = []

    for element in document.element.body.iterchildren():
        if isinstance(element, CT_P):
            paragraph = Paragraph(element, document)
            if paragraph.text.strip():
                blocks.append(paragraph.text.strip())
        elif isinstance(element, CT_Tbl):
            table = Table(element, document)
            rows = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                blocks.append("\n".join(rows))

    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# MAIN FUNCTION — this is what other modules should call for FILE uploads
# ---------------------------------------------------------------------------

def handle_uploaded_file(file_path: str) -> dict:
    """
    Detects the file type from its extension and extracts text accordingly.

    Parameters:
        file_path: full path to the uploaded file on disk

    Returns:
        {"success": True/False, "text": "<extracted text>", "error": None/"message"}
    """
    if not os.path.exists(file_path):
        return {"success": False, "text": None, "error": f"File not found: {file_path}"}

    extension = os.path.splitext(file_path)[1].lower()

    try:
        if extension == ".txt":
            extracted = extract_text_from_txt(file_path)
        elif extension == ".pdf":
            extracted = extract_text_from_pdf(file_path)
        elif extension == ".docx":
            extracted = extract_text_from_docx(file_path)
        else:
            return {
                "success": False,
                "text": None,
                "error": f"Unsupported file type: {extension}. Please use .txt, .pdf, or .docx",
            }

        extracted = extracted.strip()

        if not extracted:
            if extension == ".pdf":
                error = (
                    "No selectable text was found in this PDF. If it is scanned or image-only, "
                    "upload an OCR-searchable PDF instead."
                )
            elif extension == ".docx":
                error = "No readable paragraph or table text was found in this DOCX file."
            else:
                error = "This TXT file is empty or contains no readable text."
            return {
                "success": False,
                "text": None,
                "error": error,
            }

        return {"success": True, "text": extracted, "error": None}

    except Exception as e:
        return {"success": False, "text": None, "error": f"Failed to read file: {str(e)}"}


# ---------------------------------------------------------------------------
# QUICK TEST — run this file directly to check Module 3 works:
#   python input_handler.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing handle_pasted_text() ...")
    result = handle_pasted_text("  The server uses a load balancer.  ")
    print(result)

    print("\nTesting handle_pasted_text() with empty input ...")
    result = handle_pasted_text("   ")
    print(result)

    print("\nTo test file uploads, create a sample file named 'sample.txt'")
    print("in this same backend folder, then run:")
    print('  python -c "from input_handler import handle_uploaded_file; print(handle_uploaded_file(\'sample.txt\'))"')