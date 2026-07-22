"""Single-drive LUKS + Btrfs storage: setup, mount, umount, mount-on-boot."""

from lim import device as device_module
from lim import luks, runner, system, ui
from lim.storage.common import select_storage_target

# fdisk answer sequences; empty lines accept the defaults.
CREATE_GPT_TABLE_INPUT = "g\nw\n"
CREATE_PARTITION_INPUT = "n\n\n\n\np\nw\n"


def setup() -> None:
    print("Setups disk encryption")
    target = select_storage_target()

    device_module.overwrite_device(target.device)

    ui.info("Creating new GPT partition table...")
    runner.run(
        ["fdisk", "--wipe", "always", target.device.path],
        input_text=CREATE_GPT_TABLE_INPUT,
        sudo=True,
    )
    ui.info("Creating partition table...")
    runner.run(
        ["fdisk", "--wipe", "always", target.device.path],
        input_text=CREATE_PARTITION_INPUT,
        sudo=True,
    )

    ui.info(f"Encrypt {target.device.path}...")
    runner.run(["cryptsetup", "-v", "-y", "luksFormat", target.partition_path], sudo=True)

    ui.info("Unlock partition...")
    runner.run(["cryptsetup", "luksOpen", target.partition_path, target.mapper_name], sudo=True)

    ui.info("Create btrfs file system...")
    runner.run(["mkfs.btrfs", target.mapper_path], sudo=True)

    ui.info(f'Creating mount folder under "{target.mount_path}"...')
    runner.run(["mkdir", "-p", target.mount_path], sudo=True)

    ui.info("Mount partition...")
    runner.run(["mount", target.mapper_path, target.mount_path], sudo=True)

    user = system.real_user()
    ui.info("Own partition by user...")
    runner.run(["chown", "-R", f"{user}:{user}", target.mount_path], sudo=True)

    ui.success("Encryption successfull :)")


def mount() -> None:
    print("Mounts encrypted storages")
    target = select_storage_target()

    ui.info("Unlock partition...")
    runner.run(["cryptsetup", "luksOpen", target.partition_path, target.mapper_name], sudo=True)

    ui.info("Mount partition...")
    runner.run(["mount", target.mapper_path, target.mount_path], sudo=True)

    ui.success("Mounting successfull :)")


def umount() -> None:
    print("Unmount encrypted storages")
    target = select_storage_target()

    ui.info(f"Unmount {target.mapper_path}...")
    runner.run(["umount", target.mapper_path], sudo=True)
    runner.run(["cryptsetup", "luksClose", target.mapper_name], sudo=True)

    ui.success("Successfull :)")


def mount_on_boot() -> None:
    print("Automount encrypted storages")
    target = select_storage_target()

    luks.create_luks_key_and_update_crypttab(target.mapper_name, target.partition_path)
    luks.update_fstab(target.mapper_path, target.mount_path)

    ui.success("Installation finished. Please restart :)")
