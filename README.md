# lazygym (GymOps) 🏋️

> A terminal-based workout tracker I built for myself because I was tired of tracking my sets in my notes app.

lazygym (GymOps) is a CLI tool that lives in your terminal. You set your training split, pick today's day, and log your sets. It tracks your personal records, tells you if you're actually getting stronger, and generates a weekly summary of what you've been doing. That's it.

Inspired by [lazygit](https://github.com/jesseduffield/lazygit) — the idea that a good terminal tool should get out of your way, run locally, and just work.

---

## Features

- **100% Local**: Your data never leaves your machine. Saved in a SQLite database at `~/.gymops/gymops.db`.
- **Pre-loaded Splits**: Comes pre-seeded with Jeff Nippard's classic splits (4-Day Upper/Lower, 5-Day ULPPL, 6-Day PPL) so you can start logging immediately.
- **Estimated 1RM**: Calculates estimated 1-rep max using the Epley formula after every set.
- **Progressive Overload Stats**: Compares today's performance against your last session to tell you if you're getting stronger.
- **PR Tracking**: Auto-updates your personal records and marks them when broken.
- **Weekly Digests**: Generates markdown summaries of your weekly training volume and best lifts.
- **TUI Interface (Coming Soon)**: A full lazygit-style terminal UI to log sets and view PRs visually.

---

## Quickstart

```bash
# Clone the repository
git clone https://github.com/Pierorivera1/gymops.git
cd gymops

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .

# Confirm it works
gymops --help
```

> **Requires**: Python 3.12+ and [uv](https://github.com/astral-sh/uv)

---

## Usage

```bash
# 1. List all available training programs
gymops list-programs

# 2. Select the active program you follow (e.g. Upper/Lower)
gymops select-program "Upper/Lower (4-Day)"

# 3. Set today's training day (do this at the start of your workout)
gymops set-day "Upper A (Strength)"

# 4. Log your sets as you perform them
gymops log --exercise "Barbell Bench Press" --sets 3 --reps 8 --weight 80

# 5. Check if you achieved progressive overload compared to last session
gymops stats --exercise "Barbell Bench Press"

# 6. View your personal records
gymops prs

# 7. View exercise history
gymops history --exercise "Barbell Bench Press"

# 8. Add an exercise to the catalog
gymops add-exercise --name "Dumbbell Lateral Raise" --muscle-group "Shoulders" --type isolation

# 9. Create a custom training program with custom days and exercises
gymops add-program

# 10. Generate a weekly Markdown digest of your logged workouts
gymops digest
```

---

## Database

All logged workouts, PRs, and custom splits are kept in a single SQLite database on your host machine:
```
~/.gymops/gymops.db
```
This folder is created automatically on first run.

---

## Development & Tests

Run unit and integration tests using pytest:
```bash
# Install test requirements
uv pip install pytest

# Run tests
uv run pytest
```
