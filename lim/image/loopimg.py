"""Attach a stock disk image as a loop device to read its partitions."""

from pathlib import Path

from lim import runner, ui
from lim.errors import LimError


def attach(image_path: Path) -> str:
    """Attach the image via losetup with partition scanning; return /dev/loopN."""
    ui.info(f"Attaching {image_path} as a loop device...")
    loop = runner.output(
        ["losetup", "-Pf", "--show", str(image_path)],
        sudo=True,
        error_msg=f"Attaching {image_path} as a loop device failed.",
    ).strip()
    if not loop:
        raise LimError(f"losetup returned no device for {image_path}.")
    return loop


def detach(loop: str) -> None:
    runner.run(["losetup", "-d", loop], sudo=True, check=False)


def partition(loop: str, number: int) -> str:
    """/dev/loop0 -> /dev/loop0p1 (losetup -P names partitions with a p suffix)."""
    return f"{loop}p{number}"
