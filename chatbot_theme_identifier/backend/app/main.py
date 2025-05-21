from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from typing import List, Optional, Dict, Any
from langchain_community.embeddings import SentenceTransformerEmbeddings
import pytesseract
from PIL import Image
from langchain_community.vectorstores import Chroma
import uuid
import os
from pydantic import BaseModel, Field
from groq import Groq
import logging
from langchain_core.documents import Document
from collections import defaultdict
import json # <--- ADD THIS IMPORT

from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import fitz

# Define the Pydantic model for your query request
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    output_format: Optional[str] = None

app = FastAPI()
@app.get("/")
def root():
    return {"message": "Backend is up and running."}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "null",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
db = None
embedding_function = None
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
logging.basicConfig(level=logging.INFO)
if not GROQ_API_KEY:
    logging.warning("GROQ_API_KEY is not set in environment variables")

@app.on_event("startup")
async def startup_event():
    global db, embedding_function
    embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory="backend/data/chroma_db", embedding_function=embedding_function)

def is_potential_paragraph_start(block):
    x0 = block[0]
    return x0 > 50

def load_and_store_documents(file_paths: List[str]):
    global db
    documents = []

    print("--- Running the paragraph-grouping load_and_store_documents ---")

    for file_path in file_paths:
        try:
            doc = fitz.open(file_path)
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)

                page_text_content = ""
                if not page.get_text("text").strip() and len(page.get_images()) > 0:
                    logging.info(f"Page {page_num + 1} of {file_path} appears scanned. Attempting OCR.")
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    try:
                        page_text_content = pytesseract.image_to_string(img)
                        ocr_blocks = []
                        for para_text in page_text_content.split('\n\n'):
                            if para_text.strip():
                                ocr_blocks.append((0.0, 0.0, 0.0, 0.0, para_text.strip(), 0, 0))
                        blocks = ocr_blocks
                    except Exception as ocr_e:
                        logging.error(f"Error during OCR for page {page_num + 1} of {file_path}: {ocr_e}")
                        blocks = []
                else:
                    blocks = page.get_text("blocks")

                current_paragraph = ""
                current_paragraph_blocks = []

                for i, block in enumerate(blocks):
                    text_content = block[4].strip()

                    if text_content:
                        is_new_paragraph_start = False
                        if len(block) > 4 and isinstance(block[0], (int, float)):
                            is_new_paragraph_start = is_potential_paragraph_start(block)
                        else:
                            pass

                        if is_new_paragraph_start and current_paragraph:
                            doc_id = str(uuid.uuid4())
                            metadata = {
                                'document_id': doc_id,
                                'source': file_path,
                                'page_number': page_num + 1,
                                'paragraph_start': current_paragraph_blocks[0][0] if current_paragraph_blocks and isinstance(current_paragraph_blocks[0][0], (int, float)) else 0.0,
                                'paragraph_end': current_paragraph_blocks[-1][2] if current_paragraph_blocks and isinstance(current_paragraph_blocks[-1][2], (int, float)) else 0.0,
                            }
                            documents.append(Document(page_content=current_paragraph, metadata=metadata))
                            current_paragraph = text_content
                            current_paragraph_blocks = [block]
                        else:
                            if not current_paragraph:
                                current_paragraph = text_content
                            else:
                                current_paragraph += " " + text_content
                            current_paragraph_blocks.append(block)

            if current_paragraph:
                doc_id = str(uuid.uuid4())
                metadata = {
                    'document_id': doc_id,
                    'source': file_path,
                    'page_number': page_num + 1,
                    'paragraph_start': current_paragraph_blocks[0][0] if current_paragraph_blocks and isinstance(current_paragraph_blocks[0][0], (int, float)) else 0.0,
                    'paragraph_end': current_paragraph_blocks[-1][2] if current_paragraph_blocks and isinstance(current_paragraph_blocks[-1][2], (int, float)) else 0.0,
                }
                documents.append(Document(page_content=current_paragraph, metadata=metadata))

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}", exc_info=True)

    print("\n--- Documents before splitting ---")
    for doc in documents:
        print(f"   Metadata: {doc.metadata}")
        print(f"   Content: {doc.page_content[:100]}...\n")

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = [doc for doc in text_splitter.split_documents(documents) if doc.page_content.strip()]

    if docs:
        db.add_documents(docs)
        logging.info(f"Added {len(docs)} document chunks to ChromaDB from {file_paths}")
    else:
        logging.warning("No valid documents to add to ChromaDB.")

