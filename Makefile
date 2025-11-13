.PHONY: install test format scrape score schedule export build deploy clean

# Install Python and Node dependencies
install:
	uv pip install -e ".[dev]"
	uv run playwright install
	npm ci

# Run all tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-coverage:
	uv run pytest tests/ --cov=. --cov-report=html --cov-report=term

# Format code (placeholder - add formatters if needed)
format:
	@echo "No formatters configured yet"

# Scrape conference data
scrape:
	uv run python scraper.py

# Score sessions
score:
	uv run python relevance_scorer.py

# Generate schedule
schedule:
	uv run python scheduler.py

# Export database to JSON
export:
	uv run python export_to_json.py

# Full pipeline: scrape, score, schedule, export
pipeline: scrape score schedule export

# Build React app
build:
	npm run build

# Run development server
debug:
	npm start

# Deploy to GitHub Pages
deploy:
	npm run deploy

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf node_modules/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf *.egg-info/
	rm -f *.db
	rm -f *.db-*
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
