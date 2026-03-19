from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class AllowedRecord(BaseModel):
    """A single DNS record the client is allowed to update."""

    domain: str
    tld: str
    name: str


class ClientConfig(BaseModel):
    """A DDNS client identified by an API token."""

    token: str
    records: list[AllowedRecord]


class Config(BaseModel):
    """Top-level config loaded from the YAML config file."""

    clients: list[ClientConfig]

    def get_client(self, token: str) -> ClientConfig | None:
        """Return the client matching the given token, or None if not found."""
        for client in self.clients:
            if client.token == token:
                return client
        return None


def load_config(path: str) -> Config:
    """Load and validate the YAML config file from *path*."""
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    return Config.model_validate(data)
