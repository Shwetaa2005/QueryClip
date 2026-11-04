import os
import re
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig


def extract_video_id(url: str) -> str:
    """
    Validates the domain using urllib.parse and extracts the 11-character YouTube video ID.
    """
    if not url or not isinstance(url, str) or not url.strip():
        raise ValueError("Please enter a valid YouTube video URL.")

    url_str = url.strip()

    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    parsed = urlparse(url_str)
    hostname = parsed.hostname.lower() if parsed.hostname else ""

    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be"
    }

    if hostname not in allowed_hosts:
        raise ValueError(
            "Invalid domain. URL must be a valid YouTube host "
            "(e.g., youtube.com or youtu.be)."
        )

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
        raise ValueError(
            "Could not extract a valid 11-character YouTube video ID."
        )

    return video_id


def fetch_raw_transcript(url: str) -> list:
    video_id = extract_video_id(url)

    ws_user = os.getenv("WEBSHARE_USER")
    ws_pass = os.getenv("WEBSHARE_PASS")

    try:
        if ws_user and ws_pass:
            proxy_config = WebshareProxyConfig(
                proxy_username=ws_user,
                proxy_password=ws_pass
            )
            api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            api = YouTubeTranscriptApi()

        raw_transcript = api.fetch(video_id)

        if not raw_transcript:
            raise ValueError("Transcript track was empty for this video.")

        return raw_transcript

    except ValueError:
        raise

    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch YouTube transcript: {str(e)}"
        )


def chunk_transcript(
    raw_transcript: list,
    video_id: str,
    chunk_size: int = 150,
    overlap: int = 30
) -> list[dict]:

    """
    Creates approximately 150-word chunks with sliding-window overlap.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be between 0 and chunk_size - 1."
        )

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

        chunk_tuples = word_stream[i:i + chunk_size]

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


def fetch_and_process_video(
    url: str,
    chunk_size: int = 150,
    overlap: int = 30
) -> list[dict]:

    video_id = extract_video_id(url)

    raw_transcript = fetch_raw_transcript(url)

    chunks = chunk_transcript(
        raw_transcript,
        video_id,
        chunk_size=chunk_size,
        overlap=overlap
    )

    return chunks