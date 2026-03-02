import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8004"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    FEATURE_STORE_TYPE: str = os.getenv("FEATURE_STORE_TYPE", "memory")  # memory or redis


config = Config()
