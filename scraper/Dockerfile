FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Install Camoufox (Firefox-based, patches fingerprints at the binary level)
RUN playwright install-deps firefox && python -m camoufox fetch

COPY . scraper/

# Data directory for SQLite DB
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8230

CMD ["python", "-m", "scraper.app"]
