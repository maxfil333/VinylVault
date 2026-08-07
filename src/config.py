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
    # HTML профилей вне StaticFiles (/static), только через /me с сессией.
    USERS_DIR: Path = WEB_DIR / "protected" / "users"
    URL: str = "http://ws.audioscrobbler.com/2.0/"
    MONGO_URI: str = "mongodb://localhost:27017"



cfg = Config()

if __name__ == "__main__":
    for k, v in cfg.__dict__.items():
        print(f"{k}={v}")
