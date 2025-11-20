from langchain_core.tools import tool
from database import search_similar_regulations
from embeddings import generate_embedding

@tool
def check_arcon_compliance(query: str) -> str:
    """
    Consults the ARCON (Advertising Regulatory Council of Nigeria) regulations database 
    to check for compliance or retrieve specific articles.
    
    Args:
        query: A specific question or keyword about the advertisement content to check against regulations.
    """
    # Generate embedding for the query
    try:
        query_embedding = generate_embedding(query)
    except Exception as e:
        return f"Error generating embedding: {e}"

    # Search database
    results = search_similar_regulations(query_embedding, match_threshold=0.3, match_count=5)
    
    if not results:
        return "No specific ARCON regulations found matching this query. Please ensure the query is specific to advertising regulations."
    
    # Format results
    formatted_results = "Relevant ARCON Regulations:\n\n"
    for i, res in enumerate(results):
        content = res.get('content', '')
        metadata = res.get('metadata', {})
        title = metadata.get('title', 'Unknown Article')
        formatted_results += f"{i+1}. **{title}**\n{content}\n\n"
        
    return formatted_results

