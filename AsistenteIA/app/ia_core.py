from google import genai
from google.genai import types 
from .config import Config
from .actions import SystemActions 
from .document_loader import DocumentLoader 
import string 
import threading 
import os 
    
config = Config()

# Inicialización temporal, la instancia final se creará en __init__
document_loader = None 

# --- Importaciones condicionales de LangChain para Agentes y Herramientas ---
AGENT_ENABLED = False
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Imports del Agente (Rutas estables)
    from langchain.agents import initialize_agent 
    from langchain.agents import AgentType
    from langchain.agents import Tool
    
    # Importación de la herramienta de Google Search (desde COMMUNITY)
    from langchain_community.tools import GoogleSearchAPIWrapper 
    
    AGENT_ENABLED = True
    print("✅ Módulo Agente (LangChain) activado con éxito.")
except ImportError as e:
    print(f"❌ ADVERTENCIA: Agente deshabilitado. Fallo en la importación de LangChain: {e.name}")
except Exception as e:
    print(f"❌ ADVERTENCIA: Agente deshabilitado debido a error crítico: {e}")

# -----------------------------------------------------

class IACore:
    def __init__(self):
        
        # --- LÍNEA DE DEPURACIÓN CRÍTICA (PARA DIAGNOSTICAR LA CLAVE) ---
        key_length = len(config.GEMINI_API_KEY) if config.GEMINI_API_KEY else 0
        print(f"DEBUG: Longitud de la clave leída: {key_length}")
        
        # 1. Inicialización del Cliente base de Gemini (SDK Nativo)
        self.client = genai.Client(
            api_key=config.GEMINI_API_KEY
        )
        
        # 2. Inicialización del Document Loader con inyección del cliente
        global document_loader
        document_loader = DocumentLoader(gemini_client=self.client) 
        
        # 3. Inicialización del Modelo LLM general
        self.llm_model = config.AI_MODEL 
        
        # Inicialización del Agente (Si está habilitado)
        self.agent = None
        self.tools = []
        self.system_actions = SystemActions()

        if AGENT_ENABLED:
            try:
                # Inicialización del LLM para el Agente (requiere ChatGoogleGenerativeAI)
                self.llm_agent = ChatGoogleGenerativeAI(
                    model=self.llm_model, 
                    temperature=0, 
                    client=self.client
                )
                
                # Inicialización de la herramienta de búsqueda de Google (si las claves existen)
                if config.GOOGLE_CSE_ID and config.GOOGLE_API_KEY:
                    search = GoogleSearchAPIWrapper(
                        google_api_key=config.GOOGLE_API_KEY, 
                        google_cse_id=config.GOOGLE_CSE_ID
                    )
                    self.tools.append(
                        Tool(
                            name="Búsqueda_Web_Google",
                            description="Útil para responder preguntas sobre eventos actuales o información general.",
                            func=search.run
                        )
                    )
                    print("✅ Herramienta de Búsqueda Web activada.")
                else:
                    print("❌ ADVERTENCIA: La herramienta de Google Search no pudo inicializarse. Faltan claves en config.json.")

                # Inicialización del Agente Principal
                self.agent = initialize_agent(
                    self.tools, 
                    self.llm_agent, 
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=True, # Cambiar a False en producción
                    handle_parsing_errors=True
                )
                
            except Exception as e:
                print(f"❌ ADVERTENCIA: Agente deshabilitado debido a error en la inicialización: {e}")
                self.agent = None
                
        print("Sistema Operativo detectado: " + os.name)
        print("✅ Módulo de IA Core inicializado.")

    # Mantenemos las funciones de chat y clasificación de intención

    def chat(self, prompt: str) -> str:
        """Determina la intención y delega la respuesta."""
        
        # 1. Clasificar Intención (DOCUMENT vs. GENERAL)
        intent = self.classify_intent(prompt)

        # Usamos la instancia global que se inicializó en __init__
        global document_loader

        if intent == "DOCUMENT" and document_loader.get_document_count(document_loader.doc_store) > 0:
            # 2. Responder usando el módulo RAG nativo
            print("Intención: DOCUMENTO (Usando RAG Nativo)")
            return document_loader.qa_document_query(prompt)

        elif AGENT_ENABLED and self.agent and intent == "GENERAL":
            # 3. Responder usando el Agente (Si está habilitado)
            print("Intención: GENERAL (Usando Agente)")
            try:
                # El agente usa las herramientas definidas (Google Search)
                return self.agent.run(prompt)
            except Exception as e:
                return f"Error en la ejecución del Agente. Usando chat simple: {e}"
        else:
            # 4. Respuesta simple (sin Agente/RAG)
            print("Intención: GENERAL (Usando Chat Simple)")
            
            # Usamos el chat nativo simple como fallback
            try:
                response = self.client.models.generate_content(
                    model=self.llm_model,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                # Este error generalmente significa que la clave API es incorrecta
                if "API_KEY" in str(e):
                    return "Error: La clave GEMINI_API_KEY no es válida. Revisa tu config.json."
                return f"Error inesperado de la IA o del Chat: {e}"
            
    # Mantenemos la función classify_intent
    def classify_intent(self, prompt: str) -> str:
        """Clasifica si la pregunta necesita el documento o conocimiento general."""
        global document_loader
        if document_loader.get_document_count(document_loader.doc_store) == 0:
            return "GENERAL"
            
        doc_store = document_loader.doc_store
        
        classification_prompt = f"""
        INSTRUCCIONES CLASIFICACIÓN: Eres un clasificador de intención. Tu objetivo es decidir si la pregunta del usuario debe ser respondida usando el **DOCUMENTO CARGADO** o usando el **CONOCIMIENTO GENERAL/BÚSQUEDA WEB**.

        Si la pregunta es sobre el contenido del documento, responde DOCUMENT.
        Si la pregunta es sobre el clima, noticias, o un tema que requiere buscar en la web o conocimiento general, responde GENERAL.
        
        Pregunta del usuario: "{prompt}"
        
        RESPUESTA (DOCUMENT o GENERAL):
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=classification_prompt
            )
            intent = response.text.strip().upper()
            if intent in ["DOCUMENT", "GENERAL"]:
                return intent
            return "GENERAL" # Fallback
            
        except Exception as e:
            print(f"Error en el clasificador de intención, usando GENERAL: {e}")
            return "GENERAL"