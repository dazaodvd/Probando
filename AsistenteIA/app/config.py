import json
import os
from typing import Dict, Any

# Nombre y ubicación del archivo de configuración
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

class Config:
    """
    Clase de configuración que carga y gestiona los parámetros
    desde el archivo config.json.
    """
    def __init__(self):
        self._data: Dict[str, Any] = {}
        # Solamente cargamos la configuración, no asignamos atributos redundantes.
        self._load_config() 

    def _load_config(self):
        """
        Intenta cargar la configuración desde config.json. 
        Crea un archivo por defecto si no existe.
        """
        # Valores por defecto para crear un archivo nuevo
        default_data = {
            "assistant_name": "Asistente IA",
            "theme": "dark",
            "GEMINI_API_KEY": "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",
            "ai_model": "gemini-2.5-flash",
            "GOOGLE_API_KEY": "AIzaSyBB4yR1muJmJVNBzI6q_GtSAugeNJhrKus",
            "GOOGLE_CSE_ID": "4368144c3a0074f98"
        }

        if not os.path.exists(CONFIG_FILE):
            print(f"❌ ADVERTENCIA: No se encontró el archivo de configuración en {CONFIG_FILE}.")
            self._data = default_data
            self._save_config()
            print("❗ Se creó un archivo config.json con valores por defecto. Por favor, llénalo y vuelve a ejecutar.")
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
                
            # CRÍTICO: Si el JSON cargado está incompleto, lo completamos con valores por defecto
            # Esto evita que se sobrescriban tus claves, pero asegura que todos los atributos existan.
            for key, value in default_data.items():
                if key not in self._data:
                    self._data[key] = value

        except json.JSONDecodeError as e:
            print(f"❌ ERROR CRÍTICO: El archivo config.json no es un JSON válido. Revisa la sintaxis (comas y corchetes). Error: {e}")
            self._data = {} # Deja los datos vacíos si hay error de sintaxis

        except Exception as e:
            print(f"❌ ERROR al cargar config.json: {e}")
            self._data = {}

    def _save_config(self):
        """Guarda la configuración actual en el archivo."""
        try:
            if self._data:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=4)
        except Exception as e:
            print(f"❌ ERROR al guardar config.json: {e}")

    # --- Propiedades de Acceso (Los @property) ---
    # Los atributos se leen directamente desde el diccionario _data

    @property
    def ASSISTANT_NAME(self):
        return self._data.get("assistant_name", "Asistente IA")

    @property
    def THEME(self):
        return self._data.get("theme", "dark")

    @property
    def AI_MODEL(self):
        return self._data.get("ai_model", "gemini-2.5-flash")
        
    @property
    def GEMINI_API_KEY(self):
        # Lee la clave. Busca GEMINI_API_KEY (mayúsculas) primero y luego gemini_api_key (minúsculas)
        # Esto soluciona problemas de nomenclatura histórica.
        return self._data.get("GEMINI_API_KEY", self._data.get("gemini_api_key", None))

    @property
    def GOOGLE_API_KEY(self):
        return self._data.get("GOOGLE_API_KEY", None)
        
    @property
    def GOOGLE_CSE_ID(self):
        return self._data.get("GOOGLE_CSE_ID", None)