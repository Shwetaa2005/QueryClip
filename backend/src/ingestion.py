import os
import re
from youtube_transcript_api import YouTubeTranscriptApi

#Extracts the 11 character video ID from various youtube link formats
def extract_video_id(url:str)->str:
    pattern = r"(?:v=|\/\|youtu\.be\/|\/embed\/|\/v\/|https:\/\/youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid YouTube URL")


#Extracts video_id from URL and fetches the raw transcript entries from YouTube.
def fetch_raw_transcript(url:str) -> list[dict]:
    video_id = extract_video_id(url)
    proxy_url = os.getenv("PROXY_URL")
    proxies = None
    if proxy_url:
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

    try:
        # Pass proxies dictionary if available
        if proxies:
            raw_transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
        else:
            raw_transcript = YouTubeTranscriptApi.get_transcript(video_id)

        return raw_transcript
    except Exception as e:
        raise Exception(f"Failed to fetch YouTube transcript: {str(e)}")


#Groups raw transcript items into ~300-word blocks while retaining start_time metadata.
def chunk_transcript(raw_transcript: list[dict], video_id: str, chunk_size: int = 300) -> list[dict]:
    chunks = []
    current_text = []
    current_word_count = 0
    start_time = 0.0

    for idx, item in enumerate(raw_transcript):
        text = item.text
        
        # If starting a brand new chunk, capture its start timestamp
        if current_word_count == 0:
            start_time = item.start

        words = text.split()
        current_text.append(text)
        current_word_count += len(words)

        # Check if we hit the chunk limit
        if current_word_count >= chunk_size:
            full_text = " ".join(current_text)
            chunks.append({
                "text": full_text,
                "metadata": {
                    "video_id": video_id,
                    "start_time": int(start_time)
                }
            })
            # Reset bucket for next chunk
            current_text = []
            current_word_count = 0

    # Add leftover words at the end of the video
    if current_text:
        full_text = " ".join(current_text)
        chunks.append({
            "text": full_text,
            "metadata": {
                "video_id": video_id,
                "start_time": int(start_time)
            }
        })

    return chunks

#Main function for Phase 2: Takes a YouTube URL and returns a list of processed chunks with metadata.
def fetch_and_process_video(url: str, chunk_size: int = 300) -> list[dict]:
    video_id = extract_video_id(url)
    raw_transcript = fetch_raw_transcript(url)
    chunks = chunk_transcript(raw_transcript, video_id, chunk_size)
    return chunks

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    processed_chunks = fetch_and_process_video(test_url)
    
    print(f"Total Chunks Created: {len(processed_chunks)}")
    print("\n--- FIRST CHUNK SAMPLE ---")
    print("Metadata:", processed_chunks[0]["metadata"])
    print("Text Sample:", processed_chunks[0]["text"][:150], "...")