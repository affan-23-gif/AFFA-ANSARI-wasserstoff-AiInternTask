# Use a slim Python base image for smaller size
FROM python:3.11-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for Tesseract (OCR) and Poppler (for PDF processing)
# build-essential for compiling some Python packages
# libgl1 and libglib2.0-0 are common dependencies for image processing libraries like Pillow
# poppler-utils provides pdftotext which PyMuPDF might rely on for some features
# tesseract-ocr and tesseract-ocr-eng are the Tesseract engine and English language pack
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy your backend folder into the container
# This copies backend/ to /app/backend/
COPY backend/ /app/backend/

# Install Python dependencies from requirements.txt
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Create the directory for ChromaDB persistent data
# This is where ChromaDB will store its files inside the container
RUN mkdir -p /app/backend/data/chroma_db

# Expose the port that your FastAPI application will listen on
EXPOSE 8000

# Command to run your FastAPI application using Uvicorn
# 0.0.0.0 makes it accessible from outside the container
# backend.main:app means: look in the 'backend' folder, find 'main.py', and inside it, find the 'app' variable (your FastAPI instance).
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
