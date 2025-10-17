.PHONY: help install test lint format run docker-build docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make run          - Run FastAPI server"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker compose services"
	@echo "  make docker-down  - Stop Docker compose services"
	@echo "  make clean        - Clean cache and build files"

install:
	pip install -r requirements.txt

test:
	pytest -v

lint:
	@echo "Running linters..."
	ruff check src/ tests/

format:
	@echo "Formatting code..."
	ruff format src/ tests/

run:
	python src/app.py

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/

