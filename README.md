#  QueryClip

**Time-aware YouTube video Q&A powered by Retrieval-Augmented Generation (RAG).**

Paste a YouTube link, ask questions about the video, and get answers grounded in the transcript, with clickable timestamps that jump straight to the relevant moment.

<img width="1917" height="907" alt="image" src="https://github.com/user-attachments/assets/5c2fbd0a-2638-46aa-99af-593513e6a868" />


---

##  Features

- **Transcript ingestion**: Fetches captions from any YouTube video that has them
- **Time-aware chunking**: Splits transcripts into ~300-word chunks while keeping each chunk's start time
- **Semantic search**: Embeds chunks with Sentence Transformers and stores them in ChromaDB
- **Grounded answers**: Gemini answers using only the retrieved transcript snippets
- **Clickable timestamps**: Every fact links back to the exact moment in the video
- **Resilient LLM calls**: Retries with exponential backoff and falls back to other models on 5xx errors
- **Clean chat UI**: React + Tailwind interface with an embedded video player

---

##  How It Works

```
YouTube URL
    │
    ▼
Extract video ID ──► Fetch transcript ──► Chunk (~300 words + start time)
                                                   │
                                                   ▼
                                    Embed (all-MiniLM-L6-v2) ──► ChromaDB
                                                                    │
User question ──► Embed ──► Similarity search (filtered by video) ◄─┘
                                    │
                                    ▼
                    Top-k chunks + timestamp links ──► Gemini ──► Answer
```

---

##  Tech Stack

| Layer      | Technology                                                  |
| ---------- | ----------------------------------------------------------- |
| Frontend   | React (Vite), Tailwind CSS, Axios, React Markdown           |
| Backend    | FastAPI, Uvicorn, Pydantic                                  |
| Vector DB  | ChromaDB (persistent, local)                                |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`)                  |
| LLM        | Google Gemini via the `google-genai` SDK                    |
| Ingestion  | `youtube-transcript-api`                                    |

---

##  Project Structure

```
QueryClip/
│
├── backend/                  # FastAPI backend
│   ├── .env                  # Environment variables (GEMINI_API_KEY)
│   ├── requirements.txt      # Python dependencies
│   ├── main.py               # API endpoints
│   └── src/
│       ├── __init__.py
│       ├── ingestion.py      # Transcript extraction & chunking
│       ├── vector_store.py   # ChromaDB management & similarity search
│       └── rag_engine.py     # Prompt building & Gemini integration
│
└── frontend/                 # React app (Vite)
    ├── package.json
    ├── tailwind.config.js
    └── src/
        ├── App.jsx           # Main UI & state management
        ├── index.css
        └── main.jsx
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/QueryClip.git
cd QueryClip
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```env
GEMINI_API_KEY=your_api_key_here
```

Start the server:

```bash
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive docs are available at `http://127.0.0.1:8000/docs`.

> The first run downloads the embedding model, so it may take a moment. ChromaDB data is stored in a `chroma_db/` folder in the directory you start the server from.

### 3. Frontend setup

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`).

---

##  API Reference

### `GET /`

Health check.

```json
{ "message": "QueryClip API is live!" }
```

### `POST /api/analyze`

Fetches the transcript, chunks it, and indexes it in ChromaDB.

**Request**

```json
{ "url": "https://www.youtube.com/watch?v=VIDEO_ID" }
```

**Response**

```json
{
  "status": "success",
  "video_id": "VIDEO_ID",
  "chunks_count": 12,
  "message": "Video processed and indexed successfully!"
}
```

### `POST /api/query`

Retrieves relevant chunks and returns a grounded answer.

**Request**

```json
{
  "video_id": "VIDEO_ID",
  "query": "What does the speaker say about pricing?"
}
```

**Response**

```json
{
  "answer": "The speaker explains the pricing model at [02:14](https://www.youtube.com/watch?v=VIDEO_ID&t=134s)..."
}
```

**Error responses**

| Status | Meaning                                                    |
| ------ | ---------------------------------------------------------- |
| `400`  | Invalid URL or transcript could not be fetched             |
| `503`  | The Gemini model is overloaded; try again shortly          |
| `500`  | Unexpected server error (check the backend terminal logs)  |

---

##  Configuration

| Setting            | Location                | Default                                  |
| ------------------ | ----------------------- | ---------------------------------------- |
| `GEMINI_API_KEY`   | `backend/.env`          | none (required)                          |
| Gemini model list  | `backend/src/rag_engine.py` (`MODELS`) | first entry is tried first, others are fallbacks |
| Chunk size         | `backend/src/ingestion.py`             | 300 words                                |
| Results retrieved  | `backend/main.py` (`top_k`)            | 3                                        |
| API base URL       | `frontend/src/App.jsx`                 | `http://127.0.0.1:8000`                  |

---

##  Testing Modules Individually

Each backend module has a `__main__` block for quick checks. Run them from the `backend/` folder:

```bash
python -m src.ingestion
python -m src.vector_store
python -m src.rag_engine
```

---

##  Known Limitations

- Only works for videos that have captions or auto-generated transcripts
- YouTube may rate-limit or block transcript requests from some IPs or cloud hosts
- Answers are limited to the top retrieved chunks, so broad "summarize everything" questions may be incomplete
- Gemini models can be temporarily overloaded (503); the app retries and falls back automatically

---


##  Contributing

Contributions are welcome. Fork the repo, create a feature branch, and open a pull request.

```bash
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

---

##  Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- [Google Gemini](https://ai.google.dev/)
