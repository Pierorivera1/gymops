"""
GymOps database layer.

Handles all SQLite interactions: initialization, schema creation,
autoseeding, and all CRUD query functions.

Concepts:
    Program   — The full training split you follow (e.g. 'Upper/Lower').
                Set this once. Only change when switching programs.
    ProgramDay — One training day within a program (e.g. 'Upper A').
                Set this at the start of each gym session.
    Exercise  — A movement in the catalog (e.g. 'Barbell Bench Press').
    Workout   — A logged set: exercise + sets + reps + weight.

Database location: ~/.gymops/gymops.db
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from gymops.models import DayExercise, Exercise, PR, Program, ProgramDay, Workout


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def get_db_path() -> Path:
    """
    Resolve the path to the SQLite database file.

    Returns ~/.gymops/gymops.db, creating the directory if it does not
    already exist. This ensures persistence on the host machine regardless
    of Docker restarts.
    """
    env_path = os.environ.get("GYMOPS_DB_PATH")
    if env_path:
        return Path(env_path)
    db_dir = Path.home() / ".gymops"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "gymops.db"


# ---------------------------------------------------------------------------
# Connection context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Yield an open SQLite connection with foreign key support enabled.

    Args:
        db_path: Optional override path (used in tests with a temp file).
    """
    path = str(db_path) if db_path else str(get_db_path())
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS exercises (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    UNIQUE NOT NULL,
    muscle_group TEXT    NOT NULL,
    type         TEXT    NOT NULL CHECK(type IN ('compound', 'isolation'))
);

CREATE TABLE IF NOT EXISTS programs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    created_by TEXT    NOT NULL CHECK(created_by IN ('system', 'user'))
);

