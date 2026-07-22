"""Ensure the host can chroot into a foreign-architecture image (qemu binfmt)."""

import platform
import shutil
from pathlib import Path

from lim import runner, ui
from lim.errors import LimError

# Building natively needs no qemu; on these the chroot runs directly.
_NATIVE_ARM = ("aarch64", "armv7l", "armv6l", "arm64")

# Repo-based installs only; AUR helpers refuse to run from this root process.
_BINFMT_INSTALLERS = {
    "apt-get": ["apt-get", "install", "-y", "qemu-user-static", "binfmt-support"],
    "dnf": ["dnf", "install", "-y", "qemu-user-static"],
    "zypper": ["zypper", "--non-interactive", "install", "qemu-linux-user"],
    "pacman": ["pacman", "-S", "--needed", "--noconfirm", "qemu-user-static-binfmt"],
}


def _entry_enabled(entry: Path) -> bool:
    try:
        return "enabled" in entry.read_text()
    except OSError:
        return False


def qemu_binfmt_enabled() -> bool:
    binfmt = Path("/proc/sys/fs/binfmt_misc")
    return binfmt.is_dir() and any(_entry_enabled(e) for e in binfmt.glob("qemu-*"))


def auto_enable() -> bool:
    """Install qemu-user-static via the host package manager and register binfmt."""
    command = next((cmd for tool, cmd in _BINFMT_INSTALLERS.items() if shutil.which(tool)), None)
    if command is None:
        ui.warning("No supported host package manager found (apt-get/dnf/zypper/pacman).")
        return False
    runner.run(command, sudo=True, check=False)
    runner.run(["systemctl", "restart", "systemd-binfmt"], sudo=True, check=False)
    return qemu_binfmt_enabled()


def ensure_ready() -> None:
    """Make foreign-arch chroot work, or fail with actionable guidance.

    Called before the target is erased, so a host that cannot run the image's
    binaries aborts early instead of mid-build with a cryptic "Exec format error".
    """
    if platform.machine() in _NATIVE_ARM:
        return
    if qemu_binfmt_enabled():
        ui.info("Cross-architecture build: qemu binfmt handlers are registered.")
        return
    ui.warning(
        f"Cross-architecture build: this host ({platform.machine()}) cannot run the "
        "image's ARM binaries in chroot yet."
    )
    if ui.confirm("Install qemu-user-static and register binfmt now?"):
        if auto_enable():
            ui.success("qemu binfmt handlers registered.")
            return
        ui.warning("Automatic setup did not register a handler.")
    raise LimError(
        "Cross-architecture chroot is not available. Install qemu-user-static + binfmt "
        "manually, or build on the target itself (e.g. the Pi booted from USB).\n"
        "  Arch/Manjaro : qemu-user-static + qemu-user-static-binfmt (AUR), "
        "then: sudo systemctl restart systemd-binfmt\n"
        "  Debian/Ubuntu: sudo apt install qemu-user-static binfmt-support"
    )
