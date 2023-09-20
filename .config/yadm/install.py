#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path
from typing import Annotated, AnyStr, Iterable, Sequence

import typer
from rich import print
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

BASE_DIR = Path(__file__).resolve().parent


def main(
    base_dir: Annotated[Path, typer.Argument(help="Base directory")] = BASE_DIR
) -> None:
    try:
        # TODO: ensure they all upgrade too
        ensure_sudo()
        install_requirements(base_dir / "requirements")
        print("[green]Done![/green]")
    except subprocess.CalledProcessError as e:
        print_called_process_error(e)
        raise SystemExit(1)


def execute(*args: str | Path, input: AnyStr | None = None) -> None:
    """
    Executes given command, checking its result.
    """
    subprocess.run(args, capture_output=True, check=True, input=input)


def print_called_process_error(error: subprocess.CalledProcessError) -> None:
    """
    Nicely prints given error.
    """
    cmd = error.cmd if isinstance(error.cmd, str) else " ".join(error.cmd)
    print(f"Command failed: [yellow]{cmd}[/yellow]")
    if error.stdout:
        stdout: str = error.stdout.decode()
        print_end = "" if stdout.endswith("\n") else "\n"
        print(f"[purple]{stdout}[/purple]", end=print_end)
    if error.stderr:
        stderr: str = error.stderr.decode()
        print_end = "" if stderr.endswith("\n") else "\n"
        print(f"[red]{error.stderr.decode()}[/red]", end=print_end)


def ensure_sudo() -> None:
    """
    Ensures sudo password is cached.
    """
    print("Checking for `sudo` access (may request your password)...")
    try:
        execute("sudo", "-n", "true")
    except subprocess.CalledProcessError:
        execute("sudo", "true")


def track_commands(
    commands: Sequence[Sequence[str]],
    *,
    finished_message: str = "Done!",
) -> Iterable[Sequence[str]]:
    """
    Tracks progress by iterating over given command sequence.
    """
    with Progress(
        BarColumn(),
        TaskProgressColumn(show_speed=True),
        TimeRemainingColumn(elapsed_when_finished=True),
        TextColumn("{task.description}"),
    ) as progress:
        task_id = progress.add_task("Starting...")
        for command in progress.track(commands, task_id=task_id):
            progress.update(
                task_id,
                description=f"[grey53]{' '.join(command)}[/grey53]",
            )
            yield command
        progress.update(task_id, description=finished_message)


def install_requirements(requirements_dir: Path) -> None:
    """
    Installs all requirements from given directory.
    """
    requirements = {
        "apt.txt": get_apt_requirement_install_commands,
        "brew.txt": get_brew_requirement_install_commands,
        "pip.txt": get_pip_requirement_install_commands,
        "snap.txt": get_snap_requirement_install_commands,
    }

    print("Installing requirements...")

    for requirements_file, get_install_commands_function in requirements.items():
        path = requirements_dir / requirements_file
        if path.is_file():
            print(f"Installing from: [yellow]{requirements_file}[/yellow]")

            requirements = [
                r
                for r in path.read_text().splitlines()
                if not r.strip().startswith("#")
            ]

            finished_message = (
                "[green]"
                + f"{len(requirements)} package"
                + ("" if len(requirements) == 1 else "s")
                + " installed"
                + "[/green]"
            )

            for command in track_commands(
                get_install_commands_function(requirements),
                finished_message=finished_message,
            ):
                execute(*command)

    print("Installed requirements.")


def get_apt_requirement_install_commands(
    requirements: Sequence[str],
) -> list[Sequence[str]]:
    """
    Returns a list of commands that install given apt requirements.
    """
    commands = [("sudo", "apt", "update")]
    commands.extend(("sudo", "apt", "install", r) for r in requirements)
    return commands


def get_brew_requirement_install_commands(
    requirements: Sequence[str],
) -> list[Sequence[str]]:
    """
    Returns a list of commands that install given brew requirements.
    """
    commands = [("brew", "update")]
    commands.extend(("brew", "install", r) for r in requirements)
    return commands


def get_pip_requirement_install_commands(
    requirements: Sequence[str],
) -> list[Sequence[str]]:
    """
    Returns a list of commands that install given pip requirements.
    """
    return [(sys.executable, "-m", "pip", "install", "-U", r) for r in requirements]


def get_snap_requirement_install_commands(
    requirements: Sequence[str],
) -> list[Sequence[str]]:
    """
    Returns a list of commands that install given snap requirements.
    """
    commands = [("sudo", "snap", "refresh")]
    commands.extend(("sudo", "snap", "install", "--classic", r) for r in requirements)
    return commands


if __name__ == "__main__":
    typer.run(main)
