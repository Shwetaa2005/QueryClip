from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ingestion import fetch_and_process_video, extract_video_id
from src.vector_store import VectorStoreManager
from src.rag_engine import generate_rag_response

# Initialize FastAPI application
app = FastAPI(title="QueryClip API", version="1.0")

# Enable CORS so React frontend can communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any frontend URL (e.g. React)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Vector Database Manager Instance
db_manager = VectorStoreManager()


# Pydantic models for strict JSON request bodies
class AnalyzeRequest(BaseModel):
    url: str

class QueryRequest(BaseModel):
    video_id: str
    query: str


@app.get("/")
def read_root():
    """Health check endpoint to verify API is running."""
    return {"message": "QueryClip API is live!"}


@app.post("/api/analyze")
def analyze_video(request: AnalyzeRequest):
    """
    Extracts transcript, creates time-aware chunks, and indexes them into ChromaDB.
    """
    try:
        video_id = extract_video_id(request.url)
        chunks = fetch_and_process_video(request.url)
        db_manager.add_chunks(chunks)
        
        return {
            "status": "success",
            "video_id": video_id,
            "chunks_count": len(chunks),
            "message": "Video processed and indexed successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/query")
def query_video(request: QueryRequest):
    """
    Queries vector store for context and generates grounded response via Gemini.
    """
    try:
        # Retrieve relevant context from ChromaDB
        context_chunks = db_manager.query(request.query, video_id=request.video_id, top_k=3)
        
        if not context_chunks:
            return {"answer": "No relevant transcript context found for this video."}

        # Generate grounded response using Gemini
        answer = generate_rag_response(request.query, context_chunks, request.video_id)
        return {"answer": answer}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))