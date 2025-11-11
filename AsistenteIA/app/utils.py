import sqlite3
import json
import os

DB_NAME = 'asv_memory.db'
CONFIG_FILE = 'user_config.json'

class MemoryManager:
    """Gestiona la base de datos local (SQLite) para el historial y JSON para la configuración."""

    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), DB_NAME))
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Crea la tabla de historial si no existe."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    # --- Gestión del Historial ---

    def save_message(self, role: str, content: str):
        """Guarda un nuevo mensaje en la base de datos."""
        self.cursor.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
        self.conn.commit()

    def load_history(self, limit=50) -> list:
        """Carga el historial de mensajes."""
        self.cursor.execute(
            "SELECT role, content FROM history ORDER BY timestamp DESC LIMIT ?", 
            (limit,)
        )
        raw_history = self.cursor.fetchall()
        system_prompt_length = 1 # El system prompt se añade aparte
        # Devolver en el formato [más antiguo -> más nuevo]
        return [{"role": row[0], "content": row[1]} for row in raw_history[::-1]]

    # --- Gestión de la Configuración ---
    
    def save_user_config(self, settings: dict):
        """Guarda un diccionario de configuraciones del usuario en un archivo JSON."""
        config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        with open(config_path, 'w') as f:
            json.dump(settings, f, indent=4)

    def load_user_config(self) -> dict:
        """Carga las configuraciones del usuario desde el archivo JSON."""
        config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}