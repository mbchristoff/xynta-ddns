from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DDNS_", env_file=".env", extra="ignore")

    # Xynta HostFact API settings
    xynta_api_url: str = "https://api.xynta.com/"
    xynta_api_key: str

    # Path to the DDNS clients config file
    config_file: str = "/app/config.yml"


settings = Settings()
