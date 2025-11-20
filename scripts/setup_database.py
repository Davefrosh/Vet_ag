"""
One-time script to setup the ARCON regulations database.
Chunks the document, generates embeddings, and loads into Supabase.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.embeddings import parse_arcon_document, generate_embeddings
from src.database import vector_store, create_match_function_sql


def main():
    """Main setup function."""
    print("\n" + "="*70)
    print("ARCON VETTING AGENT - DATABASE SETUP")
    print("="*70 + "\n")
    
    # Step 1: Parse and chunk the ARCON document
    print("Step 1: Parsing ARCON document...")
    arcon_path = "docs/arcon.md"
    
    if not os.path.exists(arcon_path):
        print(f"Error: {arcon_path} not found!")
        return
    
    chunks = parse_arcon_document(arcon_path)
    print(f"Extracted {len(chunks)} chunks\n")
    
    # Step 2: Generate embeddings
    print("Step 2: Generating embeddings...")
    chunks_with_embeddings = generate_embeddings(chunks)
    print(f"Generated embeddings for {len(chunks_with_embeddings)} chunks\n")
    
    # Step 3: Insert into Supabase
    print("Step 3: Inserting into Supabase...")
    
    # Check current count
    current_count = vector_store.get_count()
    print(f"Current chunks in database: {current_count}")
    
    if current_count > 0:
        response = input("Database already contains chunks. Do you want to add more? (yes/no): ")
        if response.lower() != 'yes':
            print("Setup cancelled.")
            return
    
    # Batch insert (50 at a time to avoid timeouts)
    batch_size = 50
    for i in range(0, len(chunks_with_embeddings), batch_size):
        batch = chunks_with_embeddings[i:i + batch_size]
        vector_store.insert_chunks(batch)
        print(f"  Inserted batch {i//batch_size + 1}/{(len(chunks_with_embeddings)//batch_size) + 1}")
    
    # Step 4: Verify insertion
    final_count = vector_store.get_count()
    print(f"\nSetup complete! Total chunks in database: {final_count}")
    
    # Print SQL function reminder
    print("\n" + "="*70)
    print("IMPORTANT: Run this SQL in Supabase SQL Editor (if not already done):")
    print("="*70)
    print(create_match_function_sql())
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

