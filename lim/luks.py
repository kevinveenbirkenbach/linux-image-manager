"""LUKS key management plus crypttab/fstab bookkeeping."""

import re
from pathlib import Path

from lim import fsutil, runner, ui
from lim.errors import LimError

LUKS_KEY_DIRECTORY = Path("/etc/luks-keys")
CRYPTTAB_PATH = Path("/etc/crypttab")
FSTAB_PATH = Path("/etc/fstab")


def luks_uuid(partition_path: str) -> str:
    dump = runner.output(["cryptsetup", "luksDump", partition_path], sudo=True)
    match = re.search(r"UUID:\s*(\S+)", dump)
    if not match:
        raise LimError(f"Could not read LUKS UUID of {partition_path}.")
    return match.group(1)


def create_luks_key_and_update_crypttab(
    mapper_name: str,
    partition_path: str,
    *,
    key_directory: Path = LUKS_KEY_DIRECTORY,
    crypttab_path: Path = CRYPTTAB_PATH,
) -> None:
    """Generate a random keyfile, register it with LUKS and /etc/crypttab."""
    ui.info("Creating luks-key-directory...")
    key_directory.mkdir(parents=True, exist_ok=True)
    secret_key_path = key_directory / f"{mapper_name}.keyfile"
    ui.info(f"Generate secret key under: {secret_key_path}")
    if secret_key_path.exists():
        ui.warning("File already exists. Overwriting!")
    runner.run(
        ["dd", "if=/dev/urandom", f"of={secret_key_path}", "bs=512", "count=8"],
        sudo=True,
    )
    runner.sync_disks()

    ui.info("Opening and closing device to verify that everything works fine...")
    closed = runner.run(["cryptsetup", "-v", "luksClose", mapper_name], sudo=True, check=False)
    if closed.returncode != 0:
        ui.info(f"No need to luksClose {mapper_name}. Device isn't open.")
    runner.run(["cryptsetup", "luksAddKey", partition_path, str(secret_key_path)], sudo=True)
    runner.run(
        [
            "cryptsetup",
            "-v",
            "luksOpen",
            partition_path,
            mapper_name,
            f"--key-file={secret_key_path}",
        ],
        sudo=True,
    )
    runner.run(["cryptsetup", "-v", "luksClose", mapper_name], sudo=True)

    ui.info("Reading UUID...")
    uuid = luks_uuid(partition_path)
    entry = f"{mapper_name} UUID={uuid} {secret_key_path} luks"
    ui.info("Adding crypttab entry...")
    fsutil.ensure_line_in_file(entry, crypttab_path)
    ui.info(f"The file {crypttab_path} contains now the following:")
    print(crypttab_path.read_text())


def update_fstab(mapper_path: str, mount_path: str, *, fstab_path: Path = FSTAB_PATH) -> None:
    entry = f"{mapper_path} {mount_path} btrfs   defaults   0       2"
    ui.info("Adding fstab entry...")
    fsutil.ensure_line_in_file(entry, fstab_path)
    ui.info(f"The file {fstab_path} contains now the following:")
    print(fstab_path.read_text())
