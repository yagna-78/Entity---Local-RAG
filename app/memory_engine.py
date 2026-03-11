import logging
import chromadb
from datetime import datetime
from typing import List, Dict, Optional
import json

# Re-use existing embedding setup
from knowledge_engine import initialize_resources, DB_DIR

logger = logging.getLogger(__name__)

MEMORY_COLLECTION_NAME = "entity_conversation_memory"
memory_collection = None

def get_memory_collection():
    global memory_collection
    if memory_collection:
        return memory_collection
        
    try:
        initialize_resources() # Ensures DB_DIR is ready
        client = chromadb.PersistentClient(path=DB_DIR)
        
        # Proper wrapping for embedding function (Ollama)
        class LocalEmbeddingFunction(chromadb.EmbeddingFunction):
            def __call__(self, input: List[str]) -> List[List[float]]:
                # Batch embedding using Ollama
                embeddings = []
                import ollama
                for text in input:
                    try:
                        resp = ollama.embeddings(model="nomic-embed-text", prompt=text)
                        embeddings.append(resp["embedding"])
                    except Exception:
                        try:
                            resp = ollama.embeddings(model="qwen2.5:7b", prompt=text)
                            embeddings.append(resp["embedding"])
                        except:
                            embeddings.append([0.0]*1024) # Dummy
                return embeddings

        memory_collection = client.get_or_create_collection(
            name=MEMORY_COLLECTION_NAME,
            embedding_function=LocalEmbeddingFunction()
        )
        return memory_collection
    except Exception as e:
        logger.error(f"Failed to initialize memory collection: {e}")
        return None

def store_exchange(user_query: str, assistant_response: str, metadata: Dict = {}):
    """
    Stores a conversation turn into vector memory.
    """
    try:
        col = get_memory_collection()
        if not col:
            return

        # Create a rich text representation of the exchange
        # We embed the query primarily, but store the response as metadata/document
        # Actually better to embed: "User: <q> | Assistant: <a>"
        
        interaction_text = f"User: {user_query}\nAssistant: {assistant_response}"
        
        # ID is timestamp based
        interaction_id = f"mem_{int(datetime.now().timestamp())}"
        
        # Meta
        meta = metadata.copy()
        meta['timestamp'] = datetime.now().isoformat()
        meta['type'] = 'conversation'
        
        col.add(
            documents=[interaction_text],
            metadatas=[meta],
            ids=[interaction_id]
        )
        logger.info(f"Stored interaction {interaction_id} in memory.")
        
    except Exception as e:
        logger.error(f"Memory Store Error: {e}")

def retrieve_relevant_history(query: str, n_results: int = 3) -> str:
    """
    Retrieves past relevant conversations.
    """
    try:
        col = get_memory_collection()
        if not col or col.count() == 0:
            return ""

        results = col.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return ""
            
        # Format for context injection
        history_context = "### Relevant Past Conversations:\n"
        for i, doc in enumerate(results['documents'][0]):
            history_context += f"- {doc}\n"
            
        return history_context
        
    except Exception as e:
        logger.error(f"Memory Retrieval Error: {e}")
        return ""
