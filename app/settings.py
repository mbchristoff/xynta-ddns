from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DDNS_", env_file=".env", extra="ignore")

    # Xynta HostFact API settings
    xynta_api_url: str = "https://api.xynta.com/"
    xynta_api_user_id: str = "User_ID"
    xynta_api_ip_hash: str = "IP_Hash_as_created_in_portal"

    # Path to the DDNS clients config file
    config_file: str = "/app/config.yml"


settings = Settings()
