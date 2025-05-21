import PyPDF2
import os
from typing import Optional
import logging

logging.basicConfig(level=logging.DEBUG)  # Or logging.INFO

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extracts text from a PDF file."""
    text = ""
    try:
        logging.debug(f"Attempting to open PDF: {pdf_path}")
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            logging.debug(f"PDF opened successfully. Pages: {len(reader.pages)}")
            for page in reader.pages:
                text += page.extract_text() or ""
            logging.debug("Text extraction complete.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from {pdf_path}: {e}", exc_info=True)  # Log with traceback
        return None

def process_document(file_path: str) -> Optional[str]:
    """Processes a document based on its file type."""

    _, file_extension = os.path.splitext(file_path)
    logging.info(f"Processing file: {file_path} with extension {file_extension}")

    if file_extension.lower() == ".pdf":
        text_content = extract_text_from_pdf(file_path)
        return text_content
    else:
        logging.warning(f"Unsupported file type: {file_extension}")
        return None