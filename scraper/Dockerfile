FROM python:3.12-slim

# Install system deps for Playwright/Chromium
WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Install Playwright browsers and all required system dependencies
RUN playwright install-deps chromium && playwright install chromium

COPY . scraper/

# Data directory for SQLite DB
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8230

CMD ["python", "-m", "scraper.app"]