CREATE TABLE IF NOT EXISTS program_days (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    day_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS day_exercises (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    day_id        INTEGER NOT NULL REFERENCES program_days(id) ON DELETE CASCADE,
    exercise_id   INTEGER NOT NULL REFERENCES exercises(id),
    target_sets   INTEGER NOT NULL,
    target_reps   INTEGER NOT NULL,
    display_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workouts (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER  NOT NULL REFERENCES exercises(id),
    day_id      INTEGER  REFERENCES program_days(id),
    sets        INTEGER  NOT NULL,
    reps        INTEGER  NOT NULL,
    weight      REAL     NOT NULL,
    epley_1rm   REAL     NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prs (
    id             INTEGER  PRIMARY KEY AUTOINCREMENT,
    exercise_id    INTEGER  UNIQUE NOT NULL REFERENCES exercises(id),
    max_weight     REAL     NOT NULL,
    max_epley_1rm  REAL     NOT NULL,
    timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS active_program (
    id         INTEGER PRIMARY KEY CHECK(id = 1),
    program_id INTEGER REFERENCES programs(id),
    day_id     INTEGER REFERENCES program_days(id)
);
"""


# ---------------------------------------------------------------------------
# Seed data — Jeff Nippard's default programs
# ---------------------------------------------------------------------------

_SEED_EXERCISES = [
    # Compound — Chest / Push
    ("Barbell Bench Press", "Chest", "compound"),
    ("Larsen Press", "Chest", "compound"),
    ("Close-Grip Incline Bench Press", "Chest", "compound"),
    ("Incline Dumbbell Press", "Chest", "compound"),
    ("Diamond Push-Ups", "Chest", "compound"),
    # Isolation — Chest / Push
    ("Cable Press-Around", "Chest", "isolation"),
    ("Cable Crossover / Fly", "Chest", "isolation"),
    # Compound — Shoulders
    ("Standing Dumbbell Shoulder Press", "Shoulders", "compound"),
    ("Overhead Press", "Shoulders", "compound"),
    ("Overhead Dumbbell Press", "Shoulders", "compound"),
    # Isolation — Shoulders
    ("Dumbbell Y-Raise", "Shoulders", "isolation"),
    ("Dumbbell Lateral Raise", "Shoulders", "isolation"),
    ("Cable Face Pulls", "Shoulders", "isolation"),
    ("Chest-Supported Rear Delt Raise", "Shoulders", "isolation"),
    # Isolation — Triceps
    ("Triceps Extension Superset", "Triceps", "isolation"),
    ("Cross-Body Cable Triceps Extension", "Triceps", "isolation"),
    ("Triceps Overhead Extension", "Triceps", "isolation"),
    ("Triceps Rope Pushdowns", "Triceps", "isolation"),
    ("Skull Crushers", "Triceps", "isolation"),
    # Compound — Back / Pull
    ("Lat Pulldown", "Back", "compound"),
    ("Lat Pulldown (Neutral Grip)", "Back", "compound"),
    ("Weighted Pull-Ups", "Back", "compound"),
    ("Weighted Chin-Ups", "Back", "compound"),
    ("Chest-Supported Dumbbell Row", "Back", "compound"),
    ("Barbell Row", "Back", "compound"),
    ("Chest-Supported T-Bar Row", "Back", "compound"),
    ("Kroc Row (Dumbbell)", "Back", "compound"),
    ("Barbell Deadlift", "Back", "compound"),
    # Isolation — Back
    ("Dumbbell Lat Pullover", "Back", "isolation"),
    # Isolation — Biceps
    ("EZ-Bar Bicep Curl", "Biceps", "isolation"),
    ("Preacher Curl", "Biceps", "isolation"),
    ("EZ-Bar Preacher Curl", "Biceps", "isolation"),
    ("Incline Dumbbell Bicep Curl", "Biceps", "isolation"),
    ("Cross-Body Hammer Curl", "Biceps", "isolation"),
    ("Barbell Bicep Curl", "Biceps", "isolation"),
    # Compound — Legs
    ("Barbell Back Squat", "Legs", "compound"),
    ("Romanian Deadlift", "Legs", "compound"),
    ("Barbell Romanian Deadlift", "Legs", "compound"),
    ("Conventional Deadlift", "Legs", "compound"),
    ("Stiff-Leg Deadlift", "Legs", "compound"),
    ("Leg Press", "Legs", "compound"),
    ("Dumbbell Walking Lunge", "Legs", "compound"),
    ("Glute Ham Raise", "Legs", "compound"),
    ("Ab Wheel Rollout", "Legs", "compound"),
    # Isolation — Legs
    ("Seated Leg Curl", "Legs", "isolation"),
    ("Lying Leg Curl", "Legs", "isolation"),
    ("Leg Extension", "Legs", "isolation"),
    ("Calf Press (on Leg Press)", "Calves", "isolation"),
    ("Seated Calf Raise", "Calves", "isolation"),
    ("Standing Calf Raise", "Calves", "isolation"),
    # Isolation — Core
    ("Weighted Decline Crunch", "Core", "isolation"),
    ("Hanging Leg Raise", "Core", "isolation"),
    ("Cable Crunch", "Core", "isolation"),
]

# Seed structure: program_name -> list of (day_name, day_order, [(exercise_name, sets, reps)])
_SEED_PROGRAMS = {
    "ULPPL (5-Day)": [
        ("Push (Day 1)", 1, [
            ("Barbell Bench Press", 3, 4),
            ("Larsen Press", 2, 10),
            ("Standing Dumbbell Shoulder Press", 3, 9),
            ("Cable Press-Around", 2, 13),
            ("Dumbbell Y-Raise", 3, 13),
            ("Triceps Extension Superset", 3, 8),
            ("Cross-Body Cable Triceps Extension", 2, 11),
        ]),
        ("Pull (Day 2)", 2, [
            ("Lat Pulldown", 4, 10),
            ("Chest-Supported Dumbbell Row", 3, 11),
            ("Dumbbell Lat Pullover", 2, 11),
            ("Cable Face Pulls", 3, 13),
            ("EZ-Bar Bicep Curl", 3, 7),
            ("Preacher Curl", 2, 11),
        ]),
        ("Legs (Day 3)", 3, [
            ("Barbell Back Squat", 3, 4),
            ("Romanian Deadlift", 3, 9),
            ("Dumbbell Walking Lunge", 2, 10),
            ("Seated Leg Curl", 3, 11),
            ("Calf Press (on Leg Press)", 4, 11),
            ("Weighted Decline Crunch", 3, 11),
        ]),
        ("Upper (Day 4)", 4, [
            ("Weighted Pull-Ups", 2, 9),
            ("Close-Grip Incline Bench Press", 3, 8),
            ("Kroc Row (Dumbbell)", 3, 11),
            ("Dumbbell Lateral Raise", 3, 13),
            ("Cross-Body Hammer Curl", 3, 11),
            ("Diamond Push-Ups", 1, 10),
        ]),
        ("Lower (Day 5)", 5, [
            ("Conventional Deadlift", 1, 5),
            ("Stiff-Leg Deadlift", 2, 8),
            ("Leg Press", 4, 11),
            ("Glute Ham Raise", 3, 9),
            ("Leg Extension", 3, 9),
            ("Seated Calf Raise", 4, 17),
            ("Hanging Leg Raise", 3, 15),
        ]),
    ],
    "PPL (6-Day)": [
        ("Push A", 1, [
            ("Barbell Bench Press", 3, 6),
            ("Incline Dumbbell Press", 3, 9),
            ("Cable Crossover / Fly", 3, 13),
            ("Dumbbell Lateral Raise", 4, 11),
            ("Triceps Overhead Extension", 3, 11),
            ("Triceps Rope Pushdowns", 3, 13),
        ]),
        ("Pull A", 2, [
            ("Weighted Pull-Ups", 3, 7),
            ("Barbell Row", 3, 9),
            ("Lat Pulldown (Neutral Grip)", 3, 11),
            ("Chest-Supported Rear Delt Raise", 3, 13),
            ("Incline Dumbbell Bicep Curl", 3, 9),
            ("EZ-Bar Preacher Curl", 3, 13),
        ]),
        ("Legs A", 3, [
            ("Barbell Back Squat", 3, 7),
            ("Leg Press", 3, 11),
            ("Lying Leg Curl", 3, 13),
            ("Leg Extension", 3, 13),
            ("Standing Calf Raise", 4, 11),
            ("Ab Wheel Rollout", 3, 11),
        ]),
        ("Push B", 4, [
            ("Overhead Press", 3, 7),
            ("Incline Dumbbell Press", 3, 9),
            ("Cable Crossover / Fly", 3, 13),
            ("Dumbbell Lateral Raise", 4, 11),
            ("Triceps Overhead Extension", 3, 11),
            ("Triceps Rope Pushdowns", 3, 13),
        ]),
        ("Pull B", 5, [
            ("Barbell Deadlift", 2, 5),
            ("Barbell Row", 3, 9),
            ("Lat Pulldown (Neutral Grip)", 3, 11),
            ("Chest-Supported Rear Delt Raise", 3, 13),
            ("Incline Dumbbell Bicep Curl", 3, 9),
            ("EZ-Bar Preacher Curl", 3, 13),
        ]),
        ("Legs B", 6, [
            ("Romanian Deadlift", 3, 9),
            ("Leg Press", 3, 11),
            ("Lying Leg Curl", 3, 13),
            ("Leg Extension", 3, 13),
            ("Standing Calf Raise", 4, 11),
            ("Ab Wheel Rollout", 3, 11),
        ]),
    ],
    "Upper/Lower (4-Day)": [
        ("Upper A (Strength)", 1, [
            ("Barbell Bench Press", 4, 5),
            ("Weighted Chin-Ups", 3, 7),
            ("Overhead Dumbbell Press", 3, 9),
            ("Dumbbell Lateral Raise", 3, 13),
            ("Cable Face Pulls", 3, 17),
            ("Skull Crushers", 3, 11),
            ("Barbell Bicep Curl", 3, 9),
        ]),
        ("Lower A (Strength)", 2, [
            ("Barbell Back Squat", 4, 5),
            ("Stiff-Leg Deadlift", 3, 9),
            ("Dumbbell Walking Lunge", 3, 10),
            ("Leg Extension", 3, 13),
            ("Seated Leg Curl", 3, 13),
            ("Standing Calf Raise", 4, 11),
            ("Cable Crunch", 3, 17),
        ]),
        ("Upper B (Hypertrophy)", 3, [
            ("Incline Dumbbell Press", 3, 11),
            ("Chest-Supported T-Bar Row", 3, 11),
            ("Overhead Dumbbell Press", 3, 9),
            ("Dumbbell Lateral Raise", 3, 13),
            ("Cable Face Pulls", 3, 17),
            ("Skull Crushers", 3, 11),
            ("Barbell Bicep Curl", 3, 9),
        ]),
        ("Lower B (Hypertrophy)", 4, [
            ("Barbell Romanian Deadlift", 3, 11),
            ("Leg Press", 3, 11),
            ("Dumbbell Walking Lunge", 3, 10),
            ("Leg Extension", 3, 13),
            ("Seated Leg Curl", 3, 13),
            ("Standing Calf Raise", 4, 11),
            ("Cable Crunch", 3, 17),
        ]),
    ],
}


# ---------------------------------------------------------------------------
# Initialization & seeding
# ---------------------------------------------------------------------------

def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initialize the database: create tables and seed default data.

    If the database already contains data, seeding is skipped (idempotent).

    Args:
        db_path: Optional override path for testing.
    """
    with get_connection(db_path) as conn:
        conn.executescript(_DDL)
        _seed_if_empty(conn)


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Seed exercises and Jeff Nippard programs only on a fresh database."""
    row = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()
    if row[0] > 0:
        return

    # Insert default exercises
    conn.executemany(
        "INSERT OR IGNORE INTO exercises (name, muscle_group, type) VALUES (?, ?, ?)",
        _SEED_EXERCISES,
    )

    # Insert Jeff Nippard programs, their days, and day exercises
    for program_name, days in _SEED_PROGRAMS.items():
        conn.execute(
            "INSERT INTO programs (name, created_by) VALUES (?, 'system')",
            (program_name,),
        )
        program_id = conn.execute(
            "SELECT id FROM programs WHERE name = ?", (program_name,)
        ).fetchone()["id"]

        for day_name, day_order, exercises in days:
            conn.execute(
                "INSERT INTO program_days (program_id, name, day_order) VALUES (?, ?, ?)",
                (program_id, day_name, day_order),
            )
            day_id = conn.execute(
                "SELECT id FROM program_days WHERE program_id = ? AND name = ?",
                (program_id, day_name),
            ).fetchone()["id"]

            for display_order, (ex_name, sets, reps) in enumerate(exercises, start=1):
                ex_row = conn.execute(
                    "SELECT id FROM exercises WHERE name = ?", (ex_name,)
                ).fetchone()
                if ex_row:
                    conn.execute(
                        """INSERT INTO day_exercises
                           (day_id, exercise_id, target_sets, target_reps, display_order)
                           VALUES (?, ?, ?, ?, ?)""",
                        (day_id, ex_row["id"], sets, reps, display_order),
                    )


# ---------------------------------------------------------------------------
# Exercise queries
# ---------------------------------------------------------------------------

def get_exercise_by_name(name: str, db_path: Optional[Path] = None) -> Optional[Exercise]:
    """
    Fetch a single exercise by name (case-insensitive).

    Args:
        name: The exercise name to search for.
        db_path: Optional override path for testing.

    Returns:
        An Exercise dataclass, or None if not found.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM exercises WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
    return Exercise(**dict(row)) if row else None


def add_exercise(
    name: str,
    muscle_group: str,
    exercise_type: str,
    db_path: Optional[Path] = None,
) -> Exercise:
    """
    Add a new exercise to the catalog in Title Case.

    Args:
        name: Display name for the exercise.
        muscle_group: Primary muscle group targeted.
        exercise_type: 'compound' or 'isolation'.
        db_path: Optional override path for testing.

    Returns:
        The newly created Exercise dataclass.

    Raises:
        ValueError: If an exercise with the same name already exists.
    """
    if get_exercise_by_name(name, db_path):
        raise ValueError(f"Exercise '{name}' already exists in the catalog.")
    title_name = name.title()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO exercises (name, muscle_group, type) VALUES (?, ?, ?)",
            (title_name, muscle_group, exercise_type),
        )
        row = conn.execute(
            "SELECT * FROM exercises WHERE name = ?", (title_name,)
        ).fetchone()
    return Exercise(**dict(row))


def get_all_exercises(db_path: Optional[Path] = None) -> list[Exercise]:
    """Return all exercises ordered alphabetically."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM exercises ORDER BY name").fetchall()
    return [Exercise(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Workout queries
# ---------------------------------------------------------------------------

def _calc_epley_1rm(weight: float, reps: int) -> float:
    """
    Calculate estimated 1-rep max using the Epley formula.

    Formula: 1RM = weight * (1 + reps / 30)

    Args:
        weight: Weight lifted in kg.
        reps: Number of repetitions performed.

    Returns:
        Estimated 1RM rounded to 2 decimal places.
    """
    return round(weight * (1 + reps / 30.0), 2)


def add_workout(
    exercise_name: str,
    sets: int,
    reps: int,
    weight: float,
    db_path: Optional[Path] = None,
) -> Workout:
    """
    Log a workout set and automatically update the PR if improved.

    Validates inputs, resolves exercise and active day from the database,
    calculates Epley 1RM, inserts the record, and upserts the PR table.

    Args:
        exercise_name: Name of the exercise (case-insensitive lookup).
        sets: Number of sets performed.
        reps: Number of reps performed per set.
        weight: Weight lifted in kg.
        db_path: Optional override path for testing.

    Returns:
        The newly logged Workout dataclass.

    Raises:
        ValueError: If validation fails or the exercise is not found.
    """
    if sets < 1:
        raise ValueError("Sets must be at least 1.")
    if reps < 1:
        raise ValueError("Reps must be at least 1.")
    if weight < 0.0:
        raise ValueError("Weight cannot be negative.")

    exercise = get_exercise_by_name(exercise_name, db_path)
    if not exercise:
        raise ValueError(
            f"Exercise '{exercise_name}' not found. "
            "Register it first with: gymops add-exercise"
        )

    epley_1rm = _calc_epley_1rm(weight, reps)
    active = get_active_state(db_path)
    active_day_id = active["day_id"] if active else None

    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO workouts (exercise_id, day_id, sets, reps, weight, epley_1rm)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (exercise.id, active_day_id, sets, reps, weight, epley_1rm),
        )
        row = conn.execute(
            """SELECT w.*, e.name as exercise_name
               FROM workouts w JOIN exercises e ON w.exercise_id = e.id
               WHERE w.exercise_id = ? ORDER BY w.id DESC LIMIT 1""",
            (exercise.id,),
        ).fetchone()
        _upsert_pr(conn, exercise.id, weight, epley_1rm)

    d = dict(row)
    return Workout(
        id=d["id"],
        exercise_id=d["exercise_id"],
        exercise_name=d["exercise_name"],
        sets=d["sets"],
        reps=d["reps"],
        weight=d["weight"],
        epley_1rm=d["epley_1rm"],
        timestamp=d["timestamp"],
        day_id=d.get("day_id"),
    )


def _upsert_pr(
    conn: sqlite3.Connection,
    exercise_id: int,
    weight: float,
    epley_1rm: float,
) -> None:
    """Insert or update the PR if the new 1RM is a personal record."""
    existing = conn.execute(
        "SELECT max_epley_1rm FROM prs WHERE exercise_id = ?", (exercise_id,)
    ).fetchone()

    if not existing:
        conn.execute(
            "INSERT INTO prs (exercise_id, max_weight, max_epley_1rm) VALUES (?, ?, ?)",
            (exercise_id, weight, epley_1rm),
        )
    elif epley_1rm > existing["max_epley_1rm"]:
        conn.execute(
            """UPDATE prs SET max_weight = ?, max_epley_1rm = ?,
               timestamp = CURRENT_TIMESTAMP WHERE exercise_id = ?""",
            (weight, epley_1rm, exercise_id),
        )


def get_history(
    exercise_name: str,
    limit: int = 10,
    db_path: Optional[Path] = None,
) -> list[Workout]:
    """
    Return the most recent workout logs for an exercise, newest first.

    Args:
        exercise_name: Name of the exercise (case-insensitive).
        limit: Maximum number of records to return.
        db_path: Optional override path for testing.

    Raises:
        ValueError: If the exercise is not found.
    """
    exercise = get_exercise_by_name(exercise_name, db_path)
    if not exercise:
        raise ValueError(f"Exercise '{exercise_name}' not found.")

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT w.*, e.name as exercise_name
               FROM workouts w JOIN exercises e ON w.exercise_id = e.id
               WHERE w.exercise_id = ?
               ORDER BY w.timestamp DESC, w.id DESC LIMIT ?""",
            (exercise.id, limit),
        ).fetchall()

    return [
        Workout(
            id=r["id"],
            exercise_id=r["exercise_id"],
            exercise_name=r["exercise_name"],
            sets=r["sets"],
            reps=r["reps"],
            weight=r["weight"],
            epley_1rm=r["epley_1rm"],
            timestamp=r["timestamp"],
            day_id=r["day_id"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# PR queries
# ---------------------------------------------------------------------------

def get_all_prs(db_path: Optional[Path] = None) -> list[PR]:
    """Return all personal records joined with exercise names."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT p.*, e.name as exercise_name
               FROM prs p JOIN exercises e ON p.exercise_id = e.id
               ORDER BY e.name""",
        ).fetchall()

    return [
        PR(
            id=r["id"],
            exercise_id=r["exercise_id"],
            exercise_name=r["exercise_name"],
            max_weight=r["max_weight"],
            max_epley_1rm=r["max_epley_1rm"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Program queries
# ---------------------------------------------------------------------------

def get_all_programs(db_path: Optional[Path] = None) -> list[Program]:
    """Return all programs ordered by name."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM programs ORDER BY name").fetchall()
    return [Program(**dict(r)) for r in rows]


def get_program_days(
    program_id: int, db_path: Optional[Path] = None
) -> list[ProgramDay]:
    """
    Return all training days for a program, ordered by day_order.

    Args:
        program_id: The ID of the program.
        db_path: Optional override path for testing.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM program_days WHERE program_id = ? ORDER BY day_order",
            (program_id,),
        ).fetchall()
    return [ProgramDay(**dict(r)) for r in rows]


def get_day_exercises(
    day_id: int, db_path: Optional[Path] = None
) -> list[DayExercise]:
    """
    Return all exercises for a training day, ordered by display_order.

    Args:
        day_id: The ID of the program day.
        db_path: Optional override path for testing.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT de.*, e.name as exercise_name
               FROM day_exercises de
               JOIN exercises e ON de.exercise_id = e.id
               WHERE de.day_id = ?
               ORDER BY de.display_order""",
            (day_id,),
        ).fetchall()

    return [
        DayExercise(
            id=r["id"],
            day_id=r["day_id"],
            exercise_id=r["exercise_id"],
            exercise_name=r["exercise_name"],
            target_sets=r["target_sets"],
            target_reps=r["target_reps"],
            display_order=r["display_order"],
        )
        for r in rows
    ]


def add_program(
    name: str,
    days: list[tuple[str, list[tuple[int, int, int]]]],
    db_path: Optional[Path] = None,
) -> Program:
    """
    Create a new user-defined training program.

    Args:
        name: Unique name for the program.
        days: List of (day_name, [(exercise_id, target_sets, target_reps)]).
        db_path: Optional override path for testing.

    Returns:
        The newly created Program dataclass.

    Raises:
        ValueError: If a program with the same name already exists.
    """
    with get_connection(db_path) as conn:
        exists = conn.execute(
            "SELECT id FROM programs WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        if exists:
            raise ValueError(f"Program '{name}' already exists.")

        conn.execute(
            "INSERT INTO programs (name, created_by) VALUES (?, 'user')", (name,)
        )
        program_row = conn.execute(
            "SELECT * FROM programs WHERE name = ?", (name,)
        ).fetchone()
        program_id = program_row["id"]

        for day_order, (day_name, exercises) in enumerate(days, start=1):
            conn.execute(
                "INSERT INTO program_days (program_id, name, day_order) VALUES (?, ?, ?)",
                (program_id, day_name, day_order),
            )
            day_id = conn.execute(
                "SELECT id FROM program_days WHERE program_id = ? AND name = ?",
                (program_id, day_name),
            ).fetchone()["id"]

            for display_order, (ex_id, sets, reps) in enumerate(exercises, start=1):
                conn.execute(
                    """INSERT INTO day_exercises
                       (day_id, exercise_id, target_sets, target_reps, display_order)
                       VALUES (?, ?, ?, ?, ?)""",
                    (day_id, ex_id, sets, reps, display_order),
                )

    return Program(**dict(program_row))


# ---------------------------------------------------------------------------
# Active program/day state
# ---------------------------------------------------------------------------

def get_active_state(db_path: Optional[Path] = None) -> Optional[dict]:
    """
    Return the currently active program and day as a dict, or None.

    Returns:
        A dict with keys 'program', 'day' (both dataclasses) and
        'program_id', 'day_id' (ints), or None if nothing is set.
    """
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM active_program WHERE id = 1").fetchone()
    if not row:
        return None

    result: dict = {"program_id": row["program_id"], "day_id": row["day_id"]}

    if row["program_id"]:
        with get_connection(db_path) as conn:
            p = conn.execute(
                "SELECT * FROM programs WHERE id = ?", (row["program_id"],)
            ).fetchone()
        result["program"] = Program(**dict(p)) if p else None
    else:
        result["program"] = None

    if row["day_id"]:
        with get_connection(db_path) as conn:
            d = conn.execute(
                "SELECT * FROM program_days WHERE id = ?", (row["day_id"],)
            ).fetchone()
        result["day"] = ProgramDay(**dict(d)) if d else None
    else:
        result["day"] = None

    return result


def set_active_program(program_id: int, db_path: Optional[Path] = None) -> None:
    """
    Set the active program. Clears the active day (user must set it separately).

    Args:
        program_id: The program to mark as active.
        db_path: Optional override path for testing.

    Raises:
        ValueError: If the program_id does not exist.
    """
    with get_connection(db_path) as conn:
        exists = conn.execute(
            "SELECT id FROM programs WHERE id = ?", (program_id,)
        ).fetchone()
        if not exists:
            raise ValueError(f"Program with id {program_id} not found.")
        conn.execute(
            """INSERT INTO active_program (id, program_id, day_id) VALUES (1, ?, NULL)
               ON CONFLICT(id) DO UPDATE SET program_id = excluded.program_id, day_id = NULL""",
            (program_id,),
        )


def set_active_day(day_id: int, db_path: Optional[Path] = None) -> None:
    """
    Set today's training day within the active program.

    Args:
        day_id: The program_days ID to mark as today's session.
        db_path: Optional override path for testing.

    Raises:
        ValueError: If no program is active, or the day doesn't belong to it.
    """
    active = get_active_state(db_path)
    if not active or not active.get("program_id"):
        raise ValueError(
            "No active program. Set one first with: gymops select-program"
        )

    with get_connection(db_path) as conn:
        day_row = conn.execute(
            "SELECT * FROM program_days WHERE id = ? AND program_id = ?",
            (day_id, active["program_id"]),
        ).fetchone()
        if not day_row:
            raise ValueError(
                f"Day id {day_id} does not belong to the active program."
            )
        conn.execute(
            """INSERT INTO active_program (id, program_id, day_id) VALUES (1, ?, ?)
               ON CONFLICT(id) DO UPDATE SET day_id = excluded.day_id""",
            (active["program_id"], day_id),
        )


# ---------------------------------------------------------------------------
# Stats & digest queries
# ---------------------------------------------------------------------------

def get_last_two_sessions(
    exercise_name: str, db_path: Optional[Path] = None
) -> list[Workout]:
    """Return the two most recent workout sessions for an exercise."""
    return get_history(exercise_name, limit=2, db_path=db_path)


def get_workouts_in_range(
    days: int = 7, db_path: Optional[Path] = None
) -> list[Workout]:
    """Return all workouts logged within the last N days."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT w.*, e.name as exercise_name
               FROM workouts w JOIN exercises e ON w.exercise_id = e.id
               WHERE w.timestamp >= datetime('now', ?)
               ORDER BY w.timestamp DESC, w.id DESC""",
            (f"-{days} days",),
        ).fetchall()

    return [
        Workout(
            id=r["id"],
            exercise_id=r["exercise_id"],
            exercise_name=r["exercise_name"],
            sets=r["sets"],
            reps=r["reps"],
            weight=r["weight"],
            epley_1rm=r["epley_1rm"],
            timestamp=r["timestamp"],
            day_id=r["day_id"],
        )
        for r in rows
    ]
