# GymOps 🏋️

> A terminal-based workout tracker I built because I was tired of tracking my sets in my notes app.

GymOps is a CLI tool that lives in your terminal. You log your workouts, it tracks your personal records, tells you if you're actually getting stronger, and generates a weekly summary of what you've been doing. That's it.

Inspired by [lazygit](https://github.com/jesseduffield/lazygit) — the idea that a good terminal tool should get out of your way and just work.

---

## What it does

- Logs workouts (exercise, sets, reps, weight) to a local SQLite database at `~/.gymops/gymops.db`
- Calculates your estimated 1-rep max using the Epley formula after every set
- Tracks personal records per exercise and alerts you when you break one
- Comes pre-loaded with Jeff Nippard's ULPPL, PPL, and Upper/Lower routines
- Shows progressive overload stats — did you actually get stronger since last session?
- Generates a weekly Markdown digest of your training
- Eventually: a full TUI interface like lazygit, so you can browse your history visually

---

## Quickstart

```bash
# Clone and set up
git clone https://github.com/Pierorivera1/gymops.git
cd gymops

# Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e .

# You're ready
gymops --help
```

> **Requires**: Python 3.12+ and [uv](https://github.com/astral-sh/uv)

---

## Usage

```bash
# Pick a routine to follow
gymops list-routines
gymops select-routine "ULPPL — Push (Day 1)"

# Log a session
gymops log --exercise "Barbell Bench Press" --sets 4 --reps 8 --weight 80

# Did you get stronger?
gymops stats --exercise "Barbell Bench Press"

# Check your PRs
gymops prs

# See your full history for an exercise
gymops history --exercise "Barbell Bench Press"

# Add an exercise that isn't in the default catalog
gymops add-exercise --name "Dumbbell Curl" --muscle-group "Biceps" --type isolation

# Build your own routine
gymops add-routine

# Generate a weekly summary
gymops digest
```

---

## How the database works

Your data never leaves your machine. GymOps stores everything in a single SQLite file at:

```
~/.gymops/gymops.db
```

On first run it auto-creates the database and seeds it with Jeff Nippard's default routines so you can start logging immediately.

---

## Roadmap

- [x] CLI with all core commands
- [x] SQLite persistence with PR tracking
- [x] Jeff Nippard routine autoseed
- [x] Epley 1RM calculation and progressive overload stats
- [x] Weekly digest generator
- [ ] Full test suite
- [ ] Docker support (run it anywhere without installing Python)
- [ ] TUI interface — lazygit-style, browse history, log sets, view PRs visually
