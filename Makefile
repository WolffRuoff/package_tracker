.PHONY: setup install install-scraper test test-scraper test-all coverage lint build-card docker-build docker-run docker-stop

PYTHON_VERSION := 3.12

# Initial setup: install uv, Python, and all dependencies
setup:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv python install $(PYTHON_VERSION)
	$(MAKE) install
	$(MAKE) install-scraper
	@echo "Setup complete. Run 'make test-all' to verify."

# HA integration development
install:
	uv sync

test:
	uv run pytest tests/ -v

coverage:
	uv run pytest tests/ --cov --cov-report=term-missing

lint:
	uv run ruff check .

# Scraper development
install-scraper:
	cd scraper && uv sync

test-scraper:
	cd scraper && uv run pytest tests/ -v

# All tests
test-all: test test-scraper

# Frontend
build-card:
	cd frontend-src && npm install && npm run build

# Docker
docker-build:
	docker build -t package-tracker-scraper scraper/

docker-run:
	docker run -d --name package-tracker-scraper -p 8230:8230 -v package-tracker-data:/data package-tracker-scraper

docker-stop:
	docker stop package-tracker-scraper && docker rm package-tracker-scraper
