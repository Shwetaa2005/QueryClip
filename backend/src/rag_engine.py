import os
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Google GenAI Client
# Automatically picks up GEMINI_API_KEY from environment variables
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def format_timestamp_link(video_id: str, seconds: int) -> str:
    """
    Converts raw seconds into a formatted MM:SS string with an embedded YouTube link.
    """
    minutes = seconds // 60
    secs = seconds % 60
    url = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
    timestamp_text = f"{minutes:02d}:{secs:02d}"
    return f"[{timestamp_text}]({url})"


def generate_rag_response(query: str, context_chunks: list[dict], video_id: str) -> str:
    """
    Formats retrieved chunks with timestamp links and sends a grounded prompt to Gemini.
    """
    # 1. Format each retrieved chunk with its clickable timestamp link
    context_text = ""
    for chunk in context_chunks:
        link = format_timestamp_link(video_id, chunk["start_time"])
        context_text += f"\n- Timestamp {link}: {chunk['text']}\n"

    # 2. Build the strict grounding prompt
    prompt = f"""
You are QueryClip, an AI assistant answering questions about a YouTube video.

Use ONLY the provided transcript snippets to answer the question. 

Rules:
1. Every time you state a fact from the video, you MUST include the EXACT Markdown timestamp link provided in the context snippets.
2. DO NOT write plain text timestamps like [00:00] or [05:34].
3. ALWAYS copy the EXACT markdown link format: [MM:SS](https://www.youtube.com/watch?v={video_id}&t=Xs).
4. If the answer cannot be found in the context, state: "I couldn't find information about this in the video."

Context Snippets:
{context_text}

User Question: {query}

Answer:
"""

    # 3. Call Gemini model using modern client syntax
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    return response.text


if __name__ == "__main__":
    from backend.src.ingestion import fetch_and_process_video, extract_video_id
    from backend.src.vector_store import VectorStoreManager

    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    v_id = extract_video_id(test_url)

    print("1. Ingesting video...")
    chunks = fetch_and_process_video(test_url)

    print("2. Storing in ChromaDB...")
    db_manager = VectorStoreManager()
    db_manager.add_chunks(chunks)

    print("3. Querying Vector DB...")
    question = "What is the commitment mentioned in the video?"
    retrieved = db_manager.query(question, video_id=v_id, top_k=2)

    print("4. Generating RAG Answer from Gemini...\n")
    answer = generate_rag_response(question, retrieved, v_id)
    
    print("=== FINAL RAG ANSWER ===")
    print(answer)