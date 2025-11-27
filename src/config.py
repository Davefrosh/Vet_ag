import os
from pathlib import Path

def get_config(key):
    """
    Get configuration value from Streamlit secrets or environment variables.
    This lazy loading approach ensures secrets are loaded when needed, not at import time.
    """
    # First try environment variables (already loaded from .env)
    from dotenv import load_dotenv
    # Load .env from project root (parent directory of src/)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    value = os.getenv(key)
    if value:
        return value
    
    # Then try Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    # If both fail, check if we have a secrets.toml file to parse manually
    secrets_path = Path(__file__).parent.parent / '.streamlit' / 'secrets.toml'
    if secrets_path.exists():
        try:
            # Simple parsing for our needs
            with open(secrets_path, 'r') as f:
                for line in f:
                    if line.strip().startswith(key):
                        # Extract value between quotes
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            value = parts[1].strip().strip('"')
                            return value
        except:
            pass
    
    return None

# Lazy loaded configuration
OPENAI_API_KEY = None
SUPABASE_URL = None
SUPABASE_SERVICE_KEY = None

def load_config():
    """Load all configuration values."""
    global OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
    if OPENAI_API_KEY is None:
        OPENAI_API_KEY = get_config("OPENAI_API_KEY")
        SUPABASE_URL = get_config("SUPABASE_URL")
        SUPABASE_SERVICE_KEY = get_config("SUPABASE_SERVICE_KEY")
    return OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
