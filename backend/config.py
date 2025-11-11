import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


class Config:
    """Configuración del asistente IA"""
    
    # IA Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyA-lww96btgpwJwduOIYXa7EhnnJC-xmoE')
    AI_MODEL = os.environ.get('AI_MODEL', 'gemini-2.0-flash-exp')
    
    # Google Search (opcional)
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
    GOOGLE_CSE_ID = os.environ.get('GOOGLE_CSE_ID', '')
    
    # App Settings
    ASSISTANT_NAME = os.environ.get('ASSISTANT_NAME', 'Asistente IA')
    THEME = os.environ.get('THEME', 'dark')
    
    # Database paths
    DB_PATH = os.path.join(ROOT_DIR, 'db')
    DOCS_COLLECTION = "documents"
    MEMORY_COLLECTION = "conversation_memory"
    
    @classmethod
    def ensure_directories(cls):
        """Crea los directorios necesarios si no existen"""
        if not os.path.exists(cls.DB_PATH):
            os.makedirs(cls.DB_PATH)
