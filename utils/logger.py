from loguru import logger
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
)

logger.add(
    LOG_DIR / "career_os.log",
    rotation="5 MB",
    retention="10 days",
    level="DEBUG",
)

app_logger = logger
