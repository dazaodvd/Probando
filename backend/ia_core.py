from google import genai
from config import Config
from document_loader import DocumentLoader, RAG_ENABLED
import os

# Imports de LangChain para agentes (opcional)
AGENT_ENABLED = False
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.agents import initialize_agent, AgentType, Tool
    from langchain_community.tools import GoogleSearchAPIWrapper
    
    AGENT_ENABLED = True
    print("✅ Módulo Agente (LangChain) activado con éxito.")
except ImportError as e:
    print(f"❌ ADVERTENCIA: Agente deshabilitado. Fallo en la importación de LangChain: {e}")
except Exception as e:
    print(f"❌ ADVERTENCIA: Agente deshabilitado debido a error crítico: {e}")


class IACore:
    """Core del asistente de IA"""
    
    def __init__(self):
        # Inicialización del cliente de Gemini
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        
        # Modelo LLM
        self.llm_model = Config.AI_MODEL
        
        # Inicialización del Document Loader (RAG)
        self.document_loader = None
        if RAG_ENABLED:
            try:
                self.document_loader = DocumentLoader(gemini_client=self.client)
                print("✅ Document Loader inicializado correctamente.")
            except Exception as e:
                print(f"❌ Error al inicializar Document Loader: {e}")
        
        # Inicialización del agente (opcional)
        self.agent = None
        self.tools = []
        
        if AGENT_ENABLED:
            try:
                # LLM para el agente
                self.llm_agent = ChatGoogleGenerativeAI(
                    model=self.llm_model,
                    temperature=0,
                    client=self.client
                )
                
                # Herramienta de búsqueda Google (si están configuradas las claves)
                if Config.GOOGLE_CSE_ID and Config.GOOGLE_API_KEY:
                    search = GoogleSearchAPIWrapper(
                        google_api_key=Config.GOOGLE_API_KEY,
                        google_cse_id=Config.GOOGLE_CSE_ID
                    )
                    self.tools.append(
                        Tool(
                            name="Búsqueda_Web_Google",
                            description="Útil para responder preguntas sobre eventos actuales o información general.",
                            func=search.run
                        )
                    )
                    print("✅ Herramienta de Búsqueda Web activada.")
                
                # Inicializar agente
                if self.tools:
                    self.agent = initialize_agent(
                        self.tools,
                        self.llm_agent,
                        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                        verbose=False,
                        handle_parsing_errors=True
                    )
            except Exception as e:
                print(f"❌ ADVERTENCIA: Agente deshabilitado debido a error: {e}")
                self.agent = None
        
        print("✅ Módulo de IA Core inicializado.")
    
    def chat(self, prompt: str, session_id: str = "default") -> str:
        """Determina la intención y delega la respuesta"""
        
        # Clasificar intención
        intent = self.classify_intent(prompt)
        
        # Responder según intención
        if intent == "DOCUMENT" and self.document_loader and self.document_loader.get_document_count() > 0:
            print("Intención: DOCUMENTO (Usando RAG Nativo)")
            return self.document_loader.qa_document_query(prompt)
        
        elif AGENT_ENABLED and self.agent and intent == "GENERAL":
            print("Intención: GENERAL (Usando Agente)")
            try:
                return self.agent.run(prompt)
            except Exception as e:
                print(f"Error en agente: {e}")
                return self._simple_chat(prompt)
        else:
            print("Intención: GENERAL (Usando Chat Simple)")
            return self._simple_chat(prompt)
    
    def _simple_chat(self, prompt: str) -> str:
        """Chat simple sin agente ni RAG"""
        try:
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "API_KEY" in str(e) or "API key" in str(e):
                return "Error: La clave GEMINI_API_KEY no es válida. Revisa tu configuración."
            return f"Error inesperado de la IA: {e}"
    
    def classify_intent(self, prompt: str) -> str:
        """Clasifica si la pregunta necesita el documento o conocimiento general"""
        if not self.document_loader or self.document_loader.get_document_count() == 0:
            return "GENERAL"
        
        classification_prompt = f"""
        INSTRUCCIONES CLASIFICACIÓN: Eres un clasificador de intención. Tu objetivo es decidir si la pregunta del usuario debe ser respondida usando el **DOCUMENTO CARGADO** o usando el **CONOCIMIENTO GENERAL/BÚSQUEDA WEB**.

        Si la pregunta es sobre el contenido del documento, responde DOCUMENT.
        Si la pregunta es sobre el clima, noticias, o un tema que requiere buscar en la web o conocimiento general, responde GENERAL.
        
        Pregunta del usuario: "{prompt}"
        
        RESPUESTA (DOCUMENT o GENERAL):
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=classification_prompt
            )
            intent = response.text.strip().upper()
            if intent in ["DOCUMENT", "GENERAL"]:
                return intent
            return "GENERAL"
        except Exception as e:
            print(f"Error en el clasificador de intención: {e}")
            return "GENERAL"
    
    def update_config(self, assistant_name: str = None, api_key: str = None, model: str = None) -> dict:
        """Actualiza la configuración del asistente"""
        result = {"success": False, "message": ""}
        
        try:
            if api_key:
                # Validar la clave intentando hacer una llamada simple
                test_client = genai.Client(api_key=api_key)
                test_response = test_client.models.generate_content(
                    model=model or Config.AI_MODEL,
                    contents="Hola"
                )
                
                # Si llegamos aquí, la clave es válida
                Config.GEMINI_API_KEY = api_key
                self.client = test_client
                
                if model:
                    Config.AI_MODEL = model
                    self.llm_model = model
                
                # Reinicializar document loader con el nuevo cliente
                if RAG_ENABLED:
                    self.document_loader = DocumentLoader(gemini_client=self.client)
                
                result["success"] = True
                result["message"] = "Configuración actualizada correctamente."
            
            if assistant_name:
                Config.ASSISTANT_NAME = assistant_name
                result["success"] = True
                result["message"] = "Nombre del asistente actualizado."
            
        except Exception as e:
            result["success"] = False
            result["message"] = f"Error al actualizar configuración: {e}"
        
        return result
