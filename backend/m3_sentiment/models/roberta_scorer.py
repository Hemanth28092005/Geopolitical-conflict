from transformers import pipeline
from backend.core.logger import logger

_classifier = None


def get_classifier():
    """Lazy-load RoBERTa classifier — loads once, reuses across calls."""
    global _classifier
    if _classifier is None:
        logger.info("Loading RoBERTa sentiment model...")
        _classifier = pipeline(
            "text-classification",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            max_length=512,
            truncation=True
        )
        logger.info("RoBERTa model loaded")
    return _classifier


def score_text(text: str) -> dict:
    """
    Score a single text for sentiment.
    Returns hostility score 0–100 and raw label.

    Label mapping:
      negative → high hostility (maps to 60–100)
      neutral  → medium         (maps to 40–60)
      positive → low hostility  (maps to 0–40)
    """
    if not text or len(text.strip()) < 20:
        return {"hostility": 50.0, "label": "neutral", "confidence": 0.0}

    try:
        classifier = get_classifier()
        result = classifier(text[:512])[0]

        label      = result["label"].lower()
        confidence = result["score"]  # 0.0 to 1.0

        # Map sentiment label → hostility score
        if "negative" in label:
            # negative + high confidence = high hostility
            hostility = 60 + (confidence * 40)
        elif "positive" in label:
            # positive + high confidence = low hostility
            hostility = 40 - (confidence * 40)
        else:
            # neutral
            hostility = 50.0

        return {
            "hostility": round(hostility, 2),
            "label": label,
            "confidence": round(confidence, 4)
        }

    except Exception as e:
        logger.warning(f"RoBERTa scoring failed: {e}")
        return {"hostility": 50.0, "label": "error", "confidence": 0.0}


def score_batch(texts: list[str]) -> list[dict]:
    """Score a batch of texts — more efficient than calling one by one."""
    return [score_text(t) for t in texts]