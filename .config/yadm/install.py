#!/usr/bin/env python3

import subprocess
import sys
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from threading import Thread
from typing import Annotated, BinaryIO, Iterable, Sequence

from rich import print
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from typer import Argument, Typer

cli = Typer(add_completion=False, pretty_exceptions_show_locals=False)


@dataclass
class CommandJob:
    """
    A job of commands to execute sequentially.
    """

    title: str
    commands: Sequence[Sequence[str]]
    finish_message: str


@cli.command()
def main(
    base_dir: Annotated[Path, Argument()] = Path(__file__).resolve().parent
) -> None:
    # TODO: ensure all install commands upgrade too
    jobs = get_requirements_install_jobs(base_dir / "requirements")

    ensure_sudo()
    print(
        f"Running {len(jobs)} jobs with {sum(len(job.commands) for job in jobs)} commands..."
    )
    run_jobs_display(jobs)

    print("[green]Done![/green]")


def execute(*args: str | PathLike) -> None:
    """
    Executes given command, checking its result.
    """
    subprocess.run(args, capture_output=True, check=True)


def execute_display(*args: str | PathLike, stdout: Text, stderr: Text) -> None:
    """
    Executes given command, checking its result.
    Displays its output to given `Text` objects.
    """

    def read_append(stream: BinaryIO, text: Text) -> None:
        while True:
            line = stream.readline()
            if not line:
                break
            text.append(line.decode())

    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_thread = Thread(target=read_append, args=(process.stdout, stdout))
    stderr_thread = Thread(target=read_append, args=(process.stderr, stderr))

    stdout_thread.start()
    stderr_thread.start()
    try:
        process.wait()
    except:
        process.terminate()
        raise
    finally:
        stdout_thread.join()
        stderr_thread.join()

    if process.returncode:
        raise subprocess.CalledProcessError(
            returncode=process.returncode,
            cmd=process.args,
            output=stdout.plain,
            stderr=stderr.plain,
        )


def run_jobs_display(jobs: Sequence[CommandJob]) -> None:
    """
    Runs given jobs, displaying progress.
    """
    max_job_title_length = max(len(job.title) for job in jobs)

    # Display job progress
    progress = Progress(
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(show_speed=True),
        TimeElapsedColumn(),
        "{task.description}",
    )
    task_id_to_job = {
        progress.add_task(job.title, total=len(job.commands)): job for job in jobs
    }
    total_task_id = progress.add_task(
        description="Total",
        total=int(sum(task.total for task in progress.tasks)),
    )

    # Display current command output
    stdout_text = Text()
    stderr_text = Text()

    # Format displays nicely in tables
    progress_table = Table.grid(expand=True)
    progress_table.add_row(
        Panel(
            progress,
            title="[b]Jobs",
            border_style="white",
            padding=(1, 2),
        ),
    )
    output_table = Table.grid(expand=True)
    output_table.add_column(ratio=1)
    output_table.add_column(ratio=1)
    output_table.add_row(
        Panel(
            stdout_text,
            title="[b]stdout",
            border_style="green",
            padding=(2, 2),
        ),
        Panel(
            stderr_text,
            title="[b]stderr",
            border_style="red",
            padding=(2, 2),
        ),
    )
    progress_table.add_row(output_table)

    # Display progress live
    with Live(progress_table):
        while not progress.finished:
            # Get current job and command
            current_task = next(
                task
                for task in progress.tasks
                if task.id != total_task_id and not task.finished
            )
            current_job = task_id_to_job[current_task.id]
            current_command = current_job.commands[current_task.completed]

            # Update status
            base_description = current_job.title.ljust(max_job_title_length + 2)
            description = base_description + "[yellow]" + " ".join(current_command)
            progress.update(current_task.id, description=description)

            # Execute command
            execute_display(*current_command, stdout=stdout_text, stderr=stderr_text)
            stdout_text.set_length(0)
            stderr_text.set_length(0)

            # Update status
            progress.advance(current_task.id)
            if current_task.finished:
                description = base_description + "[green]" + current_job.finish_message
                progress.update(current_task.id, description=description)

            # Update total status
            progress.advance(total_task_id)


def ensure_sudo() -> None:
    """
    Ensures sudo password is cached.
    """
    print("Checking for `sudo` access (may request your password)...")
    try:
        execute("sudo", "-n", "true")
    except subprocess.CalledProcessError:
        execute("sudo", "true")


def read_requirements(file: Path) -> list[str]:
    """
    Reads a requirements list from given file.
    """
    return [r for r in file.read_text().splitlines() if not r.strip().startswith("#")]


def get_requirements_install_jobs(requirements_dir: Path) -> list[CommandJob]:
    """
    Returns a list of jobs to install all requirements from given directory.
    """
    REQUIREMENTS = (
        ("apt", "apt.txt", get_apt_requirement_install_commands),
        ("brew", "brew.txt", get_brew_requirement_install_commands),
        ("pip", "pip.txt", get_pip_requirement_install_commands),
        ("snap", "snap.txt", get_snap_requirement_install_commands),
    )

    jobs: list[CommandJob] = list()
    for package_manager, filename, get_cmds_func in REQUIREMENTS:
        path = requirements_dir / filename
        if not path.is_file():
            print(f"[yellow]{path} not found - skipping {package_manager} requirements")
            continue

        requirements = read_requirements(path)

        jobs.append(
            CommandJob(
                title=package_manager,
                commands=get_cmds_func(requirements),
                finish_message=(
                    f"{len(requirements)} package"
                    + ("" if len(requirements) == 1 else "s")
                    + " installed"
                ),
            )
        )

    return jobs


def get_apt_requirement_install_commands(
    requirements: Iterable[str],
) -> list[list[str]]:
    """
    Returns a list of commands that install given apt requirements.
    """
    commands = [["sudo", "apt", "update", "-y"], ["sudo", "apt", "upgrade", "-y"]]
    commands.extend(["sudo", "apt", "install", "-y", r] for r in requirements)
    return commands


def get_brew_requirement_install_commands(
    requirements: Iterable[str],
) -> list[list[str]]:
    """
    Returns a list of commands that install given brew requirements.
    """
    commands = [["brew", "update"]]
    commands.extend(["brew", "install", r] for r in requirements)
    return commands


def get_pip_requirement_install_commands(
    requirements: Iterable[str],
) -> list[list[str]]:
    """
    Returns a list of commands that install given pip requirements.
    """
    return [[sys.executable, "-m", "pip", "install", "-U", r] for r in requirements]


def get_snap_requirement_install_commands(
    requirements: Iterable[str],
) -> list[list[str]]:
    """
    Returns a list of commands that install given snap requirements.
    """
    commands = [["sudo", "snap", "refresh"]]
    commands.extend(["sudo", "snap", "install", "--classic", r] for r in requirements)
    return commands


if __name__ == "__main__":
    cli()
