import os
import time
from .config import Config
from typing import TYPE_CHECKING, List, Any

# --- Imports para RAG (Usando Google GenAI y componentes estables) ---
from google import genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter # Este splitter no tiene el conflicto de la versión classic
from chromadb.api.models.Collection import Collection

# Definición de rutas de persistencia
DB_PATH = "./db"
DOCS_COLLECTION = "documents"
MEMORY_COLLECTION = "conversation_memory"

# RAG estará siempre activado si las librerías se instalaron
RAG_ENABLED = True
print("✅ Módulo RAG (Aprendizaje Local) activado con éxito (RAG Nativo).")

# Crear los directorios de persistencia si no existen
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)


class DocumentLoader:
    def __init__(self, gemini_client: genai.Client):
        # El cliente nativo de Gemini es inyectado desde ia_core
        self.client = gemini_client 
        
        # El modelo de incrustación (Embeddings). Usamos la clase de LangChain,
        # que es estable y no está en conflicto, y le inyectamos el cliente nativo.
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="text-embedding-004", 
            client=self.client 
        )
        
        # Inicializa ChromaDB (el vector store)
        self.doc_store = Chroma(
            collection_name=DOCS_COLLECTION,
            embedding_function=self.embeddings,
            persist_directory=DB_PATH
        )
        
        # Inicializa el splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
    
    # --- Funciones de Utilidad ---
    
    def get_document_count(self, doc_store: Chroma) -> int:
        """Obtiene el número de documentos cargados en el almacén vectorial."""
        try:
            return doc_store._collection.count()
        except Exception:
            return 0
            
    def load_document(self, file_path: str) -> str:
        """Carga y procesa un documento, persistiendo sus embeddings."""
        try:
            if file_path.lower().endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith('.txt'):
                loader = TextLoader(file_path)
            else:
                return "Formato de archivo no soportado. Por favor, usa .pdf o .txt."

            docs = loader.load()
            
            # 1. División del texto (Splitting)
            texts = self.text_splitter.split_documents(docs)
            
            # 2. Persistencia en ChromaDB (Indexing)
            self.doc_store.add_documents(texts)
            
            # 3. Forzar la persistencia en disco
            self.doc_store.persist()
            
            return f"✅ Documento '{os.path.basename(file_path)}' cargado y listo para consultas."
            
        except Exception as e:
            return f"❌ Error al cargar el documento: {e}"

    # --- Función Central RAG (Reescrita a Nativo) ---
    def qa_document_query(self, question: str) -> str:
        """
        Utiliza el almacén vectorial cargado para responder preguntas mediante RAG Nativo (sin RetrievalQA).
        """
        if not RAG_ENABLED: 
            return "Error interno: El módulo RAG está deshabilitado."
            
        if self.get_document_count(self.doc_store) == 0:
            return "No se ha cargado ningún documento. Por favor, carga un archivo primero."

        # 1. RECUPERACIÓN (RETRIEVAL): Buscar documentos relevantes en ChromaDB
        #    Buscar los 4 fragmentos más relevantes.
        retriever = self.doc_store.as_retriever(search_kwargs={"k": 4})
        retrieved_docs = retriever.invoke(question)
        
        # 2. CONTEXT STUFFING: Construir el contexto a partir de los documentos
        context = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
        
        # 3. INSTRUCCIÓN DEL SISTEMA (System Prompt)
        system_instruction = (
            "Eres un experto extractor de información de documentos. "
            "Tu única función es responder a la pregunta del usuario utilizando **ÚNICAMENTE** el contexto de documento proporcionado. "
            "Si la pregunta solicita una acción (ej: 'ejecuta', 'abre', 'haz', 'realiza'), debes **describir las instrucciones** encontradas, pero **NUNCA realizar la acción**. "
            "Si la respuesta o descripción no se encuentra en el contexto, debes responder: 'Según el documento cargado, no puedo encontrar esa información.'"
        )

        # 4. CONSTRUCCIÓN DEL PROMPT FINAL
        prompt_final = f"""
        {system_instruction}

        CONTEXTO DEL DOCUMENTO:
        ---
        {context}
        ---

        PREGUNTA DEL USUARIO: "{question}"
        """

        # 5. LLAMADA NATIVA A GEMINI (LLM Call)
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_final
            )
            return response.text
        except Exception as e:
            return f"Error al generar la respuesta RAG: {e}"

# Inicialización temporal, la instancia final se crea en ia_core
document_loader = None 

# Asegura que los directorios existan
def create_directories():
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)

create_directories()