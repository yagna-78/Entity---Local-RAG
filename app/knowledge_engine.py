import os
import glob
import logging
import shutil
import chromadb
import chromadb
# from sentence_transformers import SentenceTransformer
import pypdf
import traceback
from typing import List, Tuple

# Configuration
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))
COLLECTION_NAME = "entity_knowledge_collection"
# EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# RAG Hyperparameters
CHUNK_SIZE_CHARS = 600
CHUNK_OVERLAP_CHARS = 200
RETRIEVAL_K_QA = 3
RETRIEVAL_K_ADVISOR = 3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
# embedding_model = None
chroma_client = None
collection = None

def initialize_resources():
    global chroma_client, collection
    
    if collection is not None:
        return

    logger.info("Initializing Vector DB (Ollama Embeddings)...")
    # Persistent ChromaDB
    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    
    # Create or get collection with custom embedding function
    class LocalEmbeddingFunction(chromadb.EmbeddingFunction):
        def __call__(self, input: List[str]) -> List[List[float]]:
            # Batch embedding using Ollama
            embeddings = []
            import ollama
            for text in input:
                try:
                    # Using nomic-embed-text or mxbai-embed-large if available, else standard
                    # Fallback to qwen2.5:7b if specific embedding model not available? 
                    # Assuming nomic-embed-text is standard for ollama
                    resp = ollama.embeddings(model="nomic-embed-text", prompt=text)
                    embeddings.append(resp["embedding"])
                except Exception:
                    # Fallback to zeros? Or try another model?
                    # Let's try to use the main model for embeddings as fallback
                    try:
                        resp = ollama.embeddings(model="qwen2.5:7b", prompt=text)
                        embeddings.append(resp["embedding"])
                    except:
                        embeddings.append([0.0]*1024) # Dummy
            return embeddings

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=LocalEmbeddingFunction()
    )
    
    # Initial ingestion check
    try:
        if collection.count() == 0:
            ingest_data()
    except Exception as e:
        logger.error(f"Startup ingestion check failed: {e}")

def recursive_chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Splits text attempting to respect boundaries:
    1. Double newlines (Paragraphs)
    2. Single newlines
    3. Sentences (Periods)
    4. Spaces
    5. Fallback URL/Characters
    """
    if len(text) <= chunk_size:
        return [text]
        
    separators = ["\n\n", "\n", ". ", " ", ""]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:])
            break
            
        # Find best separator to break at
        best_end = -1
        for sep in separators:
            if sep == "":
                best_end = end # Force break
                break
            
            # Look for separator in the last `overlap` section of the chunk 
            # or simply look backwards from 'end'
            sep_idx = text.rfind(sep, start, end)
            
            # Ensure we make progress (don't split at start)
            if sep_idx != -1 and sep_idx > start:
                best_end = sep_idx + len(sep) # Include separator in this chunk or skip it? 
                # Usually we want to break AFTER the separator.
                break
        
        if best_end == -1:
             best_end = end # Fallback
             
        chunks.append(text[start:best_end].strip())
        
        # Move start forward, subtracting overlap
        next_start = best_end - overlap
        if next_start <= start: 
            # Prevent infinite loops if overlap >= chunk size or no progress
            next_start = start + chunk_size // 2 
            
        start = max(start + 1, next_start)
        
    return [c for c in chunks if c]


def ingest_data(force: bool = False):
    """
    Reads .txt files from the data directory, splits them, and stores embeddings.
    If force=True, it will clear the existing collection and re-ingest.
    """
    # Ensure resources are initialized
    if collection is None:
        initialize_resources()
        
    current_count = collection.count()
    if current_count > 0 and not force:
        logger.info(f"Database contains {current_count} chunks. Skipping initial ingestion. (Use /ingest to force)")
        return

    logger.info("Scanning for data files...")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    files = txt_files + pdf_files
    
    if not files:
        logger.warning("No .txt or .pdf files found in data directory.")
        return

    # If forcing, clear existing data
    if force and current_count > 0:
        logger.info("Clearing existing collection for re-ingestion...")
        try:
            existing_ids = collection.get()['ids']
            if existing_ids:
                collection.delete(ids=existing_ids)
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    documents = []
    metadatas = []
    ids = []
    
    for file_path in files:
        try:
            content = ""
            filename = os.path.basename(file_path)
            
            if file_path.lower().endswith(".pdf"):
                try:
                    reader = pypdf.PdfReader(file_path)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            content += text + "\n"
                except Exception as pdf_err:
                    logger.error(f"Error reading PDF {filename}: {pdf_err}")
                    continue
            else:
                # Text file
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            if not content.strip():
                logger.warning(f"File {filename} is empty or unreadable.")
                continue

            # Advanced Chunking
            chunks = recursive_chunk_text(content, CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS)

            for idx, chunk in enumerate(chunks):
                if len(chunk) > 20: # Ignore noise
                    documents.append(chunk)
                    metadatas.append({"source": filename})
                    ids.append(f"{filename}_{idx}")
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            logger.error(traceback.format_exc())

    if documents:
        logger.info(f"Ingesting {len(documents)} chunks from {len(files)} files...")
        batch_size = 64 # Smaller batch size for stability
        # Process in batches 
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            collection.add(documents=batch_docs, metadatas=batch_meta, ids=batch_ids)
        logger.info("Ingestion complete.")
    else:
        logger.info("No valid content found to ingest.")

def retrieve_context(query: str, n_results: int = RETRIEVAL_K_QA) -> Tuple[str, List[str]]:
    """
    Query the vector DB for relevant chunks.
    """
    if collection is None:
        initialize_resources()
        
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if not results['documents'] or not results['documents'][0]:
        return "", []
        
    # Extract unique sources
    sources = set()
    if results['metadatas'] and results['metadatas'][0]:
        for meta in results['metadatas'][0]:
             if 'source' in meta:
                 sources.add(meta['source'])

    return "\n\n---\n\n".join(results['documents'][0]), list(sources)

def get_collection_count():
    if collection is None:
        initialize_resources()
    return collection.count()
