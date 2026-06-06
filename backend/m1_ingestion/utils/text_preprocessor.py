import re
import unicodedata
import httpx
from backend.core.logger import logger

# Headers to mimic a real browser — many news sites block plain requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_text(text: str) -> str:
    """Remove noise from raw news text."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"[^\w\s\.\,\!\?\-\']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer."""
    return clean_text(text).lower().split()


def detect_language(text: str) -> str:
    """Basic language detection — returns 'en' or 'other'."""
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    return "en" if ascii_ratio > 0.85 else "other"


def fetch_article_text(url: str, timeout: int = 15) -> str | None:
    """
    Fetch full article text from a URL.
    Returns cleaned text or None if the page is paywalled/unreachable.
    """
    try:
        with httpx.Client(timeout=timeout, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(url)

        if resp.status_code != 200:
            logger.debug(f"Article fetch {resp.status_code}: {url}")
            return None

        # Extract text from HTML — strip all tags
        html = resp.text
        # Remove script and style blocks
        html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html, flags=re.DOTALL)
        # Remove all HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Clean up
        text = clean_text(text)

        # Minimum length check — paywalled pages return very little text
        if len(text) < 200:
            logger.debug(f"Article too short (likely paywalled): {url}")
            return None

        # Cap at 2000 chars — enough for sentiment scoring
        return text[:2000]

    except Exception as e:
        logger.debug(f"Article fetch failed for {url}: {e}")
        return None


def preprocess(text: str) -> dict:
    """Full preprocessing pipeline for a single text."""
    cleaned = clean_text(text)
    tokens = tokenize(cleaned)
    lang = detect_language(text)

    return {
        "original_length": len(text),
        "cleaned": cleaned,
        "tokens": tokens,
        "token_count": len(tokens),
        "language": lang
    }