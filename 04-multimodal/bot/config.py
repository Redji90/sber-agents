"""Configuration management."""
import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)
        
        # Telegram
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or self._config["telegram"]["bot_token"]
        
        # LLM
        self.llm_provider = os.getenv("LLM_PROVIDER") or self._config["llm"]["provider"]
        self.llm_model = os.getenv("LLM_MODEL") or self._config["llm"]["model"]
        self.llm_api_key = os.getenv("LLM_API_KEY") or self._config["llm"]["api_key"]
        self.llm_base_url = os.getenv("LLM_BASE_URL") or self._config["llm"].get("base_url")
        
        # VLM
        self.vlm_provider = os.getenv("VLM_PROVIDER") or self._config["vlm"]["provider"]
        self.vlm_model = os.getenv("VLM_MODEL") or self._config["vlm"]["model"]
        self.vlm_api_key = os.getenv("VLM_API_KEY") or self._config["vlm"]["api_key"]
        self.vlm_base_url = os.getenv("VLM_BASE_URL") or self._config["vlm"].get("base_url")
        
        # Speech/Transcription
        self.speech_provider = os.getenv("SPEECH_PROVIDER") or self._config.get("speech", {}).get("provider", "openai")
        self.speech_api_key = os.getenv("SPEECH_API_KEY") or self._config.get("speech", {}).get("api_key", "")
        self.speech_base_url = os.getenv("SPEECH_BASE_URL") or self._config.get("speech", {}).get("base_url", "")
        # Примечание: folder_id не используется при запросах через сервисный аккаунт
        # SpeechKit автоматически использует каталог сервисного аккаунта
        self.speech_folder_id = os.getenv("SPEECH_FOLDER_ID") or self._config.get("speech", {}).get("folder_id", "")
        self.speech_language = os.getenv("SPEECH_LANGUAGE") or self._config.get("speech", {}).get("language", "ru")
        # Vosk model path (для локального распознавания)
        self.speech_model_path = os.getenv("SPEECH_MODEL_PATH") or self._config.get("speech", {}).get("model_path", "")
        
        # Storage
        self.storage_type = os.getenv("STORAGE_TYPE") or self._config["storage"]["type"]
        self.storage_path = os.getenv("STORAGE_PATH") or self._config["storage"]["path"]
        
        # Ensure data directory exists
        if self.storage_type == "json":
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)


config = Config()

