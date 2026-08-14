FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY fpg-core /opt/fpg-core
COPY fpg-server/requirements.txt /tmp/fpg-server-requirements.txt
RUN pip install --no-cache-dir /opt/fpg-core \
    && pip install --no-cache-dir -r /tmp/fpg-server-requirements.txt

COPY fpg-server /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--timeout-keep-alive", "120", \
     "--timeout-graceful-shutdown", "10"]
