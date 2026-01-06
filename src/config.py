import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


def get_config(key: str) -> str | None:
    value = os.getenv(key)
    return value.strip() if value else None


OPENAI_API_KEY = None
SUPABASE_URL = None
SUPABASE_SERVICE_KEY = None
ASSEMBLYAI_API_KEY = None
API_SECRET_KEY = None


def load_config():
    global OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, ASSEMBLYAI_API_KEY, API_SECRET_KEY
    if OPENAI_API_KEY is None:
        OPENAI_API_KEY = get_config("OPENAI_API_KEY")
        SUPABASE_URL = get_config("SUPABASE_URL")
        SUPABASE_SERVICE_KEY = get_config("SUPABASE_SERVICE_KEY")
        ASSEMBLYAI_API_KEY = get_config("ASSEMBLYAI_API_KEY")
        API_SECRET_KEY = get_config("API_SECRET_KEY")
    return OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, ASSEMBLYAI_API_KEY, API_SECRET_KEY