@app.post("/upload/")
async def upload_documents(files: List[UploadFile]):
    """Handles document uploads."""
    file_paths = []
    for file in files:
        file_path = f"backend/data/temp/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        file_paths.append(file_path)
    load_and_store_documents(file_paths)
    return {"message": "Documents uploaded and processed successfully"}

class Citation(BaseModel):
    document_id: str
    source: str
    page_number: int
    paragraph_start: float
    paragraph_end: float
    snippet_text: str

class ThemeResponse(BaseModel): # <--- MODIFIED
    theme_name: str # Renamed from 'theme'
    theme_description: Optional[str] = None # Added for description
    citations: List[Citation]

def extract_themes_with_citations(query: str, relevant_documents: List[Document]) -> Dict[str, Any]:
    global GROQ_API_KEY

    unique_snippets_with_metadata = []
    # Create a mapping from display ID (e.g., DOC001) to actual Document object for easy lookup
    doc_id_map = {}
    for i, doc in enumerate(relevant_documents):
        display_doc_id = f"DOC{i + 1:03d}"
        unique_snippets_with_metadata.append(
            (doc.page_content, display_doc_id, doc.metadata.get('source', 'unknown'), doc.metadata.get('page_number', 1),
             doc.metadata.get('paragraph_start', 0.0), doc.metadata.get('paragraph_end', 0.0))
        )
        doc_id_map[display_doc_id] = doc # Store the original document object

    # --- LLM-Based Theme Extraction (JSON Output) ---
    context_prompt_for_themes = "\n\n".join(
        f"DOC ID: {doc_id}\nSnippet: {snippet}" for snippet, doc_id, _, _, _, _ in unique_snippets_with_metadata)

    theme_prompt = f"""
    Based on the following text snippets (with their document IDs) and the user's query: '{query}', identify 3-5 distinct and concise common themes.
    For each theme, provide:
    1. A concise 'theme_name'.
    2. A brief 'theme_description' explaining what the theme highlights.
    3. A list of 'document_ids' (from the provided DOC### identifiers) that are relevant to this theme.

    **Output your response as a JSON object with a single key "themes" which contains a JSON array of theme objects.**
    Each theme object must have "theme_name", "theme_description", and "document_ids" fields.
    Ensure the "document_ids" are from the relevant snippets provided.
    Do NOT include any other text, preamble, or markdown outside the JSON.

    Example JSON structure:
    {{
      "themes": [
        {{
          "theme_name": "Theme A",
          "theme_description": "Description of Theme A.",
          "document_ids": ["DOC001", "DOC003"]
        }},
        {{
          "theme_name": "Theme B",
          "theme_description": "Description of Theme B.",
          "document_ids": ["DOC002"]
        }}
      ]
    }}

    Text Snippets:
    {context_prompt_for_themes}
    """
    extracted_themes_data = [] # Initialize as empty list
    try:
        client = Groq(api_key=GROQ_API_KEY)
        theme_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": theme_prompt}
            ],
            model="llama3-8b-8192",
            response_format={"type": "json_object"} # <--- CRITICAL: Request JSON output
        )
        themes_raw_json = theme_completion.choices[0].message.content
        # Assuming Groq returns clean JSON, if not, you might need to strip markdown ```json ... ```
        parsed_themes_response = json.loads(themes_raw_json)
        extracted_themes_data = parsed_themes_response.get("themes", []) # Get the array under the "themes" key

        extracted_themes_for_response = []
        for theme_item in extracted_themes_data:
            theme_citations = []
            for doc_id_llm in theme_item.get("document_ids", []):
                if doc_id_llm in doc_id_map: # Check if the LLM provided DOC ID exists
                    doc_orig = doc_id_map[doc_id_llm]
                    citation = Citation(
                        document_id=doc_id_llm, # Use the display ID like DOC001
                        source=doc_orig.metadata.get('source', 'unknown'),
                        page_number=doc_orig.metadata.get('page_number', 1),
                        paragraph_start=doc_orig.metadata.get('paragraph_start', 0.0),
                        paragraph_end=doc_orig.metadata.get('paragraph_end', 0.0),
                        snippet_text=doc_orig.page_content,
                    )
                    theme_citations.append(citation)

            extracted_themes_for_response.append(ThemeResponse(
                theme_name=theme_item.get("theme_name", "Unknown Theme"),
                theme_description=theme_item.get("theme_description"),
                citations=theme_citations
            ))
        extracted_themes = extracted_themes_for_response # This is now a list of ThemeResponse objects

    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from Groq themes: {e}", exc_info=True)
        extracted_themes = [ThemeResponse(theme_name="Theme Extraction Error", theme_description="Could not parse themes from LLM. Raw response might be invalid JSON.", citations=[])]
    except Exception as e:
        extracted_themes = [ThemeResponse(theme_name="Theme Extraction Error", theme_description=f"Error extracting themes: {e}", citations=[])]
        logging.error(f"Error extracting themes: {e}", exc_info=True)

    if not extracted_themes:
        extracted_themes = [ThemeResponse(theme_name="No Themes Identified", theme_description="The LLM did not identify any specific themes.", citations=[])]

    # --- LLM-Based Answer Generation ---
    context_prompt_answer = "\n\n".join(
        f"Source: {source}, Page: {page}, Paragraph Start: {p_start}, Paragraph End: {p_end}\nSnippet: {snippet}"
        for snippet, _, source, page, p_start, p_end in unique_snippets_with_metadata)

    llm_prompt = f"""
    You are an expert researcher. Answer the user's question concisely and accurately using only the information provided in the snippets below.
    Cite the source document using the format (Citation: (Document ID, Page: Paragraph Start-End)) to support your answer.
    Focus on providing a direct answer to the query '{query}'.  Do not include information that is not directly relevant.
    If a snippet is not relevant to the query, or provides only tangential information, ignore it.

    Question: {query}

    Snippets:
    {context_prompt_answer}
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": llm_prompt}
            ],
            model="llama3-8b-8192",
        )
        llm_text = chat_completion.choices[0].message.content
    except Exception as e:
        llm_text = "Error generating answer."
        logging.error(f"Error generating answer: {e}", exc_info=True)

    # --- Combine Themes and Answer ---
    final_response: Dict[str, Any] = {
        "themes": [t.model_dump() for t in extracted_themes], # Convert Pydantic models to dicts for JSON serialization
        "answer": llm_text,
        "original_query": query,
        "original_llm_response": llm_text
    }
    return final_response

@app.post("/query/")
async def query_documents(request: QueryRequest):
    """Handles user queries against the stored documents."""
    global db

    user_query = request.query
    output_format = request.output_format

    relevant_documents = db.similarity_search(user_query, k=5)

    final_response = extract_themes_with_citations(user_query, relevant_documents)

    if output_format == "tabular":
        tabular_results = []
        for i, doc in enumerate(relevant_documents):
            doc_id = f"DOC{i + 1:03d}"
            tabular_results.append({
                "Document ID": doc_id,
                "Extracted Answer": doc.page_content[:200],
                "Citation": f"{doc.metadata.get('source', 'unknown')}, Page: {doc.metadata.get('page_number')}, Paragraph Start-End: {doc.metadata.get('paragraph_start')}-{doc.metadata.get('paragraph_end')}"
            })
        return {"tabular_results": tabular_results}
    else:
        # In this else block, final_response['themes'] already contains ThemeResponse objects
        # that are converted to dicts by model_dump() right before returning from extract_themes_with_citations.
        # So, we can directly return final_response, as it's already structured correctly.
        return final_response # This should be the structure already, no need to re-process themes here

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)