from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from typing import Optional, Type, Tuple, Dict, Any
import json
import os

class Settings(BaseSettings):
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str
    LLM_MODEL: str = "gpt-4o"
    LLM_BASE_URL: Optional[str] = None
    
    # WhatsApp Config (Selenium/Node)
    WHATSAPP_TYPE: str = "selenium" # or "cloud_api" or "node_bridge"
    WHATSAPP_ALLOWED_NUMBERS: Optional[list[str]] = None # Pulse numbers allowed to interact
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    GIPHY_API_KEY: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None
    WHATSAPP_SESSION_ID: str = "whatsapp" # Dedicated session for WhatsApp interactions
    CHROME_PATH: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    CHROME_USER_DATA_DIR: str = os.path.abspath("./whatsapp_session")
    CHROME_DEBUG_PORT: int = 9222

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    class Config:
        env_file = ".env"

class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source that reads from a JSON file.
    """
    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        file_content = self._read_file()
        field_value = file_content.get(field_name)
        return field_value, field_name, False

    def _read_file(self) -> Dict[str, Any]:
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def __call__(self) -> Dict[str, Any]:
        data = self._read_file()
        # Convert comma-separated string to list if it comes from env or JSON is a string
        if isinstance(data.get("WHATSAPP_ALLOWED_NUMBERS"), str):
            data["WHATSAPP_ALLOWED_NUMBERS"] = [n.strip() for n in data["WHATSAPP_ALLOWED_NUMBERS"].split(",") if n.strip()]
        return data

settings = Settings()
