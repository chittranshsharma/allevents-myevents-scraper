from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./eventpass.db'
    admin_token: str = ''
    frontend_origin: str = 'http://localhost:3000'
    source_config: str = ''
    allevents_authorized: bool = False
    schedule_minutes: int = 0
    request_interval_seconds: float = 3
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''
    telegram_enabled: bool = False
    app_env: str = 'local'


settings = Settings()
