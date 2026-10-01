"""
Tamil Text-to-Speech (TTS) Service for Sakhi (சகி).
Uses gTTS (Google Text-to-Speech) with in-memory caching for low-latency Tamil voice synthesis.
Guarantees spoken Tamil audio on all devices even if the client browser has no Tamil voice pack.
"""

import io
import re
import hashlib
from typing import Dict
from gtts import gTTS

# Memory cache for synthesized audio to eliminate repeated latency
AUDIO_CACHE: Dict[str, bytes] = {}
MAX_CACHE_ENTRIES = 100


def clean_text_for_speech(text: str) -> str:
    """Strip markdown, special characters, and emojis for smooth Tamil speech."""
    # Remove markdown headers, bold, italics, links
    cleaned = re.sub(r'#+\s*', '', text)
    cleaned = re.sub(r'\*+', '', cleaned)
    cleaned = re.sub(r'`+', '', cleaned)
    cleaned = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cleaned)
    # Remove non-text symbols like bullets, emojis
    cleaned = re.sub(r'[•\-—_~*#|✓✅❌🌾🪪🏦⚡📍📌💡⚙️🔊🎙️✍️❓🏛️🌸👩‍🌾]', ' ', cleaned)
    # Remove multiple spaces/newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def generate_tamil_audio(text: str, slow: bool = False) -> bytes:
    """
    Generate MP3 audio bytes for Tamil text.
    Uses in-memory cache to ensure instant response on repeated prompts.
    """
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        cleaned = "வணக்கம் அக்கா, நான் சகி."

    # Cache key based on text and speed
    cache_key = hashlib.sha256(f"{cleaned}_{slow}".encode('utf-8')).hexdigest()
    if cache_key in AUDIO_CACHE:
        return AUDIO_CACHE[cache_key]

    # Generate MP3 stream
    fp = io.BytesIO()
    tts = gTTS(text=cleaned, lang='ta', slow=slow)
    tts.write_to_fp(fp)
    audio_bytes = fp.getvalue()

    # Manage cache size
    if len(AUDIO_CACHE) >= MAX_CACHE_ENTRIES:
        # Evict oldest entry
        AUDIO_CACHE.pop(next(iter(AUDIO_CACHE)))

    AUDIO_CACHE[cache_key] = audio_bytes
    return audio_bytes
