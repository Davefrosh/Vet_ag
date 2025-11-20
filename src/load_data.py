from src.embeddings import process_and_embed_document
from src.database import insert_chunks
import os

def main():
    file_path = os.path.join("docs", "arcon.md")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print("Processing and embedding document...")
    try:
        chunks = process_and_embed_document(file_path)
        
        if chunks:
            print(f"Inserting {len(chunks)} chunks into Supabase...")
            insert_chunks(chunks)
            print("Done!")
        else:
            print("No chunks to insert.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

