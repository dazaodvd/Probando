from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import shutil

# Import IA modules
try:
    from ia_core import IACore
    from config import Config
    IA_ENABLED = True
    # Initialize IA Core
    Config.ensure_directories()
    ai_core = IACore()
    print("✅ IA Core inicializado correctamente en el servidor")
except Exception as e:
    IA_ENABLED = False
    ai_core = None
    print(f"❌ Error al inicializar IA Core: {e}")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# IA Assistant Models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ConfigUpdate(BaseModel):
    assistant_name: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None

class ConfigResponse(BaseModel):
    assistant_name: str
    model: str
    theme: str
    has_api_key: bool
    document_count: int

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# ================================
# IA Assistant Routes
# ================================

@api_router.get("/assistant/config", response_model=ConfigResponse)
async def get_assistant_config():
    """Obtiene la configuración actual del asistente"""
    if not IA_ENABLED:
        raise HTTPException(status_code=503, detail="IA Core no está disponible")
    
    doc_count = 0
    if ai_core.document_loader:
        doc_count = ai_core.document_loader.get_document_count()
    
    return ConfigResponse(
        assistant_name=Config.ASSISTANT_NAME,
        model=Config.AI_MODEL,
        theme=Config.THEME,
        has_api_key=bool(Config.GEMINI_API_KEY),
        document_count=doc_count
    )

@api_router.post("/assistant/config")
async def update_assistant_config(config_update: ConfigUpdate):
    """Actualiza la configuración del asistente"""
    if not IA_ENABLED:
        raise HTTPException(status_code=503, detail="IA Core no está disponible")
    
    result = ai_core.update_config(
        assistant_name=config_update.assistant_name,
        api_key=config_update.api_key,
        model=config_update.model
    )
    
    if result["success"]:
        return JSONResponse(content=result)
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@api_router.post("/assistant/chat", response_model=ChatResponse)
async def chat_with_assistant(chat_msg: ChatMessage):
    """Envía un mensaje al asistente y obtiene una respuesta"""
    if not IA_ENABLED:
        raise HTTPException(status_code=503, detail="IA Core no está disponible")
    
    try:
        response = ai_core.chat(chat_msg.message, chat_msg.session_id)
        return ChatResponse(response=response, session_id=chat_msg.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el chat: {str(e)}")

@api_router.post("/assistant/document/upload")
async def upload_document(file: UploadFile = File(...)):
    """Carga un documento para el aprendizaje local (RAG)"""
    if not IA_ENABLED:
        raise HTTPException(status_code=503, detail="IA Core no está disponible")
    
    if not ai_core.document_loader:
        raise HTTPException(status_code=503, detail="Document Loader no está disponible")
    
    # Verificar formato
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos .pdf y .txt")
    
    try:
        # Guardar archivo temporalmente
        upload_dir = ROOT_DIR / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Cargar documento
        result = ai_core.document_loader.load_document(str(file_path))
        
        # Eliminar archivo temporal
        file_path.unlink()
        
        return JSONResponse(content={"message": result})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar documento: {str(e)}")

@api_router.delete("/assistant/document/clear")
async def clear_documents():
    """Elimina todos los documentos cargados"""
    if not IA_ENABLED:
        raise HTTPException(status_code=503, detail="IA Core no está disponible")
    
    if not ai_core.document_loader:
        raise HTTPException(status_code=503, detail="Document Loader no está disponible")
    
    try:
        result = ai_core.document_loader.clear_documents()
        return JSONResponse(content={"message": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar documentos: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()