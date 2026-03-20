from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Config, load_config
from .models import UpdateRequest, UpdateResponse
from .settings import settings
from .xynta_client import XyntaClient, XyntaClientError

logger = logging.getLogger(__name__)

_config: Config | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config
    _config = load_config(settings.config_file)
    logger.info("Loaded config from %s", settings.config_file)
    yield


app = FastAPI(title="Xynta DDNS", lifespan=lifespan)


def _get_client_ip(request: Request) -> str:
    """Determine the real client IP address from request headers or connection info."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # x-forwarded-for may contain a comma-separated list; take the first (leftmost)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host


@app.post("/update", response_model=UpdateResponse)
async def update(request: Request, body: UpdateRequest) -> JSONResponse:
    assert _config is not None, "Config not loaded"

    client = _config.get_client(body.api_token)
    if client is None:
        return JSONResponse(
            status_code=401,
            content=UpdateResponse(status="unauthorized").model_dump(exclude_none=True),
        )

    client_ip = _get_client_ip(request)
    allowed_keys = {
        (r.domain, r.tld, r.name) for r in client.records
    }

    # Only process records the token is authorized to edit
    records_to_process = [
        r for r in body.records
        if (r.domain, r.tld, r.name) in allowed_keys
    ]

    if not records_to_process:
        return JSONResponse(
            status_code=403,
            content=UpdateResponse(
                status="unauthorized",
                message="No authorized records in request",
            ).model_dump(exclude_none=True),
        )

    xynta = XyntaClient()
    all_unchanged = True
    errors: list[str] = []

    # Group records by (domain, tld) to minimize API calls
    zones: dict[tuple[str, str], list[str]] = {}
    for rec in records_to_process:
        key = (rec.domain, rec.tld)
        zones.setdefault(key, []).append(rec.name)

    for (domain, tld), names in zones.items():
        try:
            current_records: list[dict[str, Any]] = await xynta.show_dns_zone(domain, tld)
        except XyntaClientError as exc:
            errors.append(str(exc))
            continue

        # Check if each client-requested record matches a record from Xynta
        unmatched = []
        for r in records_to_process:
            if r.domain == domain and r.tld == tld:
                found = any(
                    rec.get("name") == r.name
                    for rec in current_records
                )
                if not found:
                    if r.name:
                        unmatched.append(f"{r.name}.{r.domain}.{r.tld}")
                    else:
                        unmatched.append(f"{r.domain}.{r.tld}")

        if unmatched:
            return JSONResponse(
                status_code=400,
                content=UpdateResponse(
                    status="error",
                    message=f"No matching record(s) found on Xynta: {', '.join(unmatched)}",
                ).model_dump(exclude_none=True),
            )

        # Check whether any A/AAAA record for the requested names differs
        needs_update = False
        for rec in current_records:
            if rec.get("name") in names and rec.get("type") in ("A", "AAAA"):
                if rec.get("value") != client_ip:
                    needs_update = True
                    break

        if not needs_update:
            continue

        all_unchanged = False

        # Build updated record list: replace A/AAAA values for the requested names
        updated_records = []
        for rec in current_records:
            if rec["name"] in names and rec["type"] in ("A", "AAAA"):
                rec["value"] = client_ip
            updated_records.append(rec)

        try:
            await xynta.edit_dns_zone(domain, tld, updated_records)
        except XyntaClientError as exc:
            errors.append(str(exc))

    if errors:
        return JSONResponse(
            status_code=503,
            content=UpdateResponse(
                status="error",
                message="; ".join(errors),
            ).model_dump(exclude_none=True),
        )

    if all_unchanged:
        return JSONResponse(
            content=UpdateResponse(status="unchanged").model_dump(exclude_none=True)
        )

    return JSONResponse(
        content=UpdateResponse(status="updated").model_dump(exclude_none=True)
    )
