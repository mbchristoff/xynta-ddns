"""Tests for the Xynta DDNS API."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Set required env vars before importing the app
os.environ.setdefault("DDNS_XYNTA_API_USER_ID", "test-user-id")
os.environ.setdefault("DDNS_XYNTA_API_IP_HASH", "test-ip-hash")
os.environ.setdefault("DDNS_XYNTA_API_URL", "https://api.xynta.example/")


SAMPLE_CONFIG = textwrap.dedent(
    """\
    clients:
      - token: "valid-token-1"
        records:
          - domain: "example"
            tld: "nl"
            name: "@"
      - token: "valid-token-2"
        records:
          - domain: "mysite"
            tld: "com"
            name: "home"
    """
)

EXISTING_RECORDS: list[dict[str, Any]] = [
    {"name": "@", "type": "A", "value": "1.2.3.4", "ttl": 3600},
    {"name": "www", "type": "CNAME", "value": "example.nl.", "ttl": 3600},
]


@pytest.fixture()
def config_file(tmp_path: Path) -> str:
    p = tmp_path / "config.yml"
    p.write_text(SAMPLE_CONFIG)
    return str(p)


@pytest.fixture()
def client(config_file: str):
    """Return a TestClient with config loaded from the temp file."""
    import app.main as main_module

    # Reload settings-dependent modules to pick up any env changes
    with patch("app.settings.settings.config_file", config_file):
        from app.config import load_config
        main_module._config = load_config(config_file)
        with TestClient(main_module.app) as c:
            yield c


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_invalid_token_returns_unauthorized(client):
    resp = client.post("/update", json={"api_token": "bad-token", "records": []})
    assert resp.status_code == 401
    assert resp.json()["status"] == "unauthorized"


def test_no_authorized_records_returns_unauthorized(client):
    """Token is valid but the requested record is not in the allowed list."""
    resp = client.post(
        "/update",
        json={
            "api_token": "valid-token-1",
            "records": [{"domain": "other", "tld": "nl", "name": "@"}],
        },
    )
    assert resp.status_code == 403
    assert resp.json()["status"] == "unauthorized"


# ---------------------------------------------------------------------------
# Unchanged
# ---------------------------------------------------------------------------

def test_same_ip_returns_unchanged(client):
    with patch("app.main.XyntaClient") as MockXynta:
        instance = MockXynta.return_value
        instance.show_dns_zone = AsyncMock(return_value=EXISTING_RECORDS)

        resp = client.post(
            "/update",
            json={
                "api_token": "valid-token-1",
                "records": [{"domain": "example", "tld": "nl", "name": "@"}],
            },
            headers={"x-forwarded-for": "1.2.3.4"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "unchanged"
    instance.edit_dns_zone.assert_not_called()


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_different_ip_triggers_update(client):
    with patch("app.main.XyntaClient") as MockXynta:
        instance = MockXynta.return_value
        instance.show_dns_zone = AsyncMock(return_value=EXISTING_RECORDS)
        instance.edit_dns_zone = AsyncMock()

        resp = client.post(
            "/update",
            json={
                "api_token": "valid-token-1",
                "records": [{"domain": "example", "tld": "nl", "name": "@"}],
            },
            headers={"x-real-ip": "9.8.7.6"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"
    instance.edit_dns_zone.assert_called_once()
    # The updated records should contain the new IP
    updated = instance.edit_dns_zone.call_args[0][2]
    a_record = next(r for r in updated if r["name"] == "@" and r["type"] == "A")
    assert a_record["value"] == "9.8.7.6"
    # Other records should be unchanged
    cname = next(r for r in updated if r["type"] == "CNAME")
    assert cname["value"] == "example.nl."


# ---------------------------------------------------------------------------
# IP detection
# ---------------------------------------------------------------------------

def test_x_forwarded_for_takes_first_ip(client):
    with patch("app.main.XyntaClient") as MockXynta:
        instance = MockXynta.return_value
        instance.show_dns_zone = AsyncMock(
            return_value=[{"name": "@", "type": "A", "value": "5.5.5.5", "ttl": 3600}]
        )
        instance.edit_dns_zone = AsyncMock()

        resp = client.post(
            "/update",
            json={
                "api_token": "valid-token-1",
                "records": [{"domain": "example", "tld": "nl", "name": "@"}],
            },
            headers={"x-forwarded-for": "10.0.0.1, 172.16.0.1"},
        )

    assert resp.status_code == 200
    updated = instance.edit_dns_zone.call_args[0][2]
    assert updated[0]["value"] == "10.0.0.1"


# ---------------------------------------------------------------------------
# Unmatched record
# ---------------------------------------------------------------------------

def test_unmatched_record_returns_400(client):
    """Requested record name not present in Xynta zone → 400 error."""
    with patch("app.main.XyntaClient") as MockXynta:
        instance = MockXynta.return_value
        instance.show_dns_zone = AsyncMock(
            return_value=[{"name": "www", "type": "A", "value": "1.2.3.4", "ttl": 3600}]
        )

        resp = client.post(
            "/update",
            json={
                "api_token": "valid-token-1",
                "records": [{"domain": "example", "tld": "nl", "name": "@"}],
            },
            headers={"x-forwarded-for": "1.2.3.4"},
        )

    assert resp.status_code == 400
    body = resp.json()
    assert body["status"] == "error"
    assert "example.nl" in body["message"]
    instance.edit_dns_zone.assert_not_called()
