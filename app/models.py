from __future__ import annotations

from pydantic import BaseModel


class RecordRequest(BaseModel):
    """A single DNS record the client wants to have checked/updated."""

    domain: str
    tld: str
    name: str


class UpdateRequest(BaseModel):
    """Payload sent by the DDNS client."""

    api_token: str
    records: list[RecordRequest]


class UpdateResponse(BaseModel):
    """Response returned to the DDNS client."""

    status: str
    message: str | None = None
