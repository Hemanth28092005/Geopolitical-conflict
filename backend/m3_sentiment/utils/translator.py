from transformers import MarianMTModel, MarianTokenizer
from backend.core.logger import logger

# Cache loaded models to avoid reloading every call
_model_cache = {}

SUPPORTED_LANG_PAIRS = {
    "fr": "Helsinki-NLP/opus-mt-fr-en",
    "de": "Helsinki-NLP/opus-mt-de-en",
    "ar": "Helsinki-NLP/opus-mt-ar-en",
    "ru": "Helsinki-NLP/opus-mt-ru-en",
    "zh": "Helsinki-NLP/opus-mt-zh-en",
    "hi": "Helsinki-NLP/opus-mt-hi-en",
}


def translate_to_english(text: str, src_lang: str) -> str:
    """
    Translate text to English using Helsinki-NLP MarianMT.
    Falls back to original text if language not supported.
    """
    if src_lang == "en" or src_lang not in SUPPORTED_LANG_PAIRS:
        return text

    model_name = SUPPORTED_LANG_PAIRS[src_lang]

    if model_name not in _model_cache:
        logger.info(f"Loading translation model: {model_name}")
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        _model_cache[model_name] = (tokenizer, model)

    tokenizer, model = _model_cache[model_name]

    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )
    translated = model.generate(**inputs)
    result = tokenizer.decode(translated[0], skip_special_tokens=True)
    return result