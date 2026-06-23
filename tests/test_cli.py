"""Tests for gymops/cli.py — CLI command layer."""

import pytest
from typer.testing import CliRunner
from gymops.cli import app
from gymops import db


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_version(runner):
    """Test the --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "GymOps version" in result.stdout


def test_cli_add_exercise(runner):
    """Test registering a new exercise via CLI."""
    result = runner.invoke(
        app,
        ["add-exercise", "-n", "Bulgarian Split Squat", "-m", "Legs", "-t", "compound"],
    )
    assert result.exit_code == 0
    assert "New Exercise Registered" in result.stdout
    assert "Bulgarian Split Squat" in result.stdout


def test_cli_add_exercise_invalid_type(runner):
    """Test error handling when registering invalid type."""
    result = runner.invoke(
        app,
        ["add-exercise", "-n", "Invalid Ex", "-m", "Legs", "-t", "invalid_type"],
    )
    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_cli_list_programs(runner):
    """Test listing available programs."""
    result = runner.invoke(app, ["list-programs"])
    assert result.exit_code == 0
    assert "Available Training Programs" in result.stdout
    assert "Upper/Lower" in result.stdout


def test_cli_select_program_and_set_day(runner):
    """Test selecting a program and setting active training day."""
    # Try set-day when no program is active
    result_day_fail = runner.invoke(app, ["set-day", "Upper A (Strength)"])
    assert result_day_fail.exit_code == 1
    assert "No active program" in result_day_fail.stdout

    # Select program
    result_select = runner.invoke(app, ["select-program", "Upper/Lower (4-Day)"])
    assert result_select.exit_code == 0
    assert "is now active" in result_select.stdout

    # Now set day
    result_day = runner.invoke(app, ["set-day", "Upper A (Strength)"])
    assert result_day.exit_code == 0
    assert "Training day set to" in result_day.stdout

    # Verify state in list-programs
    result_list = runner.invoke(app, ["list-programs"])
    assert result_list.exit_code == 0
    assert "Upper A (Strength)" in result_list.stdout
    assert "← today" in result_list.stdout


def test_cli_log_workout(runner):
    """Test logging a workout set."""
    # Set active program and day first
    runner.invoke(app, ["select-program", "Upper/Lower (4-Day)"])
    runner.invoke(app, ["set-day", "Upper A (Strength)"])

    # Log Bench Press (seeded compound exercise)
    result = runner.invoke(
        app,
        ["log", "-e", "Barbell Bench Press", "-s", "3", "-r", "8", "-w", "80.0"],
    )
    assert result.exit_code == 0
    assert "Workout Logged Successfully!" in result.stdout
    assert "Barbell Bench Press" in result.stdout
    assert "Routine Guidelines" in result.stdout


def test_cli_stats_progressive_overload(runner):
    """Test progressive overload comparison command."""
    # Log 1 session
    runner.invoke(app, ["log", "-e", "Barbell Back Squat", "-s", "3", "-r", "5", "-w", "100"])
    
    # Try stats with 1 log (should say not enough data)
    result_one = runner.invoke(app, ["stats", "-e", "Barbell Back Squat"])
    assert result_one.exit_code == 0
    assert "Not enough data" in result_one.stdout

    # Log 2nd session (improvement)
    runner.invoke(app, ["log", "-e", "Barbell Back Squat", "-s", "3", "-r", "5", "-w", "105"])
    result_two = runner.invoke(app, ["stats", "-e", "Barbell Back Squat"])
    assert result_two.exit_code == 0
    assert "PROGRESSIVE OVERLOAD SUCCESS!" in result_two.stdout
    assert "+5.00%" in result_two.stdout


def test_cli_add_program_wizard(runner):
    """Test interactive program creation wizard."""
    # We will simulate entering:
    # Program name: Custom Split
    # Day 1: Push Day
    # Exercise: Barbell Bench Press
    # Sets: 3
    # Reps: 8
    # Add another exercise to day: n
    # Add another training day: n
    inputs = "Custom Split\nPush Day\nBarbell Bench Press\n3\n8\nn\nn\n"
    result = runner.invoke(app, ["add-program"], input=inputs)
    assert result.exit_code == 0
    assert "Program 'Custom Split' saved with 1 days." in result.stdout


def test_cli_digest(runner, tmp_path, monkeypatch):
    """Test digest command."""
    # Change working directory of test to tmp_path so digest file is written there
    monkeypatch.chdir(tmp_path)
    
    # Log a workout so there is data
    runner.invoke(app, ["log", "-e", "Barbell Back Squat", "-s", "3", "-r", "5", "-w", "100"])
    
    result = runner.invoke(app, ["digest"])
    assert result.exit_code == 0
    assert "Digest Generated Successfully!" in result.stdout
