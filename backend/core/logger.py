from loguru import logger
import sys
from .config import get_settings

settings = get_settings()

logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> - {message}"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)