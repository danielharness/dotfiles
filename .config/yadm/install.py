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
    commands: list[list[str]]
    finish_message: str


@cli.command()
def main(
    base_dir: Annotated[Path, Argument()] = Path(__file__).resolve().parent
) -> None:
    jobs: list[CommandJob] = get_requirements_install_jobs(
        base_dir / "requirements"
    ) + [
        get_oh_my_zsh_install_job(),
        get_terminal_theme_install_job(),
        get_zellij_plugins_install_job(),
        get_yadm_ignore_job(),
    ]

    ensure_sudo()
    run_jobs_display(jobs)

    print("[green]Done![/green]")


def execute(*args: str | PathLike) -> str:
    """
    Executes given command, erroring if it fails.
    Returns its output.
    """
    result = subprocess.run(args, capture_output=True, check=True)
    output = result.stdout.decode()
    if output.endswith("\n"):
        output = output[:-1]
    return output


def execute_display(*args: str | PathLike, stdout: Text, stderr: Text) -> None:
    """
    Executes given command, erroring if it fails.
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
    stdout_text = Text(overflow="fold")
    stderr_text = Text(overflow="fold")

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
    Returns a list of jobs that install all requirements from given directory.
    """
    REQUIREMENTS = (
        ("apt", "apt.txt", get_apt_requirement_install_commands),
        ("brew", "brew.txt", get_brew_requirement_install_commands),
        ("pip", "pip.txt", get_pip_requirement_install_commands),
        ("snap", "snap.txt", get_snap_requirement_install_commands),
    )

    jobs: list[CommandJob] = []
    for package_manager, filename, get_cmds_func in REQUIREMENTS:
        path = requirements_dir / filename
        if not path.is_file():
            print(f"[yellow]{path} not found - skipping {package_manager} requirements")
            continue

        requirements = read_requirements(path)

        jobs.append(
            CommandJob(
                title=f"{package_manager.title()} requirements",
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
    commands = [
        ["sudo", "apt-get", "update", "-y"],
        ["sudo", "apt-get", "upgrade", "-y"],
    ]
    commands.extend(
        [
            "sudo",
            "apt-get",
            "install",
            "-y",
            "-qq",
            "-o=Dpkg::Use-Pty=0",
            r,
        ]
        for r in requirements
    )
    return commands


def get_brew_requirement_install_commands(
    requirements: Iterable[str],
) -> list[list[str]]:
    """
    Returns a list of commands that install given brew requirements.
    """
    commands = [
        # Install brew
        [
            "bash",
            "-c",
            (
                'bash -c "'
                "export NONINTERACTIVE=1;"
                " $(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                '"'
            ),
        ],
        # Upgrade brew
        ["/home/linuxbrew/.linuxbrew/bin/brew", "upgrade"],
    ]
    # Install packages
    commands.extend(
        ["/home/linuxbrew/.linuxbrew/bin/brew", "install", r] for r in requirements
    )
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


def get_oh_my_zsh_install_job() -> CommandJob:
    """
    Returns a job that installs oh-my-zsh and sets zsh as the default shell.
    """
    commands: list[list[str]] = []

    # Clone oh-my-zsh
    install_dir = Path.home() / ".oh-my-zsh"
    if not install_dir.exists():
        commands.append(
            ["git", "clone", "https://github.com/ohmyzsh/ohmyzsh.git", str(install_dir)]
        )

    # Set zsh as default shell
    commands.append(["sudo", "chsh", "-s", execute("which", "zsh"), execute("whoami")])

    # Update oh-my-zsh
    commands.append(["zsh", str(install_dir / "tools" / "upgrade.sh")])

    return CommandJob(
        title="Oh-my-zsh setup", commands=commands, finish_message="Installed"
    )


def get_terminal_theme_install_job() -> CommandJob:
    """
    Returns a job that installs the terminal theme.
    """
    PROFILES_KEY = "/org/gnome/terminal/legacy/profiles:"

    profile_slug = execute("dconf", "read", f"{PROFILES_KEY}/default").replace("'", "")
    profile_key = f"{PROFILES_KEY}/:{profile_slug}"

    def dset(key: str, value: str) -> list[str]:
        return ["dconf", "write", f"{profile_key}/{key}", value]

    commands = [
        # Refresh font cache
        ["fc-cache", "-fv"],
        # Set theme: "hyper-snazzy" from https://github.com/tobark/hyper-snazzy-gnome-terminal
        dset("visible-name", "'hyper-snazzy'"),
        dset(
            "palette",
            "['#282a36', '#ff5c57', '#5af78e', '#f3f99d', '#57c7ff', '#ff6ac1', '#9aedfe', '#f1f1f0', '#686868', '#ff5c57', '#5af78e', '#f3f99d', '#57c7ff', '#ff6ac1', '#9aedfe', '#eff0eb']",
        ),
        dset("background-color", "'#282a36'"),
        dset("foreground-color", "'#eff0eb'"),
        dset("bold-color", "'#eff0eb'"),
        dset("bold-color-same-as-fg", "true"),
        dset("use-theme-colors", "false"),
        dset("use-theme-background", "false"),
        # use FiraCode Nerd Font
        dset("use-system-font", "false"),
        dset("font", "'FiraCode Nerd Font Mono 12'"),
        # Wait for screen refresh
        ["sleep", "1"],
    ]

    return CommandJob(
        title="Terminal theme", commands=commands, finish_message="Installed"
    )


def get_zellij_plugins_install_job() -> CommandJob:
    """
    Returns a job that installs zellij plugins.
    """
    PLUGINS = [
        "https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm",
    ]

    plugins_dir = Path.home() / ".config" / "zellij" / "plugins"

    # Create plugin directory
    commands = [["mkdir", "-p", str(plugins_dir)]]

    # Install plugins
    commands.extend(
        [
            "wget",
            "-P",
            str(plugins_dir),
            p,
        ]
        for p in PLUGINS
    )

    return CommandJob(
        title="Zellij plugins",
        commands=commands,
        finish_message=(
            f"{len(PLUGINS)} plugin" + ("" if len(PLUGINS) == 1 else "s") + " installed"
        ),
    )


def get_yadm_ignore_job() -> CommandJob:
    """
    Returns a job that makes yadm ignore certain files.
    """
    FILES = [
        Path.home() / ".gitconfig",
    ]

    return CommandJob(
        title="Yadm ignore",
        commands=[
            ["yadm", "update-index", "--assume-unchanged", str(f)] for f in FILES
        ],
        finish_message=(
            f"{len(FILES)} file" + ("" if len(FILES) == 1 else "s") + " ignored"
        ),
    )


if __name__ == "__main__":
    cli()
