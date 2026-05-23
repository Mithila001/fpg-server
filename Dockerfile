FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for any compiled packages (e.g., psycopg2, shapely)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 8000
EXPOSE 8000

# Production uvicorn settings:
# --timeout-keep-alive 120  keeps the TCP connection alive for 120 s between SSE events
# --timeout-graceful-shutdown 10  gives workers time to finish before forced kill
# --workers 1  CPU-bound workload: multiple workers would fight for the GIL / memory;
#              job isolation is handled by multiprocessing inside the app.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--timeout-keep-alive", "120", \
     "--timeout-graceful-shutdown", "10"]
