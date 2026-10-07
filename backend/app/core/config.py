from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "gbinsureapi"
    db_user: str = "gbinsure"
    db_password: str = "gbinsure_pass"
    jwt_secret: str = "change_me_jwt_secret"
    api_key_secret: str = "demo-api-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
