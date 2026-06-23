"""
GymOps data models.

Defines dataclasses used throughout the application to represent
structured data returned from the database layer.
"""

from dataclasses import dataclass
from datetime import datetime


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
class Routine:
    """Represents a workout routine."""

    id: int
    name: str
    created_by: str  # 'system' or 'user'


@dataclass
class RoutineExercise:
    """Represents a single exercise entry within a routine."""

    id: int
    routine_id: int
    exercise_id: int
    exercise_name: str
    target_sets: int
    target_reps: int
    display_order: int
