from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from typing import Optional, Type, Tuple, Dict, Any
import json
import os
import platform

def get_default_work_dir() -> str:
    """Get default work directory based on OS."""
    system = platform.system()
    if system == "Windows":
        return r"C:\liteclaw"
    else:
        return os.path.expanduser("~/liteclaw")

class Settings(BaseSettings):
    # Work Directory - where LiteClaw stores files, screenshots, configs
    WORK_DIR: str = get_default_work_dir()
    
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""  # Allow empty during onboarding
    LLM_MODEL: str = "gpt-4o"
    LLM_BASE_URL: Optional[str] = None
    
    # Vision LLM (for Vision Agent) - Falls back to Main LLM if not set
    VISION_LLM_PROVIDER: Optional[str] = None
    VISION_LLM_MODEL: Optional[str] = None
    VISION_LLM_API_KEY: Optional[str] = None
    VISION_LLM_BASE_URL: Optional[str] = None
    
    # WhatsApp Config (Selenium/Node)
    WHATSAPP_TYPE: str = "selenium" # or "cloud_api" or "node_bridge"
    WHATSAPP_ALLOWED_NUMBERS: Optional[list[str]] = None # Pulse numbers allowed to interact
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ALLOWED_IDS: Optional[list[str]] = None # Whitelisted Telegram Chat IDs
    GIPHY_API_KEY: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    WHATSAPP_SESSION_ID: str = "whatsapp" # Dedicated session for WhatsApp interactions
    
    # Break Time (Timestamp until when the agent is resting)
    BREAK_UNTIL: float = 0
    
    # Chrome Path
    CHROME_PATH: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    @property
    def CHROME_USER_DATA_DIR(self) -> str:
        """Store browser sessions in the centralized work directory."""
        return os.path.join(self.WORK_DIR, "sessions", "browser")
    
    CHROME_DEBUG_PORT: int = 9222
    
    def get_screenshots_dir(self) -> str:
        """Get the screenshots directory path."""
        return os.path.join(self.WORK_DIR, "screenshots")
    
    def get_configs_dir(self) -> str:
        """Get the configs directory path."""
        return os.path.join(self.WORK_DIR, "configs")
    
    def get_notes_dir(self) -> str:
        """Get the notes directory path."""
        return os.path.join(self.WORK_DIR, "notes")
    
    def get_exports_dir(self) -> str:
        """Get the exports directory path."""
        return os.path.join(self.WORK_DIR, "exports")
    
    def get_agent_instructions_path(self) -> str:
        """Get the path to AGENT.md in the configs directory."""
        return os.path.join(self.get_configs_dir(), "AGENT.md")
    
    def ensure_work_dirs(self) -> None:
        """Create work directory and subdirectories if they don't exist."""
        dirs = [
            self.WORK_DIR,
            self.get_screenshots_dir(),
            self.get_configs_dir(), 
            self.get_notes_dir(),
            self.get_exports_dir(),
            os.path.join(self.WORK_DIR, "sessions")
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

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
    Checks local directory first, then default WORK_DIR.
    """
    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        file_content = self._read_file()
        field_value = file_content.get(field_name)
        return field_value, field_name, False

    def _read_file(self) -> Dict[str, Any]:
        config_file = "config.json"
        
        # 1. Try Local Directory
        if os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception:
                pass
        
        # 2. Try Default WORK_DIR
        default_work_dir = get_default_work_dir()
        work_dir_config = os.path.join(default_work_dir, config_file)
        if os.path.exists(work_dir_config):
            try:
                with open(work_dir_config) as f:
                    return json.load(f)
            except Exception:
                pass
                
        return {}

    def __call__(self) -> Dict[str, Any]:
        data = self._read_file()
        # Convert comma-separated string to list if it comes from env or JSON is a string
        if isinstance(data.get("WHATSAPP_ALLOWED_NUMBERS"), str):
            data["WHATSAPP_ALLOWED_NUMBERS"] = [n.strip() for n in data["WHATSAPP_ALLOWED_NUMBERS"].split(",") if n.strip()]
        return data

settings = Settings()
settings.ensure_work_dirs()
