FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV DDNS_CONFIG_FILE=/app/config.yml

EXPOSE 8000

CMD ["python", "-m", "app"]
