from __future__ import annotations

from typing import Any

import httpx

from .settings import settings


class XyntaClientError(Exception):
    """Raised when the Xynta API returns an error or an unexpected response."""


class XyntaClient:
    """Thin async client for the Xynta HostFact Domains API."""

    def __init__(self) -> None:
        self._api_url = settings.xynta_api_url.rstrip("/") + "/"
        self._user_id = settings.xynta_api_user_id
        self._ip_hash = settings.xynta_api_ip_hash

    def _base_payload(self) -> dict[str, Any]:
        return {"api_key": self._ip_hash, "UserID": self._user_id, "module": "domains"}

    async def show_dns_zone(self, domain: str, tld: str) -> list[dict[str, Any]]:
        """Return the current list of DNS records for *domain*.*tld*."""
        payload = {
            **self._base_payload(),
            "action": "show-dns-zone",
            "Domain": domain,
            "Tld": tld,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._api_url, json=payload)
            response.raise_for_status()

        data = response.json()
        if data.get("status") != "success":
            raise XyntaClientError(
                f"show-dns-zone failed: {data.get('message', data.get('status'))}"
            )
        return data["data"].get("Records", [])

    async def edit_dns_zone(
        self, domain: str, tld: str, records: list[dict[str, Any]]
    ) -> None:
        """Replace the DNS zone for *domain*.*tld* with *records*."""
        payload = {
            **self._base_payload(),
            "action": "edit-dns-zone",
            "Domain": domain,
            "Tld": tld,
            "Records": records,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._api_url, json=payload)
            response.raise_for_status()

        data = response.json()
        if data.get("status") != "success":
            raise XyntaClientError(
                f"edit-dns-zone failed: {data.get('message', data.get('status'))}"
            )
