import os

def get_config(key):
    """
    Get configuration value from Streamlit secrets or environment variables.
    This lazy loading approach ensures secrets are loaded when needed, not at import time.
    """
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        # Fallback to .env for local development
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv(key)

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
