# AGENTS.md

## Project: GymOps

A Python CLI/TUI workout tracker built as a DevOps portfolio project for Piero Rivera.

## Stack
- Python 3.12, Typer, Rich, Textual
- SQLite for local data storage (`~/.gymops/gymops.db`)
- Docker + docker-compose for containerization
- GitHub Actions for CI/CD
- Terraform for Azure infrastructure provisioning
- Azure Container Registry + Azure Container Apps for deployment

## Key files
- `gymops/cli.py` — all Typer commands
- `gymops/db.py` — all database logic and SQLite queries
- `gymops/models.py` — dataclasses: Workout, Exercise, PR, Routine, RoutineExercise
- `gymops/report.py` — CI Workout Digest generator

## Conventions
- All functions must have docstrings
- All new commands must have a corresponding pytest test
- flake8 must pass before any commit
- Never hardcode credentials — use environment variables
- Use `uv` for all Python environment and package management
- Database path always resolved via `get_db_path()` in `db.py`

## Current phase
Phase 1 — Scaffolding complete (feat/cli-scaffold-db). Next: implement tests on test/cli-pytest.
