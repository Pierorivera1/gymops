"""
GymOps CLI — Command Line Interface.

All user-facing commands are defined here using Typer.
Rich is used for styled terminal output.

Commands:
    log            — Log a workout set
    add-exercise   — Register a new exercise
    add-program    — Interactive wizard to create a training program
    list-programs  — Show all training programs and days
    select-program — Set the active training program
    set-day        — Set today's training day within the active program
    stats          — Progressive overload stats for an exercise
    history        — View workout history for an exercise
    prs            — Show all personal records
    digest         — Generate weekly Markdown report
"""

import typer
from rich.console import Console

from gymops import __version__
from gymops.db import init_db

app = typer.Typer(
    name="gymops",
    help="🏋️  GymOps — CLI Workout Tracker",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print the application version and exit."""
    if value:
        console.print(f"[cyan]GymOps[/] version [bold]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """GymOps — Your personal CLI workout tracker."""
    # Initialize the database on every invocation (idempotent)
    init_db()


# ---------------------------------------------------------------------------
# gymops log
# ---------------------------------------------------------------------------

@app.command()
def log(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Exercise name."),
    sets: int = typer.Option(..., "--sets", "-s", help="Number of sets performed."),
    reps: int = typer.Option(..., "--reps", "-r", help="Number of reps per set."),
    weight: float = typer.Option(..., "--weight", "-w", help="Weight lifted in kg."),
) -> None:
    """Log a completed workout set and auto-update your PR."""
    from gymops import db
    from rich.panel import Panel

    try:
        workout = db.add_workout(exercise, sets, reps, weight)
        active = db.get_active_state()

        # Build the output panel
        content = (
            f"[dim]Exercise:[/]      [bold]{workout.exercise_name}[/]\n"
            f"[dim]Sets x Reps:[/]  [bold]{workout.sets} x {workout.reps}[/]\n"
            f"[dim]Weight:[/]       [bold]{workout.weight:.1f} kg[/]\n"
            f"[dim]Est. 1RM:[/]     [bold cyan]{workout.epley_1rm:.1f} kg[/] [gold1]★[/]\n"
            f"[dim]Timestamp:[/]    {workout.timestamp}\n"
            f"[dim]Status:[/]       Saved to database [bold spring_green1]✓[/]"
        )

        console.print(
            Panel(content, title="[bold]🏋️  Workout Logged Successfully![/]", border_style="cyan")
        )

        # Show program day guidelines if applicable
        if active and active.get("day"):
            active_day = active["day"]
            day_exs = db.get_day_exercises(active_day.id)
            for dex in day_exs:
                if dex.exercise_name.lower() == workout.exercise_name.lower():
                    ex = db.get_exercise_by_name(workout.exercise_name)
                    rep_range = "6-10 reps" if ex and ex.type == "compound" else "8-12 reps"
                    console.print(
                        f"\n[dim]Routine Guidelines for {workout.exercise_name}:[/dim]"
                    )
                    console.print(
                        f"  Target Reps for [cyan]{active_day.name}[/]: "
                        f"[cyan]{dex.target_reps} reps[/] "
                        f"(Suggested {ex.type.capitalize()} range: [dim]{rep_range}[/])"
                    )
                    break

    except ValueError as e:
        console.print(f"[bright_red]Error:[/] {e}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# gymops add-exercise
# ---------------------------------------------------------------------------

@app.command(name="add-exercise")
def add_exercise(
    name: str = typer.Option(..., "--name", "-n", help="Exercise name."),
    muscle_group: str = typer.Option(..., "--muscle-group", "-m", help="Primary muscle group."),
    exercise_type: str = typer.Option(
        ..., "--type", "-t", help="Exercise type: compound or isolation."
    ),
) -> None:
    """Register a new exercise in the catalog."""
    from gymops import db
    from rich.panel import Panel

    if exercise_type not in ("compound", "isolation"):
        console.print("[bright_red]Error:[/] Type must be 'compound' or 'isolation'.")
        raise typer.Exit(code=1)

    try:
        exercise = db.add_exercise(name, muscle_group, exercise_type)
        rep_range = "6-10 reps" if exercise.type == "compound" else "8-12 reps"
        content = (
            f"[dim]Name:[/]          [bold]{exercise.name}[/]\n"
            f"[dim]Muscle Group:[/]  {exercise.muscle_group}\n"
            f"[dim]Type:[/]          {exercise.type.capitalize()} "
            f"([dim]Suggested: {rep_range}[/])\n"
            f"[dim]Status:[/]        Registered successfully [bold spring_green1]✓[/]"
        )
        console.print(
            Panel(content, title="[bold]📝 New Exercise Registered[/]", border_style="cyan")
        )
    except ValueError as e:
        console.print(f"[bright_red]Error:[/] {e}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# gymops add-program
# ---------------------------------------------------------------------------

@app.command(name="add-program")
def add_program() -> None:
    """Interactive wizard to create a custom training program."""
    from gymops import db

    console.print("[cyan]🏋️  GymOps Program Creation Wizard[/]\n")

    # Program name
    name = typer.prompt("Enter program name")
    with db.get_connection() as conn:
        exists = conn.execute(
            "SELECT id FROM programs WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
    if exists:
        console.print(f"[bright_red]Error:[/] Program '{name}' already exists.")
        raise typer.Exit(code=1)

    days: list[tuple[str, list[tuple[int, int, int]]]] = []
    day_num = 1

    while True:
        console.print(f"\n[bold]Defining Day #{day_num}[/]:")
        day_name = typer.prompt(f"Enter name for training day #{day_num} (e.g. Upper A)")

        exercises: list[tuple[int, int, int]] = []
        ex_num = 1

        while True:
            console.print(f"\n  Adding Exercise #{ex_num} to '{day_name}':")
            ex_name = typer.prompt("  Enter exercise name")
            exercise = db.get_exercise_by_name(ex_name)
            if not exercise:
                console.print(
                    f"[bright_red]    ✗ '{ex_name}' not found.[/] "
                    "Register it first with: [cyan]gymops add-exercise[/]"
                )
                continue

            rep_range = "6-10" if exercise.type == "compound" else "8-12"
            console.print(
                f"    [dim]-> {exercise.name} registered as "
                f"{exercise.type.capitalize()} (Suggested reps: {rep_range})[/]"
            )

            target_sets = typer.prompt("    Enter target sets", type=int)
            target_reps = typer.prompt(f"    Enter target reps (Suggested: {rep_range})", type=int)
            exercises.append((exercise.id, target_sets, target_reps))
            console.print("  [cyan]Exercise added![/]")

            another_ex = typer.confirm("  Add another exercise to this day?", default=True)
            if not another_ex:
                break
            ex_num += 1

        days.append((day_name, exercises))
        console.print(f"[cyan]Day '{day_name}' added with {len(exercises)} exercises![/]")

        another_day = typer.confirm("Add another training day to this program?", default=True)
        if not another_day:
            break
        day_num += 1

    try:
        db.add_program(name, days)
        console.print(
            f"\n[bold spring_green1]Success:[/] Program '[bold]{name}[/]' "
            f"saved with {len(days)} days. [bold spring_green1]✓[/]"
        )
    except ValueError as e:
        console.print(f"[bright_red]Error:[/] {e}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# gymops list-programs
# ---------------------------------------------------------------------------

@app.command(name="list-programs")
def list_programs() -> None:
    """List all available training programs and days."""
    from gymops import db
    from rich.table import Table
    import rich.box as box

    programs = db.get_all_programs()
    active = db.get_active_state()

    table = Table(box=box.ROUNDED, border_style="cyan", show_lines=True)
    table.add_column("Status", style="bold", width=12)
    table.add_column("Program", style="white")
    table.add_column("Created By", style="dim")
    table.add_column("Days", justify="right")

    active_program_id = active["program_id"] if active else None
    active_day_id = active["day_id"] if active else None

    for p in programs:
        p_days = db.get_program_days(p.id)
        status = "[bold spring_green1]✓ ACTIVE[/]" if (active_program_id == p.id) else ""
        table.add_row(status, p.name, p.created_by.capitalize(), str(len(p_days)))

    console.print("\n[cyan]📋 Available Training Programs[/]\n")
    console.print(table)

    if active and active.get("program"):
        active_prog = active["program"]
        console.print(f"\n[cyan]{active_prog.name} — Training Days:[/]")
        p_days = db.get_program_days(active_prog.id)
        for idx, d in enumerate(p_days, start=1):
            d_exs = db.get_day_exercises(d.id)
            ex_count = len(d_exs)
            suffix = " [bold spring_green1]← today[/]" if (active_day_id == d.id) else ""
            console.print(f"  {idx}. {d.name} — {ex_count} exercises{suffix}")


# ---------------------------------------------------------------------------
# gymops select-program
# ---------------------------------------------------------------------------

@app.command(name="select-program")
def select_program(
    program_name: str = typer.Argument(..., help="Name of the program to activate."),
) -> None:
    """Set the active training program."""
    from gymops import db

    programs = db.get_all_programs()
    target_program = None
    for p in programs:
        if p.name.lower() == program_name.lower():
            target_program = p
            break

    if not target_program:
        console.print(f"[bright_red]Error:[/] Program '{program_name}' not found.")
        raise typer.Exit(code=1)

    db.set_active_program(target_program.id)
    console.print(
        f"Program '[cyan]{target_program.name}[/]' is now active! [bold spring_green1]✓[/]"
    )
    console.print("[dim]Use 'gymops set-day' to choose today's training day.[/dim]")


# ---------------------------------------------------------------------------
# gymops set-day
# ---------------------------------------------------------------------------

@app.command(name="set-day")
def set_day(
    day_name: str = typer.Argument(..., help="Name of the training day to activate."),
) -> None:
    """Set today's training day within the active program."""
    from gymops import db

    active = db.get_active_state()
    if not active or not active.get("program_id"):
        console.print(
            "[bright_red]Error:[/] No active program. Set one first with: [cyan]gymops select-program[/]"
        )
        raise typer.Exit(code=1)

    program_id = active["program_id"]
    p_days = db.get_program_days(program_id)
    target_day = None
    for d in p_days:
        if d.name.lower() == day_name.lower():
            target_day = d
            break

    if not target_day:
        console.print(f"[bright_red]Error:[/] Day '{day_name}' not found in the active program.")
        raise typer.Exit(code=1)

    db.set_active_day(target_day.id)
    console.print(
        f"Training day set to '[cyan]{target_day.name}[/]' [bold spring_green1]✓[/]"
    )
    console.print("[dim]Your logs today will be guided by this day's targets.[/dim]")


# ---------------------------------------------------------------------------
# gymops prs
# ---------------------------------------------------------------------------

@app.command()
def prs() -> None:
    """Display all personal records."""
    from gymops import db
    from rich.table import Table
    import rich.box as box

    all_prs = db.get_all_prs()

    if not all_prs:
        console.print("[dim]No personal records yet. Start logging workouts![/dim]")
        return

    table = Table(
        title="[gold1]🏆 Personal Records[/]",
        box=box.ROUNDED,
        border_style="gold1",
        show_lines=True,
    )
    table.add_column("Exercise", style="white")
    table.add_column("Max Weight (kg)", justify="right", style="cyan")
    table.add_column("Est. 1RM (kg)", justify="right", style="gold1")
    table.add_column("Date", style="dim")

    for pr in all_prs:
        table.add_row(
            pr.exercise_name,
            f"{pr.max_weight:.1f}",
            f"{pr.max_epley_1rm:.1f}",
            str(pr.timestamp)[:10],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# gymops history
# ---------------------------------------------------------------------------

@app.command()
def history(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Exercise name."),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of entries to show."),
) -> None:
    """View workout history for an exercise."""
    from gymops import db
    from rich.table import Table
    import rich.box as box

    try:
        logs = db.get_history(exercise, limit=limit)
    except ValueError as e:
        console.print(f"[bright_red]Error:[/] {e}")
        raise typer.Exit(code=1)

    if not logs:
        console.print(f"[dim]No history found for '{exercise}'.[/dim]")
        return

    table = Table(
        title=f"[cyan]📜 History — {logs[0].exercise_name}[/]",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Date", style="dim")
    table.add_column("Sets", justify="right")
    table.add_column("Reps", justify="right")
    table.add_column("Weight (kg)", justify="right", style="white")
    table.add_column("Est. 1RM (kg)", justify="right", style="gold1")

    for w in logs:
        table.add_row(
            str(w.timestamp)[:10],
            str(w.sets),
            str(w.reps),
            f"{w.weight:.1f}",
            f"{w.epley_1rm:.1f}",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# gymops stats
# ---------------------------------------------------------------------------

@app.command()
def stats(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Exercise name."),
) -> None:
    """Compare the last two sessions to measure progressive overload."""
    from gymops import db
    from rich.panel import Panel

    try:
        sessions = db.get_last_two_sessions(exercise)
    except ValueError as e:
        console.print(f"[bright_red]Error:[/] {e}")
        raise typer.Exit(code=1)

    if len(sessions) < 2:
        console.print(
            f"[dim]Not enough data for '{exercise}'. "
            "Log at least 2 sessions first.[/dim]"
        )
        return

    current, previous = sessions[0], sessions[1]
    diff_pct = ((current.epley_1rm - previous.epley_1rm) / previous.epley_1rm) * 100

    console.print(
        f"\n[cyan]📈 Progressive Overload Stats for:[/] [bold]{current.exercise_name}[/]\n"
    )
    console.print(
        f"Previous Session ({str(previous.timestamp)[:10]}):\n"
        f"  {previous.weight:.1f} kg x {previous.reps} reps  -->  "
        f"[dim]Est. 1RM: {previous.epley_1rm:.1f} kg[/]\n"
    )
    console.print(
        f"Current Session ({str(current.timestamp)[:10]}):\n"
        f"  {current.weight:.1f} kg x {current.reps} reps  -->  "
        f"[dim]Est. 1RM: {current.epley_1rm:.1f} kg[/]\n"
    )

    if diff_pct > 0:
        console.print(
            Panel(
                f"[bold green]💪 PROGRESSIVE OVERLOAD SUCCESS![/]\n"
                f"Estimated strength improved by [bold green]+{diff_pct:.2f}%[/] [bold green]▲[/]",
                border_style="green",
            )
        )
    elif diff_pct == 0:
        console.print(
            Panel(
                f"[bold gold1]📊 PLATEAU DETECTED[/]\n"
                f"No change in estimated 1RM ([bold gold1]+0.00%[/]).\n"
                "[dim]Suggestion: Try increasing reps or adding 1-2.5 kg next time.[/dim]",
                border_style="gold1",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold bright_red]📉 STRENGTH DECREASE DETECTED[/]\n"
                f"Estimated 1RM dropped by [bold bright_red]{diff_pct:.2f}%[/] [bold bright_red]▼[/]\n"
                "[dim]This can be normal. Rest, nutrition, and sleep matter![/dim]",
                border_style="bright_red",
            )
        )


# ---------------------------------------------------------------------------
# gymops digest
# ---------------------------------------------------------------------------

@app.command()
def digest(
    days: int = typer.Option(7, "--days", help="Number of days to include in the digest."),
) -> None:
    """Generate the weekly CI Workout Digest Markdown report."""
    from gymops.report import generate_digest
    from rich.panel import Panel

    output_file = generate_digest(days=days)
    content = (
        f"[dim]File Name:[/]     [bold spring_green1]{output_file}[/]\n"
        f"[dim]Days Analyzed:[/] {days} days\n"
        f"[dim]Status:[/]        Written to disk [bold spring_green1]✓[/]"
    )
    console.print(
        Panel(content, title="[bold]📊 Digest Generated Successfully![/]", border_style="cyan")
    )
