
from typing import Any
import json
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
        return {
            "uid": self._user_id,
            "hash": self._ip_hash,
            "m": "domains",
        }

    async def show_dns_zone(self, domain: str, tld: str) -> list[dict[str, Any]]:
        """Return the current list of DNS records for *domain*.*tld*."""
        payload = {
            **self._base_payload(),
            "a": "show-dns-zone",
            "t": None,
            "test": None,
            "Domain": domain,
            "Tld": tld,
        }
        form_payload = {k: '' if v is None else str(v) for k, v in payload.items()}
        async with httpx.AsyncClient() as client:
            response = await client.post(self._api_url, data=form_payload)
            response.raise_for_status()

        data = response.json()
        try:
            records = data['0']['results'][0]['dns_zone']['records']
        except Exception:
            raise XyntaClientError(f"show-dns-zone failed: {data}")
        return records

    async def edit_dns_zone(
        self, domain: str, tld: str, records: list[dict[str, Any]]
    ) -> None:
        """Replace the DNS zone for *domain*.*tld* with *records*."""
        dns_zone_obj = {"records": records}
        payload = {
            **self._base_payload(),
            "a": "edit-dns-zone",
            "t": None,
            "test": None,
            "Domain": domain,
            "Tld": tld,
            "DNSZone": json.dumps(dns_zone_obj) if records else '',
        }
        form_payload = {k: '' if v is None else str(v) for k, v in payload.items()}
        print(payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(self._api_url, data=form_payload)
            response.raise_for_status()

        data = response.json()
        print(json.dumps(data, indent=2))
        # Check for success in the response, similar to show_dns_zone
        try:
            status = data['0']['status']
        except Exception:
            raise XyntaClientError(f"edit-dns-zone failed: {data}")
        if status != 'success':
            raise XyntaClientError(f"edit-dns-zone failed: {data}")
