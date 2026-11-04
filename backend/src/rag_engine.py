import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is missing in backend/.env.")

client = genai.Client(api_key=api_key)

# Updated active Gemini models
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

def format_timestamp_link(video_id: str, seconds: int) -> str:
    minutes = seconds // 60
    secs = seconds % 60
    url = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
    timestamp_text = f"{minutes:02d}:{secs:02d}"
    return f"[{timestamp_text}]({url})"


def call_gemini(prompt: str, system_instruction: str) -> str:
    """
    Calls Gemini model with AFC disabled to eliminate SDK warnings,
    and handles automatic retries and fallback models cleanly.
    """
    last_error = None
    
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                        # Disable AFC to prevent SDK warnings on generate_content
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )
                )

                if response and response.text and response.text.strip():
                    return response.text.strip()

                last_error = Exception("Received empty response from Gemini API.")
                time.sleep(1)

            except errors.ServerError as e:
                last_error = e
                if attempt < 2:
                    time.sleep(2 ** attempt)

            except errors.ClientError as e:
                # E.g. Quota exhausted or invalid key: log error and move to next model
                last_error = e
                print(f"ClientError with {model}: {e}")
                break

            except Exception as net_err:
                last_error = net_err
                if attempt < 2:
                    time.sleep(1)

    raise RuntimeError(f"Gemini API generation failed across all models. Cause: {last_error}")


def generate_rag_response(query: str, context_chunks: list[dict], video_id: str) -> str:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")
        
    if not context_chunks:
        return "I couldn't find any relevant transcript snippets to answer your question."

    context_text = ""
    for chunk in context_chunks:
        link = format_timestamp_link(video_id, chunk["start_time"])
        context_text += f"\nTimestamp {link}: {chunk['text']}\n"

    system_instruction = (
        "You are QueryClip, an AI assistant answering questions about a YouTube video.\n"
        "Use ONLY the provided transcript snippets to answer the question.\n\n"
        "Rules:\n"
        "1. Every time you state a fact from the video, you MUST include the EXACT Markdown timestamp link provided in the context snippets.\n"
        "2. DO NOT write plain text timestamps like [00:00] or [05:34].\n"
        "3. ALWAYS copy the EXACT markdown link format: [MM:SS](https://www.youtube.com/watch?v=...&t=Xs).\n"
        "4. If the answer cannot be found in the context, state: 'I couldn't find information about this in the video.'"
    )

    prompt = f"Context Snippets:\n{context_text}\n\nUser Question: {query.strip()}"

    return call_gemini(prompt, system_instruction)