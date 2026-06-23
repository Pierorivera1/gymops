"""Tests for gymops/db.py — database layer."""

import pytest
from gymops import db as db_module


def test_db_seeding(db_path):
    """Test that default exercises and Jeff Nippard programs are seeded on init."""
    exercises = db_module.get_all_exercises(db_path=db_path)
    assert len(exercises) > 40  # Seeding has 53 exercises

    programs = db_module.get_all_programs(db_path=db_path)
    assert len(programs) == 3  # ULPPL, PPL, Upper/Lower

    # Check program days for Upper/Lower
    ul_program = next(p for p in programs if "Upper/Lower" in p.name)
    days = db_module.get_program_days(ul_program.id, db_path=db_path)
    assert len(days) == 4
    assert days[0].name == "Upper A (Strength)"


def test_add_exercise(db_path):
    """Test registering a new exercise in the catalog."""
    new_ex = db_module.add_exercise("Bulgarian Split Squat", "Legs", "compound", db_path=db_path)
    assert new_ex.name == "Bulgarian Split Squat"
    assert new_ex.muscle_group == "Legs"
    assert new_ex.type == "compound"

    # Duplicate should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        db_module.add_exercise("bulgarian split squat", "Legs", "compound", db_path=db_path)


def test_active_state_manipulation(db_path):
    """Test getting/setting active programs and days."""
    # Initially no active state
    state = db_module.get_active_state(db_path=db_path)
    assert state is None

    programs = db_module.get_all_programs(db_path=db_path)
    ul_prog = next(p for p in programs if "Upper/Lower" in p.name)

    # Set active program
    db_module.set_active_program(ul_prog.id, db_path=db_path)
    state = db_module.get_active_state(db_path=db_path)
    assert state is not None
    assert state["program_id"] == ul_prog.id
    assert state["program"].name == ul_prog.name
    assert state["day_id"] is None
    assert state["day"] is None

    # Try setting a day that does not belong to active program (should fail)
    # Let's find a day from another program
    other_prog = next(p for p in programs if p.id != ul_prog.id)
    other_days = db_module.get_program_days(other_prog.id, db_path=db_path)
    with pytest.raises(ValueError, match="does not belong to the active program"):
        db_module.set_active_day(other_days[0].id, db_path=db_path)

    # Set valid day
    ul_days = db_module.get_program_days(ul_prog.id, db_path=db_path)
    db_module.set_active_day(ul_days[0].id, db_path=db_path)
    state = db_module.get_active_state(db_path=db_path)
    assert state["day_id"] == ul_days[0].id
    assert state["day"].name == ul_days[0].name


def test_add_program(db_path):
    """Test creating a custom training program."""
    exercises = db_module.get_all_exercises(db_path=db_path)
    bench_id = next(ex.id for ex in exercises if ex.name == "Barbell Bench Press")
    squat_id = next(ex.id for ex in exercises if ex.name == "Barbell Back Squat")

    custom_days = [
        ("Push Day", [(bench_id, 3, 8)]),
        ("Leg Day", [(squat_id, 4, 6)]),
    ]

    prog = db_module.add_program("Custom Push/Legs", custom_days, db_path=db_path)
    assert prog.name == "Custom Push/Legs"
    assert prog.created_by == "user"

    p_days = db_module.get_program_days(prog.id, db_path=db_path)
    assert len(p_days) == 2
    assert p_days[0].name == "Push Day"

    day_exs = db_module.get_day_exercises(p_days[0].id, db_path=db_path)
    assert len(day_exs) == 1
    assert day_exs[0].exercise_id == bench_id
    assert day_exs[0].target_sets == 3
    assert day_exs[0].target_reps == 8


def test_add_workout_and_prs(db_path):
    """Test logging workout sets and how PRs are updated."""
    # 1. Log a workout set (should succeed and set a PR)
    w1 = db_module.add_workout("Barbell Bench Press", 3, 8, 80.0, db_path=db_path)
    assert w1.exercise_name == "Barbell Bench Press"
    assert w1.sets == 3
    assert w1.reps == 8
    assert w1.weight == 80.0
    expected_1rm = round(80.0 * (1 + 8 / 30.0), 2)
    assert w1.epley_1rm == expected_1rm

    prs = db_module.get_all_prs(db_path=db_path)
    assert len(prs) == 1
    assert prs[0].exercise_name == "Barbell Bench Press"
    assert prs[0].max_weight == 80.0
    assert prs[0].max_epley_1rm == expected_1rm

    # 2. Log a worse workout set (should not update PR)
    db_module.add_workout("Barbell Bench Press", 3, 5, 70.0, db_path=db_path)
    prs2 = db_module.get_all_prs(db_path=db_path)
    assert prs2[0].max_weight == 80.0
    assert prs2[0].max_epley_1rm == expected_1rm

    # 3. Log a better workout set (should update PR)
    db_module.add_workout("Barbell Bench Press", 3, 8, 85.0, db_path=db_path)
    prs3 = db_module.get_all_prs(db_path=db_path)
    assert prs3[0].max_weight == 85.0
    expected_new_1rm = round(85.0 * (1 + 8 / 30.0), 2)
    assert prs3[0].max_epley_1rm == expected_new_1rm

    # 4. Check history
    history = db_module.get_history("Barbell Bench Press", db_path=db_path)
    assert len(history) == 3
    # Check order (newest first)
    assert history[0].weight == 85.0
    assert history[1].weight == 70.0
    assert history[2].weight == 80.0


def test_stats_progressive_overload(db_path):
    """Test retrieval of last two sessions for stats."""
    # Not enough data initially
    with pytest.raises(ValueError):
        # Non-existent exercise
        db_module.get_last_two_sessions("Non Existent", db_path=db_path)

    # Correct exercise but only 1 session logged
    db_module.add_workout("Barbell Back Squat", 3, 5, 100.0, db_path=db_path)
    sessions = db_module.get_last_two_sessions("Barbell Back Squat", db_path=db_path)
    assert len(sessions) == 1

    # Log second session
    db_module.add_workout("Barbell Back Squat", 3, 5, 105.0, db_path=db_path)
    sessions2 = db_module.get_last_two_sessions("Barbell Back Squat", db_path=db_path)
    assert len(sessions2) == 2
    assert sessions2[0].weight == 105.0
    assert sessions2[1].weight == 100.0
