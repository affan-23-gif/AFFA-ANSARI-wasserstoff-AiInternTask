from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
import logging

logging.basicConfig(level=logging.INFO)

CHROMA_DB_PATH = "backend/data/chroma_db"
os.makedirs(CHROMA_DB_PATH, exist_ok=True)

_chroma_client = None  # Global variable for Chroma client
_chroma_collection_name = "my_collection"  # Global collection name

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = Chroma(
            persist_directory=CHROMA_DB_PATH,
            collection_name=_chroma_collection_name,  # Specify collection here
            embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        )
        logging.info(f"Initialized Chroma client at {CHROMA_DB_PATH}, collection={_chroma_collection_name}")
    return _chroma_client

def initialize_vector_database():
    """Initializes and returns the Chroma vector database."""
    db = get_chroma_client()  # Get the client, which also initializes the DB
    logging.info(f"Retrieved Chroma database client (or initialized) for collection '{_chroma_collection_name}'")
    return db

def add_document_to_database(db: Chroma, text: str, metadata: dict):
    """Adds a document and its metadata to the vector database."""
    try:
        db.add_texts([text], metadatas=[metadata])
        logging.info(f"Added document to database with metadata: {metadata}")
    except Exception as e:
        logging.error(f"Error adding document to database: {e}")
        raise  # Re-raise the exception

def query_vector_database(db: Chroma, query: str, k: int = 2):
    """
    Queries the vector database for the top k most similar documents.

    Args:
        db: The Chroma vector database.
        query: The user's query string.
        k: The number of top results to return.

    Returns:
        A list of documents that are most similar to the query.
    """

    results = db.similarity_search(query, k=k)  # Pass k directly
    return results