"""Encrypted Btrfs RAID1 across two drives.

See https://balaskas.gr/btrfs/raid1.html and
https://mutschler.eu/linux/install-guides/ubuntu-btrfs-raid1/
"""

from lim import luks, runner, ui
from lim.storage.common import StorageTarget, select_storage_target


def _select_pair() -> tuple[StorageTarget, StorageTarget]:
    ui.info("RAID1 partition 1...")
    first = select_storage_target()
    ui.info("RAID1 partition 2...")
    second = select_storage_target()
    return first, second


def setup() -> None:
    first, second = _select_pair()

    ui.info(f"Encrypting {first.device.path}...")
    runner.run(["cryptsetup", "luksFormat", first.device.path], sudo=True)
    ui.info(f"Encrypting {second.device.path}...")
    runner.run(["cryptsetup", "luksFormat", second.device.path], sudo=True)

    runner.run(["cryptsetup", "luksOpen", first.device.path, first.mapper_name], sudo=True)
    runner.run(["cryptsetup", "luksOpen", second.device.path, second.mapper_name], sudo=True)
    runner.run(["cryptsetup", "status", first.mapper_path], sudo=True)
    runner.run(["cryptsetup", "status", second.mapper_path], sudo=True)

    runner.run(
        [
            "mkfs.btrfs",
            "-m",
            "raid1",
            "-d",
            "raid1",
            first.mapper_path,
            second.mapper_path,
        ],
        sudo=True,
    )

    ui.success("Encryption successfull :)")


def _show_luks_devices() -> None:
    for name in runner.output(["lsblk", "-dno", "NAME"], check=False).split():
        if runner.succeeds(["cryptsetup", "isLuks", f"/dev/{name}"], sudo=True):
            ui.info(f"/dev/{name} is a LUKS encrypted storage device.")


def mount_on_boot() -> None:
    ui.info("Activate Automount raid1 encrypted storages...")
    _show_luks_devices()

    first, second = _select_pair()

    luks.create_luks_key_and_update_crypttab(first.mapper_name, first.device.path)
    ui.info(f'Creating mount folder under "{first.mount_path}"...')
    runner.run(["mkdir", "-vp", first.mount_path], sudo=True)
    luks.create_luks_key_and_update_crypttab(second.mapper_name, second.device.path)
    luks.update_fstab(first.mapper_path, first.mount_path)

    ui.success("Installation finished. Please restart :)")
