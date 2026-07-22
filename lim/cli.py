"""Command line interface: `lim --type <command>`."""

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass

from lim import system, ui
from lim.data import crypt, sync
from lim.errors import LimError
from lim.image import backup, chroot
from lim.image import setup as image_setup
from lim.image import unlock as image_unlock
from lim.image import wizard as image_wizard
from lim.storage import raid1, single_drive


@dataclass(frozen=True)
class Command:
    func: Callable[[], None]
    description: str
    needs_root: bool


COMMANDS: dict[str, Command] = {
    "image": Command(
        image_setup.run_setup,
        "Linux Image Setup:\n"
        "  - Creates partitions and formats them.\n"
        "  - Transfers the Linux image file to the device.\n"
        "  - Configures boot and root partitions.",
        needs_root=True,
    ),
    "guided": Command(
        image_wizard.run_guided,
        "Guided Encrypted Linux Image Setup (default command):\n"
        "  - Walks through flashing a Linux image (Arch, Raspberry Pi OS, ...) onto a device.\n"
        "  - Encrypts the root with LUKS and enables remote unlock over Tor.",
        needs_root=True,
    ),
    "remote-unlock": Command(
        image_unlock.remote_unlock,
        "Remote LUKS Boot Unlock:\n"
        "  - Reaches a waiting initramfs over Tor (onion) or plain SSH.\n"
        "  - Runs cryptroot-unlock or presents the passphrase prompt.",
        needs_root=False,
    ),
    "single": Command(
        single_drive.setup,
        "Single Drive Encryption Setup:\n"
        "  - Sets up disk encryption using LUKS on one drive.\n"
        "  - Configures a Btrfs file system for secure storage.",
        needs_root=True,
    ),
    "raid1": Command(
        raid1.setup,
        "RAID1 Encryption Setup:\n"
        "  - Configures a virtual RAID1 with two drives.\n"
        "  - Uses LUKS encryption and a Btrfs RAID1 file system for redundancy.",
        needs_root=True,
    ),
    "backup": Command(
        backup.run_backup,
        "Backup Image Setup:\n"
        "  - Creates an image backup from a memory device to a file.\n"
        "  - Uses dd to transfer the image from the specified device to an image file.",
        needs_root=True,
    ),
    "chroot": Command(
        chroot.run_chroot,
        "Chroot Environment Setup:\n"
        "  - Mounts partitions and configures the chroot environment for a Linux image.\n"
        "  - Provides a shell within the Linux image for system maintenance.",
        needs_root=True,
    ),
    "mount": Command(
        single_drive.mount,
        "Mount Encrypted Storage:\n  - Unlocks a LUKS partition and mounts it.",
        needs_root=True,
    ),
    "umount": Command(
        single_drive.umount,
        "Unmount Encrypted Storage:\n  - Unmounts a LUKS partition and closes the mapper.",
        needs_root=True,
    ),
    "single-boot": Command(
        single_drive.mount_on_boot,
        "Single Drive Automount Setup:\n"
        "  - Creates a LUKS keyfile and registers it in crypttab and fstab.",
        needs_root=True,
    ),
    "raid1-boot": Command(
        raid1.mount_on_boot,
        "RAID1 Automount Setup:\n"
        "  - Creates LUKS keyfiles for both drives and registers them in crypttab/fstab.",
        needs_root=True,
    ),
    "unlock": Command(
        crypt.unlock,
        "Unlock Data:\n  - Decrypts the encfs data store into the decrypted folder.",
        needs_root=False,
    ),
    "lock": Command(
        crypt.lock,
        "Lock Data:\n  - Unmounts the decrypted encfs folder.",
        needs_root=False,
    ),
    "import": Command(
        sync.import_from_system,
        "Import Data:\n  - Copies personal data from the system into the encrypted store.",
        needs_root=False,
    ),
    "export": Command(
        sync.export_to_system,
        "Export Data:\n  - Copies personal data from the encrypted store back to the system.",
        needs_root=False,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    epilog_lines = ["Available script types:"]
    epilog_lines += [
        f"  {name:<12} - {command.description.splitlines()[0].rstrip(':')}"
        for name, command in COMMANDS.items()
    ]
    parser = argparse.ArgumentParser(
        prog="lim",
        description="Linux Image Manager — manages Linux images and encrypted storage.",
        epilog="\n".join(epilog_lines),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type",
        default="guided",
        choices=list(COMMANDS.keys()),
        help="Command to execute (default: guided).",
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Automatically confirm execution without prompting the user.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    command = COMMANDS[args.type]

    if command.needs_root:
        system.ensure_root()

    ui.header()
    ui.info(f"Selected command: {args.type}")
    ui.info("Description:")
    print(command.description)

    try:
        if not args.auto_confirm:
            input("Press Enter to execute or Ctrl+C to cancel...")
        command.func()
    except LimError as exc:
        ui.error(f"{exc} -> Leaving program.")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        ui.error("Execution aborted by user.")
        sys.exit(1)
