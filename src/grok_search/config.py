import os
from pathlib import Path


class Config:
    _instance = None
    _DEFAULT_MODEL = "grok-4-fast"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def debug_enabled(self) -> bool:
        return os.getenv("GROK_DEBUG", "false").lower() in ("true", "1", "yes")

    @property
    def retry_max_attempts(self) -> int:
        return int(os.getenv("GROK_RETRY_MAX_ATTEMPTS", "3"))

    @property
    def retry_multiplier(self) -> float:
        return float(os.getenv("GROK_RETRY_MULTIPLIER", "1"))

    @property
    def retry_max_wait(self) -> int:
        return int(os.getenv("GROK_RETRY_MAX_WAIT", "10"))

    @property
    def grok_api_url(self) -> str:
        url = os.getenv("GROK_API_URL")
        if not url:
            raise ValueError("GROK_API_URL is not set")
        return url

    @property
    def grok_api_key(self) -> str:
        key = os.getenv("GROK_API_KEY")
        if not key:
            raise ValueError("GROK_API_KEY is not set")
        return key

    @property
    def grok_model(self) -> str:
        return os.getenv("GROK_MODEL", self._DEFAULT_MODEL)

    @property
    def api_key(self) -> str | None:
        """API key for authenticating requests to this service. None = no auth."""
        return os.getenv("API_KEY") or None

    @property
    def api_host(self) -> str:
        return os.getenv("API_HOST", "0.0.0.0")

    @property
    def api_port(self) -> int:
        return int(os.getenv("API_PORT", "8000"))

    @property
    def log_level(self) -> str:
        return os.getenv("GROK_LOG_LEVEL", "INFO").upper()

    @property
    def log_dir(self) -> Path:
        log_dir_str = os.getenv("GROK_LOG_DIR", "logs")
        log_dir = Path(log_dir_str)
        if log_dir.is_absolute():
            return log_dir

        home_log_dir = Path.home() / ".config" / "grok-search" / log_dir_str
        try:
            home_log_dir.mkdir(parents=True, exist_ok=True)
            return home_log_dir
        except OSError:
            pass

        cwd_log_dir = Path.cwd() / log_dir_str
        try:
            cwd_log_dir.mkdir(parents=True, exist_ok=True)
            return cwd_log_dir
        except OSError:
            pass

        tmp_log_dir = Path("/tmp") / "grok-search" / log_dir_str
        tmp_log_dir.mkdir(parents=True, exist_ok=True)
        return tmp_log_dir

    @staticmethod
    def mask_api_key(key: str) -> str:
        if not key or len(key) <= 8:
            return "***"
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


config = Config()
