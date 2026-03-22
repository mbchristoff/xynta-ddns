# xynta-ddns

DDNS service for Xynta DNS

## Overview

`xynta-ddns` is a lightweight dynamic DNS update service built with [FastAPI](https://fastapi.tiangolo.com/). It runs in a Docker container and exposes a single HTTP endpoint that DDNS clients can POST to. When the client's current IP address differs from the DNS record stored at Xynta, the service updates the record automatically via the [Xynta HostFact API](https://help.xynta.com/en/article/api-documentation-domains-module-s1808y/).

---

## Container image

Pre-built images are published to the GitHub Container Registry on every push:

```
ghcr.io/mbchristoff/xynta-ddns:latest   # latest build from main
ghcr.io/mbchristoff/xynta-ddns:main     # current main branch build
ghcr.io/mbchristoff/xynta-ddns:<branch> # sanitized branch-name build
```

Pull the latest image:

```bash
docker pull ghcr.io/mbchristoff/xynta-ddns:latest
```

---

## Quick start

### 1. Copy and fill in the environment file

```bash
cp .env.example .env
```

Edit `.env` and set:

| Variable | Description |
|---|---|
| `DDNS_XYNTA_API_USER_ID` | Your Xynta HostFact UserID |
| `DDNS_XYNTA_API_IP_HASH` | The IP-hash (API key) from your Xynta account |
| `DDNS_XYNTA_API_URL` | *(optional)* Xynta API base URL (default: `https://api.xynta.com/`) |
| `DDNS_CONFIG_FILE` | *(optional)* Path to the clients config file inside the container (default: `/app/config.yml`) |
| `DDNS_VERBOSE` | *(optional)* Log Xynta API payloads and responses at DEBUG level (default: `false`) |
| `DDNS_UVICORN_HOST` | *(optional)* Host address for uvicorn to bind to (default: `0.0.0.0`) |
| `DDNS_UVICORN_PORT` | *(optional)* Port for uvicorn to listen on (default: `8000`) |
| `DDNS_UVICORN_FORWARDED_ALLOW_IPS` | *(optional)* IPs/CIDRs trusted to set `X-Forwarded-For` (default: `*` — trust all; restrict to your reverse proxy IP in production) |

### 2. Create the client config

```bash
cp config.example.yml config.yml
```

Edit `config.yml` to define which DDNS clients are allowed and which DNS records each may update:

```yaml
clients:
  - token: "your-secret-token"
    records:
      - domain: "example"
        tld: "nl"
        name: "@"
```

> [!WARNING]
> `config.yml` and `.env` are excluded from git by default to prevent secrets from leaking. **Never commit them.**

### 3. Start the service

```bash
docker compose up -d
```

The service listens on port **80**.

---

## API

### `POST /update`

Updates DNS records if the caller's IP has changed.

**Request body** (`application/json`):

```json
{
  "api_token": "your-secret-token",
  "records": [
    { "domain": "example", "tld": "nl", "name": "@" }
  ]
}
```

**Responses**:

| Response | Meaning |
|---|---|
| `{"status": "unauthorized"}` | Unknown token or no permitted records in the request |
| `{"status": "error", "message": "No matching record(s) found on Xynta: ..."}` | Requested record(s) do not exist in the DNS zone |
| `{"status": "unchanged"}` | Client IP matches all requested A/AAAA records |
| `{"status": "updated"}` | Records were updated successfully |
| `{"status": "error", "message": "..."}` | Xynta API error |

**IP resolution order**: `X-Forwarded-For` (first hop) → `X-Real-IP` → direct connection IP.

---

## Development

Install dependencies (includes test requirements):

```bash
pip install -r requirements-test.txt
```

Run the app locally (requires `.env` with credentials):

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest tests/ -v
```

