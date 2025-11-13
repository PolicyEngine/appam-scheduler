#!/bin/bash
# Quick start script for APPAM Conference Scheduler

set -e

echo "================================================"
echo " APPAM Conference Scheduler - Full Pipeline"
echo "================================================"
echo ""

echo "Step 1: Scraping conference data..."
uv run python scraper.py
echo ""

echo "Step 2: Scoring sessions..."
uv run python relevance_scorer.py
echo ""

echo "Step 3: Generating schedule..."
uv run python scheduler.py
echo ""

echo "Step 4: Exporting to JSON..."
uv run python export_to_json.py
echo ""

echo "================================================"
echo " Pipeline complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  - Run 'npm start' to view the web app"
echo "  - Run 'npm run build' to build for production"
echo "  - Run 'npm run deploy' to deploy to GitHub Pages"
echo ""
