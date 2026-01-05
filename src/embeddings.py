import re
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import load_config

embeddings_model = None


def get_embeddings_model():
    global embeddings_model
    if embeddings_model is None:
        OPENAI_API_KEY, _, _, _, _ = load_config()
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in config")
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=OPENAI_API_KEY
        )
    return embeddings_model


def generate_embedding(text: str) -> List[float]:
    model = get_embeddings_model()
    text = text.replace("\n", " ")
    return model.embed_query(text)


def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    model = get_embeddings_model()
    texts = [chunk['content'].replace("\n", " ") for chunk in chunks]
    embeddings = model.embed_documents(texts)
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks


def parse_arcon_document(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

    text = text.replace('\r\n', '\n')
    article_splits = re.split(r'(?=\n#{2,3}\s+Article)', text)
    
    chunks = []
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    
    for article_text in article_splits:
        if not article_text.strip():
            continue
            
        header_match = re.search(r'(#{2,3}\s+Article.*)', article_text)
        title = header_match.group(1).strip().replace('#', '').strip() if header_match else "Introduction/General"
        content = article_text.strip()
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
    chunks = parse_arcon_document(file_path)
    chunks_with_embeddings = generate_embeddings(chunks)
    return chunks_with_embeddings
