import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8003"))
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./data/models")
    INFERENCE_BACKEND: str = os.getenv("INFERENCE_BACKEND", "numpy")  # numpy, openvino, onnx
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
