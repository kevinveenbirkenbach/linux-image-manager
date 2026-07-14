"""Process-level helpers: privilege handling and user resolution."""

import getpass
import os
import sys
from pathlib import Path

from lim import ui


def is_root() -> bool:
    return os.geteuid() == 0


def ensure_root() -> None:
    """Re-execute the current command with sudo when not running as root."""
    if is_root():
        return
    ui.info("Root privileges required. Re-executing with sudo...")
    script = str(Path(sys.argv[0]).resolve())
    # Deliberate privilege escalation: replace this process with sudo.
    os.execvp("sudo", ["sudo", sys.executable, script, *sys.argv[1:]])  # noqa: S606


def real_user() -> str:
    """Return the invoking user, even when running under sudo."""
    return os.environ.get("SUDO_USER") or getpass.getuser()


def real_home() -> Path:
    """Home directory of the invoking user, even when running under sudo."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        return Path("/home") / sudo_user
    return Path.home()
