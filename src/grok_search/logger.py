import logging
from datetime import datetime
from .config import config

logger = logging.getLogger("grok_search")
logger.setLevel(getattr(logging, config.log_level, logging.INFO))

_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler
_console_handler = logging.StreamHandler()
_console_handler.setLevel(getattr(logging, config.log_level, logging.INFO))
_console_handler.setFormatter(_formatter)
logger.addHandler(_console_handler)

# File handler
try:
    log_dir = config.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"grok_search_{datetime.now().strftime('%Y%m%d')}.log"

    _file_handler = logging.FileHandler(log_file, encoding='utf-8')
    _file_handler.setLevel(getattr(logging, config.log_level, logging.INFO))
    _file_handler.setFormatter(_formatter)
    logger.addHandler(_file_handler)
except OSError:
    pass
