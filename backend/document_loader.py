import os
from typing import List, Any
from config import Config

# Imports para RAG
try:
    from google import genai
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_community.document_loaders import TextLoader, PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    RAG_ENABLED = True
    print("✅ Módulo RAG (Aprendizaje Local) activado con éxito")
except ImportError as e:
    RAG_ENABLED = False
    print(f"❌ ADVERTENCIA: RAG deshabilitado. Error de importación: {e}")


class DocumentLoader:
    """Maneja la carga y consulta de documentos usando RAG"""
    
    def __init__(self, gemini_client: genai.Client):
        if not RAG_ENABLED:
            raise Exception("RAG no está habilitado. Faltan dependencias.")
            
        self.client = gemini_client
        
        # Asegurar que existan los directorios
        Config.ensure_directories()
        
        # Inicializar embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            client=self.client
        )
        
        # Inicializar ChromaDB
        self.doc_store = Chroma(
            collection_name=Config.DOCS_COLLECTION,
            embedding_function=self.embeddings,
            persist_directory=Config.DB_PATH
        )
        
        # Inicializar text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def get_document_count(self) -> int:
        """Obtiene el número de documentos cargados"""
        try:
            return self.doc_store._collection.count()
        except Exception:
            return 0
    
    def load_document(self, file_path: str) -> str:
        """Carga y procesa un documento, persistiendo sus embeddings"""
        try:
            if file_path.lower().endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith('.txt'):
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                return "Formato de archivo no soportado. Por favor, usa .pdf o .txt."
            
            # Cargar y dividir el documento
            docs = loader.load()
            texts = self.text_splitter.split_documents(docs)
            
            # Agregar a ChromaDB
            self.doc_store.add_documents(texts)
            
            # Persistir
            if hasattr(self.doc_store, 'persist'):
                self.doc_store.persist()
            
            return f"✅ Documento '{os.path.basename(file_path)}' cargado y listo para consultas."
        
        except Exception as e:
            return f"❌ Error al cargar el documento: {e}"
    
    def qa_document_query(self, question: str) -> str:
        """Responde preguntas usando RAG nativo"""
        if self.get_document_count() == 0:
            return "No se ha cargado ningún documento. Por favor, carga un archivo primero."
        
        try:
            # Recuperación de documentos relevantes
            retriever = self.doc_store.as_retriever(search_kwargs={"k": 4})
            retrieved_docs = retriever.invoke(question)
            
            # Construir contexto
            context = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
            
            # System instruction
            system_instruction = (
                "Eres un experto extractor de información de documentos. "
                "Tu única función es responder a la pregunta del usuario utilizando **ÚNICAMENTE** el contexto de documento proporcionado. "
                "Si la pregunta solicita una acción (ej: 'ejecuta', 'abre', 'haz', 'realiza'), debes **describir las instrucciones** encontradas, pero **NUNCA realizar la acción**. "
                "Si la respuesta o descripción no se encuentra en el contexto, debes responder: 'Según el documento cargado, no puedo encontrar esa información.'"
            )
            
            # Prompt final
            prompt_final = f"""
            {system_instruction}

            CONTEXTO DEL DOCUMENTO:
            ---
            {context}
            ---

            PREGUNTA DEL USUARIO: "{question}"
            """
            
            # Llamada a Gemini
            response = self.client.models.generate_content(
                model=Config.AI_MODEL,
                contents=prompt_final
            )
            
            return response.text
        
        except Exception as e:
            return f"Error al generar la respuesta RAG: {e}"
    
    def clear_documents(self) -> str:
        """Elimina todos los documentos cargados"""
        try:
            # Eliminar todos los documentos de la colección
            self.doc_store.delete_collection()
            
            # Reinicializar la colección
            self.doc_store = Chroma(
                collection_name=Config.DOCS_COLLECTION,
                embedding_function=self.embeddings,
                persist_directory=Config.DB_PATH
            )
            
            return "✅ Todos los documentos han sido eliminados."
        except Exception as e:
            return f"❌ Error al eliminar documentos: {e}"
