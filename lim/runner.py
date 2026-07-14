"""Thin wrapper around subprocess for all external commands.

Every module calls external tools through this module so tests can
replace ``run``/``output``/``succeeds``/``pipeline`` with fakes.

Missing binaries never surface as tracebacks: actions (``check=True``,
``pipeline``) abort with a clear LimError, tolerated calls
(``check=False``, ``succeeds``) degrade to a warning plus shell-style
exit code 127.
"""

import os
import shlex
import subprocess

from lim import ui
from lim.errors import LimError

COMMAND_NOT_FOUND = 127


def _with_sudo(cmd: list[str], *, sudo: bool) -> list[str]:
    parts = [str(part) for part in cmd]
    if sudo and os.geteuid() != 0:
        return ["sudo", *parts]
    return parts


def _not_found_message(cmd: list[str]) -> str:
    return f"Command not found: {cmd[0]} — please install it."


def run(
    cmd: list[str],
    *,
    sudo: bool = False,
    input_text: str | None = None,
    check: bool = True,
    error_msg: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a command inheriting stdio so progress output stays visible."""
    cmd = _with_sudo(cmd, sudo=sudo)
    ui.info(f"Running: {shlex.join(cmd)}")
    try:
        result = subprocess.run(cmd, input=input_text, text=True, check=False)
    except FileNotFoundError:
        if check:
            raise LimError(error_msg or _not_found_message(cmd)) from None
        ui.warning(_not_found_message(cmd))
        return subprocess.CompletedProcess(cmd, COMMAND_NOT_FOUND)
    if check and result.returncode != 0:
        raise LimError(
            error_msg
            or f"Command failed with code {result.returncode}: {shlex.join(cmd)}"
        )
    return result


def output(
    cmd: list[str],
    *,
    sudo: bool = False,
    check: bool = True,
    error_msg: str | None = None,
) -> str:
    """Run a command and return its stripped stdout."""
    cmd = _with_sudo(cmd, sudo=sudo)
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        if check:
            raise LimError(error_msg or _not_found_message(cmd)) from None
        ui.warning(_not_found_message(cmd))
        return ""
    if check and result.returncode != 0:
        raise LimError(
            error_msg
            or f"Command failed with code {result.returncode}: {shlex.join(cmd)}"
            + (f"\n{result.stderr.strip()}" if result.stderr else "")
        )
    return result.stdout.strip()


def succeeds(cmd: list[str], *, sudo: bool = False) -> bool:
    """Run a command silently, report whether it exited with 0."""
    cmd = _with_sudo(cmd, sudo=sudo)
    try:
        return subprocess.run(cmd, capture_output=True, check=False).returncode == 0
    except FileNotFoundError:
        ui.warning(_not_found_message(cmd))
        return False


def pipeline(
    *cmds: list[str],
    sudo_last: bool = False,
    error_msg: str | None = None,
) -> None:
    """Run commands as a shell-style pipeline (cmd1 | cmd2 | ...)."""
    prepared = [
        _with_sudo(cmd, sudo=sudo_last and index == len(cmds) - 1)
        for index, cmd in enumerate(cmds)
    ]
    pretty = " | ".join(shlex.join(cmd) for cmd in prepared)
    ui.info(f"Running: {pretty}")
    processes: list[subprocess.Popen] = []
    previous_stdout = None
    try:
        for index, cmd in enumerate(prepared):
            last = index == len(prepared) - 1
            process = subprocess.Popen(
                cmd,
                stdin=previous_stdout,
                stdout=None if last else subprocess.PIPE,
            )
            if previous_stdout is not None:
                previous_stdout.close()
            previous_stdout = process.stdout
            processes.append(process)
    except FileNotFoundError as exc:
        if previous_stdout is not None:
            previous_stdout.close()
        for process in processes:
            process.kill()
            process.wait()
        raise LimError(f"Command not found: {exc.filename} — please install it.") from None
    for process in processes:
        process.wait()
    if any(process.returncode != 0 for process in processes):
        raise LimError(error_msg or f"Pipeline failed: {pretty}")


def sync_disks() -> None:
    run(["sync"])
