import re
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from src.ingestion import fetch_and_process_video, extract_video_id
from src.vector_store import VectorStoreManager
from src.rag_engine import generate_rag_response

app = FastAPI(title="QueryClip API", version="1.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_manager = VectorStoreManager()


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")

class QueryRequest(BaseModel):
    video_id: str = Field(..., description="11-character YouTube video ID")
    query: str = Field(..., description="User search query")

    @field_validator("video_id")
    @classmethod
    def validate_video_id(cls, v: str) -> str:
        v_clean = v.strip() if v else ""
        if not re.fullmatch(r"[a-zA-Z0-9_-]{11}", v_clean):
            raise ValueError("video_id must be a valid 11-character string.")
        return v_clean


@app.get("/")
def read_root():
    return {"status": "online", "message": "QueryClip API is live!"}


@app.post("/api/analyze")
def analyze_video(request: AnalyzeRequest):
    if not request.url or not request.url.strip():
        raise HTTPException(status_code=400, detail="Please enter a YouTube video URL.")

    try:
        video_id = extract_video_id(request.url)
        chunks = fetch_and_process_video(request.url)
        
        if not chunks:
            raise HTTPException(status_code=422, detail="No usable transcript content could be extracted from this video.")
            
        db_manager.add_chunks(chunks)
        
        return {
            "status": "success",
            "video_id": video_id,
            "chunks_count": len(chunks),
            "message": "Video processed and indexed successfully!"
        }
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=str(re))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/query")
def query_video(request: QueryRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Please type a question before submitting.")

    try:
        context_chunks = db_manager.query(request.query.strip(), video_id=request.video_id, top_k=3)
        
        if not context_chunks:
            return {"answer": "No relevant transcript context found for this video."}

        answer = generate_rag_response(request.query.strip(), context_chunks, request.video_id)
        return {"answer": answer}
        
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=str(re))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")