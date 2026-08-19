from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parents[1]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(BASE_DIR) / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    API_KEY: str
    s3_user: str
    s3_password: str
    s3_access_key: str
    s3_secret_key: str
    s3_endpoint: str
    s3_base_domain: str
    s3_bucket: str = "vinyl"

    BASE_DIR: Path = BASE_DIR
    WEB_DIR: Path = BASE_DIR / "web"
    WEBSITE_DIR: Path = WEB_DIR / "website"
    URL: str = "http://ws.audioscrobbler.com/2.0/"
    MONGO_URI: str = "mongodb://localhost:27017"
    # Срок сессии: TTL в Mongo по login_time и Max-Age cookie.
    SESSION_TTL_SEC: int = 14 * 24 * 60 * 60

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    # За HTTPS-прокси: включить COOKIE_SECURE и разрешить прокси присылать X-Forwarded-*.
    # Схему запроса брать из заголовков нельзя, пока прокси не в списке доверенных.
    COOKIE_SECURE: bool = False
    FORWARDED_ALLOW_IPS: str = "127.0.0.1"
    ENABLE_DOCS: bool = False

    SEARCH_CACHE_TTL_SEC: int = 300

    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = BASE_DIR / "__logs"
    LOG_ROTATION: str = "5 MB"
    LOG_RETENTION: str = "14 days"



cfg = Config()

if __name__ == "__main__":
    for k, v in cfg.__dict__.items():
        print(f"{k}={v}")
