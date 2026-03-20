import uvicorn

from .settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.uvicorn_host,
        port=settings.uvicorn_port,
        proxy_headers=True,
        forwarded_allow_ips=settings.uvicorn_forwarded_allow_ips,
    )
