"""Download the selected image and transfer it onto the target device."""

from pathlib import Path

from lim import device as device_module
from lim import runner, ui
from lim.errors import LimError
from lim.image.plan import DEFAULT_BOOT_SIZE, ImagePlan
from lim.image.session import ImageSession


def download_image(plan: ImagePlan) -> None:
    if ui.confirm("Should the image download be forced?"):
        if plan.image_path.is_file():
            ui.info(f"Removing image {plan.image_path}.")
            plan.image_path.unlink()
        else:
            ui.info(
                "Forcing download wasn't neccessary. "
                f"File {plan.image_path} doesn't exist."
            )

    ui.info("Start Download procedure...")
    if plan.image_path.is_file():
        ui.info("Image exist local. Download skipped.")
        return
    ui.info(f'Image "{plan.image_name}" doesn\'t exist under local path "{plan.image_path}".')
    ui.info(f'Image "{plan.image_name}" gets downloaded from "{plan.download_url}"...')
    runner.run(
        ["wget", plan.download_url, "-O", str(plan.image_path)],
        error_msg=f'Download from "{plan.download_url}" failed.',
    )


def arch_partition_input(boot_size: str) -> str:
    """Fdisk answers: FAT32 boot partition of boot_size plus root partition."""
    return (
        "o\n"          # clear out any partitions on the drive
        "p\n"          # list partitions (should be empty)
        "n\np\n1\n\n"  # new primary partition 1, default start sector
        f"{boot_size}\n"
        "t\nc\n"       # set partition 1 to type W95 FAT32 (LBA)
        "n\np\n2\n\n\n"  # new primary partition 2 over the remaining space
        "w\n"          # write partition table
    )


def decompress_command(image_path: Path) -> list[str]:
    """Build the command that streams the raw image to stdout for dd."""
    suffix = image_path.suffix
    if suffix == ".zip":
        return ["unzip", "-p", str(image_path)]
    if suffix == ".gz":
        return ["gunzip", "-c", str(image_path)]
    if suffix == ".iso":
        return ["pv", str(image_path)]
    if suffix == ".xz":
        return ["unxz", "-c", str(image_path)]
    raise LimError(f'Image transfer for "{image_path.name}" is not supported yet!')


def _luks_format_root(plan: ImagePlan, session: ImageSession) -> None:
    luks_format = [
        "cryptsetup", "-v", "luksFormat",
        "-c", "aes-xts-plain64", "-s", "512", "-h", "sha512",
        "--use-random", "-i", "1000",
    ]
    if plan.luks_memory_cost:
        ui.info(
            f"Formating {session.root_partition_path} with LUKS "
            f"with --pbkdf-memory set to {plan.luks_memory_cost}"
        )
        luks_format += ["--pbkdf-memory", plan.luks_memory_cost]
    else:
        ui.info(f"Formating {session.root_partition_path} with LUKS")
    runner.run([*luks_format, session.root_partition_path], sudo=True)


def transfer_arch_image(plan: ImagePlan, session: ImageSession) -> None:
    boot_size = plan.boot_size or DEFAULT_BOOT_SIZE
    ui.info(f"The boot partition will be set to {boot_size}.")
    ui.info("Creating partitions...")
    runner.run(
        ["fdisk", session.device.path],
        input_text=arch_partition_input(boot_size),
        sudo=True,
    )

    ui.info("Format boot partition...")
    runner.run(["mkfs.vfat", session.boot_partition_path], sudo=True)

    if plan.encrypt_system:
        _luks_format_root(plan, session)
        session.decrypt_root()

    ui.info("Format root partition...")
    runner.run([f"mkfs.{plan.root_filesystem}", "-f", session.root_mapper_path], sudo=True)
    session.mount_partitions()

    ui.info("Root files will be transfered to device...")
    runner.run(
        ["bsdtar", "-xpf", str(plan.image_path), "-C", str(session.root_mount_path)],
        sudo=True,
    )
    runner.sync_disks()

    ui.info("Boot files will be transfered to device...")
    boot_source = session.root_mount_path / "boot"
    for entry in sorted(boot_source.iterdir()):
        runner.run(["mv", "-v", str(entry), str(session.boot_mount_path)], sudo=True)


def transfer_image(plan: ImagePlan, session: ImageSession) -> None:
    if ui.confirm(f"Should the partition table of {session.device.path} be deleted?"):
        ui.info("Deleting...")
        runner.run(["wipefs", "-a", session.device.path], sudo=True)
    else:
        ui.info("Skipping partition table deletion...")

    device_module.overwrite_device(session.device)

    ui.info("Starting image transfer...")
    if plan.distribution == "arch":
        transfer_arch_image(plan, session)
        return
    blocksize = session.device.optimal_blocksize
    ui.info(f"Transfering {plan.image_path.suffix} file...")
    runner.pipeline(
        decompress_command(plan.image_path),
        [
            "dd",
            f"of={session.device.path}",
            f"bs={blocksize}",
            "conv=fsync",
            "status=progress",
        ],
        sudo_last=True,
        error_msg=f"DD {plan.image_path} to {session.device.path} failed.",
    )
    runner.sync_disks()
