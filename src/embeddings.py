import re
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import OPENAI_API_KEY

# Initialize OpenAI Embeddings
embeddings_model = None

def get_embeddings_model():
    global embeddings_model
    if embeddings_model is None:
        if not OPENAI_API_KEY:
             raise ValueError("OPENAI_API_KEY not set in config")
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=OPENAI_API_KEY
        )
    return embeddings_model

def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single string."""
    model = get_embeddings_model()
    # Remove newlines to avoid interference with embedding generation in some models
    text = text.replace("\n", " ") 
    return model.embed_query(text)

def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate embeddings for a list of chunks.
    Modifies the list in-place or returns a new list with 'embedding' key.
    """
    model = get_embeddings_model()
    texts = [chunk['content'].replace("\n", " ") for chunk in chunks]
    
    # Embed in batches if needed, but langchain handles this usually
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = model.embed_documents(texts)
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks

def parse_arcon_document(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses the ARCON markdown file into chunks based on Articles,
    then applies overlapping chunking strategy within articles if they are large.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

    # 1. Initial split by Article to preserve metadata context
    # Regex looks for lines starting with ## Article or ### Article
    # We normalize newlines first
    text = text.replace('\r\n', '\n')
    
    # Split based on markdown headers that denote articles.
    # The lookahead (?=...) keeps the delimiter in the next chunk
    article_splits = re.split(r'(?=\n#{2,3}\s+Article)', text)
    
    chunks = []
    
    # Initialize text splitter for overlapping strategy
    # This satisfies the requirement for "overlapping strategy"
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    
    for article_text in article_splits:
        if not article_text.strip():
            continue
            
        # Extract title/header for metadata
        header_match = re.search(r'(#{2,3}\s+Article.*)', article_text)
        title = header_match.group(1).strip().replace('#', '').strip() if header_match else "Introduction/General"
        
        # Basic cleaning
        content = article_text.strip()
        
        # Apply overlapping chunking to this article
        sub_chunks = text_splitter.create_documents([content])
        
        for i, sub_chunk in enumerate(sub_chunks):
            chunk_metadata = {
                "title": title,
                "source": "arcon_regulations",
                "chunk_index": i,
                "total_article_chunks": len(sub_chunks)
            }
            
            chunks.append({
                "content": sub_chunk.page_content,
                "metadata": chunk_metadata
            })
    
    return chunks

def process_and_embed_document(file_path: str):
    """
    Orchestrates parsing and embedding.
    Returns list of dicts ready for DB insertion.
    """
    chunks = parse_arcon_document(file_path)
    chunks_with_embeddings = generate_embeddings(chunks)
    return chunks_with_embeddings
