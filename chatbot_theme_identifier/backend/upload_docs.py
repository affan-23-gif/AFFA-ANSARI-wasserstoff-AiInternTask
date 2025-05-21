import requests
import os

# Make sure your FastAPI backend is running (e.g., on http://localhost:8000)
BACKEND_URL = "http://localhost:8000/upload/"
DOCS_DIR = "backend/data/raw_docs/" # Adjust this path if your documents are elsewhere

def upload_documents_from_folder(folder_path):
    uploaded_count = 0
    failed_count = 0
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith(".pdf"):
            print(f"Uploading: {filename}...")
            try:
                with open(file_path, "rb") as f:
                    files = {"files": (filename, f, "application/pdf")}
                    response = requests.post(BACKEND_URL, files=files)
                    response.raise_for_status() # Raise an exception for HTTP errors
                    print(f"Successfully uploaded {filename}: {response.json()}")
                    uploaded_count += 1
            except requests.exceptions.RequestException as e:
                print(f"Failed to upload {filename}: {e}")
                failed_count += 1
            except Exception as e:
                print(f"An unexpected error occurred with {filename}: {e}")
                failed_count += 1
        else:
            print(f"Skipping non-PDF file or directory: {filename}")

    print(f"\n--- Upload Summary ---")
    print(f"Total files attempted: {uploaded_count + failed_count}")
    print(f"Successfully uploaded: {uploaded_count}")
    print(f"Failed uploads: {failed_count}")

if __name__ == "__main__":
    if not os.path.exists(DOCS_DIR):
        print(f"Error: Document directory '{DOCS_DIR}' not found. Please create it and place your PDFs inside.")
    else:
        upload_documents_from_folder(DOCS_DIR)