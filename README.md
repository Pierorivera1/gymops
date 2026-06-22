# GymOps — Python CLI/TUI Workout Tracker

A DevOps portfolio project demonstrating containerization, CI/CD, Infrastructure as Code, and Azure deployment.

## Stack
- Python 3.12 + Typer + Rich + Textual
- SQLite (local persistence at `~/.gymops/gymops.db`)
- Docker + docker-compose
- GitHub Actions (CI/CD)
- Terraform + Azure Container Registry + Azure Container Apps

## Quickstart
```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install in editable mode
uv pip install -e .

# Run the CLI
gymops --help
```

## Current Phase
Phase 1 — Python CLI App (scaffolding in progress)
