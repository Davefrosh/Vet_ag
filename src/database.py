import supabase
from config import load_config
import time

def get_supabase_client():
    _, SUPABASE_URL, SUPABASE_SERVICE_KEY = load_config()
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase credentials not found in environment variables.")
    return supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class VectorStore:
    def __init__(self):
        self.client = get_supabase_client()
        self.table_name = "arcon_regulations"

    def insert_chunks(self, chunks):
        """
        Insert a list of chunks (dict with content, metadata, embedding) into Supabase.
        """
        try:
            response = self.client.table(self.table_name).insert(chunks).execute()
            return response.data
        except Exception as e:
            print(f"Error inserting chunks: {e}")
            raise e

    def get_count(self):
        """
        Get total count of rows in the table.
        """
        try:
            # exact=True needed for count
            response = self.client.table(self.table_name).select("*", count="exact", head=True).execute()
            return response.count
        except Exception as e:
            print(f"Error getting count: {e}")
            return 0

    def search_similar(self, query_embedding, match_threshold=0.3, match_count=5):
        """
        Search for similar regulations using the match_arcon_regulations RPC.
        """
        params = {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count
        }
        try:
            response = self.client.rpc("match_arcon_regulations", params).execute()
            return response.data
        except Exception as e:
            print(f"Error searching regulations: {e}")
            return []

# Global instance (lazy loaded)
_vector_store = None

def get_vector_store():
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

def insert_chunks(chunks):
    return get_vector_store().insert_chunks(chunks)

def search_similar_regulations(query_embedding, match_threshold=0.3, match_count=5):
    return get_vector_store().search_similar(query_embedding, match_threshold, match_count)

def create_match_function_sql():
    """
    Returns the SQL to create the similarity search function.
    Useful for setup scripts to display to user.
    """
    return """
-- Function for vector similarity search
CREATE OR REPLACE FUNCTION match_arcon_regulations(
  query_embedding vector(3072),
  match_threshold float DEFAULT 0.1,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    content,
    metadata,
    1 - (arcon_regulations.embedding <=> query_embedding) as similarity
  FROM arcon_regulations
  WHERE 1 - (arcon_regulations.embedding <=> query_embedding) > match_threshold
  ORDER BY arcon_regulations.embedding <=> query_embedding
  LIMIT match_count;
$$;
"""
