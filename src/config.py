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
    WEBSITE_DIR: Path = BASE_DIR / "website"
    # HTML профилей генерируются на диск и отдаются с сервера (не CDN): сессия /me, частые пересборки.
    USERS_DIR: Path = WEBSITE_DIR / "data" / "users"
    URL: str = "http://ws.audioscrobbler.com/2.0/"




cfg = Config()

if __name__ == "__main__":
    for k, v in cfg.__dict__.items():
        print(f"{k}={v}")
