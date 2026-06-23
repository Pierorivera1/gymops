"""
GymOps data models.

Defines dataclasses used throughout the application to represent
structured data returned from the database layer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Exercise:
    """Represents a single exercise in the catalog."""

    id: int
    name: str
    muscle_group: str
    type: str  # 'compound' or 'isolation'


@dataclass
class Workout:
    """Represents a single logged workout set."""

    id: int
    exercise_id: int
    exercise_name: str
    sets: int
    reps: int
    weight: float
    epley_1rm: float
    timestamp: datetime
    day_id: Optional[int] = None  # Which training day this log belongs to


@dataclass
class PR:
    """Represents the personal record for an exercise."""

    id: int
    exercise_id: int
    exercise_name: str
    max_weight: float
    max_epley_1rm: float
    timestamp: datetime


@dataclass
class Program:
    """
    Represents a full training program (e.g. 'Upper/Lower', 'PPL').

    A program is the complete split you follow. It contains multiple
    training days (e.g. Upper A, Lower A, Upper B, Lower B).
    You set this once and only change it when switching programs.
    """

    id: int
    name: str
    created_by: str  # 'system' or 'user'


@dataclass
class ProgramDay:
    """
    Represents one training day within a program (e.g. 'Upper A').

    You select the active day at the start of each gym session.
    It guides which exercises to log and their target sets/reps.
    """

    id: int
    program_id: int
    name: str
    day_order: int


@dataclass
class DayExercise:
    """Represents a single exercise entry within a training day."""

    id: int
    day_id: int
    exercise_id: int
    exercise_name: str
    target_sets: int
    target_reps: int
    display_order: int
