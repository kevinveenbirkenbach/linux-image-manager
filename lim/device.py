"""Block-device selection and low-level device helpers."""

import stat as stat_module
from dataclasses import dataclass
from pathlib import Path

from lim import runner, ui
from lim.errors import LimError

SYS_BLOCK_PATH = Path("/sys/block")

PARTITION_TABLE_INFO = """\
##########################################################################################
Note on Partition Table Deletion:
---------------------------------------------
• MBR (Master Boot Record):
  - Typically occupies the first sector (512 bytes), i.e., 1 block.

• GPT (GUID Partition Table):
  - Uses a protective MBR (1 block), a GPT header (1 block),
    and usually a partition entry array that takes up about 32 blocks.
  - Total: approximately 34 blocks (assuming a 512-byte block size).

Recommendation: For deleting a GPT partition table, use a block size of 512 bytes
                and overwrite at least 34 blocks to ensure the entire table is cleared.
##########################################################################################"""


def optimal_blocksize(name: str, sys_block_path: Path = SYS_BLOCK_PATH) -> str:
    """64 * physical block size, or "4K" when the size cannot be read.

    See https://www.heise.de/ct/hotline/Optimale-Blockgroesse-fuer-dd-2056768.html
    """
    size_path = sys_block_path / name / "queue" / "physical_block_size"
    try:
        return str(64 * int(size_path.read_text().strip()))
    except (OSError, ValueError):
        return "4K"


@dataclass(frozen=True)
class Device:
    name: str  # e.g. "sda" or "mmcblk0"

    @property
    def path(self) -> str:
        return f"/dev/{self.name}"

    @property
    def optimal_blocksize(self) -> str:
        return optimal_blocksize(self.name)

    def partition(self, number: int) -> str:
        """/dev/sda -> /dev/sda1, /dev/mmcblk0 -> /dev/mmcblk0p1."""
        if self.name[-1].isdigit():
            return f"{self.path}p{number}"
        return f"{self.path}{number}"


def is_block_device(path: str) -> bool:
    try:
        return stat_module.S_ISBLK(Path(path).stat().st_mode)
    except OSError:
        return False


def select_device() -> Device:
    ui.info("Available devices:")
    runner.run(["lsblk", "-o", "NAME,SIZE,TYPE,MODEL"], check=False)
    name = ui.ask("Please type in the name of the device: /dev/")
    device = Device(name)
    if not name or not is_block_device(device.path):
        raise LimError(f"{device.path} is not a valid device.")
    ui.info(f"Device path set to: {device.path}")
    ui.info(f"Optimal blocksize set to: {device.optimal_blocksize}")
    return device


def overwrite_device(device: Device) -> None:
    """Optionally overwrite the device (or its first blocks) with zeros."""
    print(PARTITION_TABLE_INFO)
    answer = ui.ask(
        f"Should {device.path} be overwritten with zeros before copying? (y/N/block count)"
    )
    if answer == "y":
        ui.info("Overwriting entire device...")
        runner.run(
            [
                "dd",
                "if=/dev/zero",
                f"of={device.path}",
                f"bs={device.optimal_blocksize}",
                "status=progress",
            ],
            sudo=True,
            error_msg=f"Overwriting {device.path} failed.",
        )
        runner.sync_disks()
    elif answer in ("", "N"):
        ui.info("Skipping Overwriting...")
    elif answer.isdigit():
        ui.info(f"Overwriting {answer} blocks...")
        runner.run(
            [
                "dd",
                "if=/dev/zero",
                f"of={device.path}",
                f"bs={device.optimal_blocksize}",
                f"count={answer}",
                "status=progress",
            ],
            sudo=True,
            error_msg=f"Overwriting {device.path} failed.",
        )
        runner.sync_disks()
    else:
        raise LimError("Invalid input. Block count must be a number.")


def blkid_value(path: str, tag: str) -> str:
    """Return a blkid tag value ("TYPE", "UUID", ...) or "" when unavailable."""
    return runner.output(["blkid", path, "-s", tag, "-o", "value"], sudo=True, check=False)


def is_mounted(path_fragment: str) -> bool:
    """Whether any current mount line contains the given fragment."""
    mounts = runner.output(["mount"], check=False)
    return any(path_fragment in line for line in mounts.splitlines())
