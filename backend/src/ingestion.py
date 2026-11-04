import os
import re
from urllib.parse import urlparse, parse_qs
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str:
    """
    Validates domain and extracts the 11-character YouTube video ID.
    """
    if not url or not isinstance(url, str) or not url.strip():
        raise ValueError("Please enter a valid YouTube video URL.")
        
    url_str = url.strip()
    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    parsed = urlparse(url_str)
    hostname = parsed.hostname.lower() if parsed.hostname else ""

    allowed_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
    if hostname not in allowed_hosts:
        raise ValueError("Invalid domain. URL must be a valid YouTube host (e.g., youtube.com or youtu.be).")

    video_id = None
    if hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif "/shorts/" in parsed.path:
        video_id = parsed.path.split("/shorts/")[1].split("/")[0]
    elif "/embed/" in parsed.path:
        video_id = parsed.path.split("/embed/")[1].split("/")[0]
    elif "/v/" in parsed.path:
        video_id = parsed.path.split("/v/")[1].split("/")[0]
    else:
        query_params = parse_qs(parsed.query)
        if "v" in query_params and query_params["v"]:
            video_id = query_params["v"][0]

    if not video_id or not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id):
        raise ValueError("Could not extract a valid 11-character YouTube video ID.")

    return video_id


def fetch_raw_transcript(url: str) -> list[dict]:
    """
    Fetches raw transcript captions using pytubefix with client rotation and fallback to youtube_transcript_api.
    """
    video_id = extract_video_id(url)
    errors_list = []

    # Attempt 1: pytubefix with default WEB client
    try:
        yt = YouTube(url, client='WEB')
        if yt.captions:
            caption_track = (
                yt.captions.get('en') or 
                yt.captions.get('a.en') or 
                list(yt.captions.values())[0]
            )
            events = caption_track.json_captions.get("events", [])
            raw_transcript = []
            for event in events:
                if "segs" not in event:
                    continue
                text = "".join([seg.get("utf8", "") for seg in event["segs"]]).strip()
                if not text or text == "\n":
                    continue
                raw_transcript.append({
                    "text": text,
                    "start": event.get("tStartMs", 0) / 1000.0,
                    "duration": event.get("dDurationMs", 0) / 1000.0
                })
            if raw_transcript:
                return raw_transcript
    except Exception as e:
        errors_list.append(f"pytubefix WEB: {str(e)}")

    # Attempt 2: pytubefix with ANDROID client fallback
    try:
        yt = YouTube(url, client='ANDROID')
        if yt.captions:
            caption_track = (
                yt.captions.get('en') or 
                yt.captions.get('a.en') or 
                list(yt.captions.values())[0]
            )
            events = caption_track.json_captions.get("events", [])
            raw_transcript = []
            for event in events:
                if "segs" not in event:
                    continue
                text = "".join([seg.get("utf8", "") for seg in event["segs"]]).strip()
                if not text or text == "\n":
                    continue
                raw_transcript.append({
                    "text": text,
                    "start": event.get("tStartMs", 0) / 1000.0,
                    "duration": event.get("dDurationMs", 0) / 1000.0
                })
            if raw_transcript:
                return raw_transcript
    except Exception as e:
        errors_list.append(f"pytubefix ANDROID: {str(e)}")

    # Attempt 3: youtube_transcript_api fallback
    try:
        api = YouTubeTranscriptApi()
        raw_transcript = api.fetch(video_id)
        if raw_transcript:
            return raw_transcript
    except Exception as e:
        errors_list.append(f"youtube_transcript_api: {str(e)}")

    raise RuntimeError(f"Could not fetch transcript across attempts. Errors: {' | '.join(errors_list)}")


def chunk_transcript(raw_transcript: list, video_id: str, chunk_size: int = 150, overlap: int = 30) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1.")

    if not raw_transcript:
        return []

    def get_val(item, key, default):
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    word_stream = []
    for item in raw_transcript:
        text = get_val(item, "text", "")
        start_time = int(get_val(item, "start", 0))
        if not text:
            continue
        for word in text.split():
            word_stream.append((word, start_time))

    if not word_stream:
        return []

    chunks = []
    i = 0
    total_words = len(word_stream)

    while i < total_words:
        chunk_tuples = word_stream[i : i + chunk_size]
        chunk_words = [t[0] for t in chunk_tuples]
        chunk_start_time = chunk_tuples[0][1]

        chunks.append({
            "text": " ".join(chunk_words),
            "metadata": {
                "video_id": video_id,
                "start_time": chunk_start_time,
                "chunk_index": len(chunks)
            }
        })

        if i + chunk_size >= total_words:
            break

        i += (chunk_size - overlap)

    return chunks


def fetch_and_process_video(url: str, chunk_size: int = 150, overlap: int = 30) -> list[dict]:
    video_id = extract_video_id(url)
    raw_transcript = fetch_raw_transcript(url)
    chunks = chunk_transcript(raw_transcript, video_id, chunk_size=chunk_size, overlap=overlap)
    return chunks