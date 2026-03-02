import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEVOPS_MODE: str = os.getenv("DEVOPS_MODE", "demo")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8002"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def is_real_mode(self) -> bool:
        return self.DEVOPS_MODE == "real" and bool(self.ANTHROPIC_API_KEY)


config = Config()
