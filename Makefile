# Automata Workflows Makefile
# Provides convenient commands for development and deployment

.PHONY: help install dev test lint format clean worker workflow docker-build docker-up docker-down

# Default target
help:
	@echo "Automata Workflows - Available Commands:"
	@echo ""
	@echo "  install       - Install dependencies with uv"
	@echo "  dev           - Start development environment"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linting and type checking"
	@echo "  format        - Format code with black and isort"
	@echo "  clean         - Clean up cache files"
	@echo "  worker        - Start workflow workers"
	@echo "  workflow      - Run individual workflow"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-up     - Start services with Docker Compose"
	@echo "  docker-down   - Stop services with Docker Compose"
	@echo "  docker-logs   - Show Docker logs"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies with uv..."
	uv sync

# Development setup
dev: install
	@echo "🚀 Setting up development environment..."
	@echo "Starting Temporal with Podman Compose..."
	podman-compose up -d temporal
	@echo ""
	@echo "✅ Development environment ready!"
	@echo "Run 'make worker' to start workflow workers"

# Run tests
test:
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v --cov=shared --cov=workflows

# Lint and type check
lint:
	@echo "🔍 Running linting and type checking..."
	uv run ruff check .
	uv run mypy shared/ workflows/
	uv run black --check .
	uv run isort --check-only .

# Format code
format:
	@echo "✨ Formatting code..."
	uv run black .
	uv run isort .

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true

# Start workers
worker:
	@echo "🤖 Starting workflow workers..."
	uv run python scripts/run_workers.py --workflow all

# Start specific worker
worker-llm:
	@echo "🤖 Starting LLM inference worker..."
	uv run python scripts/run_workers.py --workflow llm_inference

# Run workflow
workflow:
	@echo "🔄 Running workflow..."
	@read -p "Enter workflow name (llm_inference): " workflow; \
	w=$${workflow:-llm_inference}; \
	read -p "Enter input JSON or file path: " input; \
	if [ -f "$$input" ]; then \
		uv run python scripts/run_workflow.py --workflow $$w --input-file "$$input"; \
	else \
		uv run python scripts/run_workflow.py --workflow $$w --input "$$input"; \
	fi

# Quick test with LLM
test-llm:
	@echo "🧪 Testing LLM inference..."
	uv run python scripts/run_workflow.py --workflow llm_inference --input-file examples/llm_test_input.json

# Database migration
migrate:
	@echo "🗄️ Running database migrations..."
	uv run python scripts/migrate_db.py

# Show configuration
config:
	@echo "⚙️ Current configuration:"
	uv run python -c "from shared.config import config; \
		print(f'Temporal Host: {config.TEMPORAL_HOST}'); \
		print(f'Temporal Namespace: {config.TEMPORAL_NAMESPACE}'); \
		print(f'Task Queue: {config.TEMPORAL_TASK_QUEUE}'); \
		print(f'Log Level: {config.LOG_LEVEL}');"

# Docker commands
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t automata-workflows:latest .

docker-up:
	@echo "🚀 Starting all services with Docker Compose..."
	docker-compose up -d
	@echo "✅ Services started. Use 'make docker-logs' to view logs."

docker-down:
	@echo "🛑 Stopping services..."
	docker-compose down
	@echo "✅ Services stopped."

docker-infrastructure:
	@echo "🏗️ Starting infrastructure services only..."
	docker-compose -f docker-compose.infrastructure.yml up -d
	@echo "✅ Infrastructure started. Use 'make docker-workers' to start workers."

docker-workers:
	@echo "👥 Starting worker services..."
	docker-compose -f docker-compose.infrastructure.yml -f docker-compose.workers.yml up -d
	@echo "✅ Workers started."

docker-logs:
	docker-compose logs -f

docker-logs-workers:
	docker-compose -f docker-compose.workers.yml logs -f

docker-status:
	@echo "📊 Service status:"
	docker-compose ps

# Quick development with Docker
docker-dev: docker-up
	@echo "⏳ Waiting for services to be ready..."
	sleep 10
	@echo "🌐 Access services:"
	@echo "  - Temporal Web UI: http://localhost:8233"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Jaeger: http://localhost:16686"

docker-clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete."
		print(f'OpenRouter Model: {config.OPENROUTER_MODEL}'); \
		print(f'API Key: {\"SET\" if config.OPENROUTER_API_KEY else \"NOT SET\"}'); \
		print(f'Database URL: {config.DATABASE_URL}'); \
		print(f'Log Level: {config.LOG_LEVEL}')"