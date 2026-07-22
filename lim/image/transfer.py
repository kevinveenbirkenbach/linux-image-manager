"""Download the selected image and transfer it onto the target device."""

import shutil
from pathlib import Path

from lim import device as device_module
from lim import runner, ui
from lim.errors import LimError
from lim.image import loopimg
from lim.image.plan import DEFAULT_BOOT_SIZE, ImagePlan
from lim.image.session import ImageSession


def download_image(plan: ImagePlan, *, force_prompt: bool = True) -> None:
    if force_prompt and ui.confirm("Should the image download be forced?"):
        if plan.image_path.is_file():
            ui.info(f"Removing image {plan.image_path}.")
            plan.image_path.unlink()
        else:
            ui.info(f"Forcing download wasn't neccessary. File {plan.image_path} doesn't exist.")

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
        "o\n"  # clear out any partitions on the drive
        "p\n"  # list partitions (should be empty)
        "n\np\n1\n\n"  # new primary partition 1, default start sector
        f"{boot_size}\n"
        "t\nc\n"  # set partition 1 to type W95 FAT32 (LBA)
        "n\np\n2\n\n\n"  # new primary partition 2 over the remaining space
        "w\n"  # write partition table
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
        "cryptsetup",
        "-v",
        "luksFormat",
        "-c",
        "aes-xts-plain64",
        "-s",
        "512",
        "-h",
        "sha512",
        "--use-random",
        "-i",
        "1000",
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


def _create_encrypted_layout(plan: ImagePlan, session: ImageSession) -> None:
    """Partition the target, LUKS-format the root, format and mount both."""
    boot_size = plan.boot_size or DEFAULT_BOOT_SIZE
    ui.info(f"Creating partitions (boot {boot_size})...")
    runner.run(
        ["fdisk", session.device.path],
        input_text=arch_partition_input(boot_size),
        sudo=True,
    )
    runner.run(["mkfs.vfat", session.boot_partition_path], sudo=True)
    _luks_format_root(plan, session)
    session.decrypt_root()
    runner.run([f"mkfs.{plan.root_filesystem}", "-F", session.root_mapper_path], sudo=True)
    session.mount_partitions()


def _copy_tree(source: str, target: str, flags: list[str]) -> None:
    """Copy a directory's contents, showing progress when rsync is available."""
    if shutil.which("rsync"):
        runner.run(["rsync", *flags, "--info=progress2", f"{source}/", f"{target}/"], sudo=True)
    else:
        runner.run(["cp", "-a", f"{source}/.", target], sudo=True)


def _fix_boot_fstab(session: ImageSession) -> None:
    """Repoint the stock boot fstab line at the freshly created boot partition.

    The copied image mounts /boot(/firmware) by the stock PARTUUID, which no
    longer exists after repartitioning; swap in the new boot UUID, mount point
    unchanged. No-op when the image carries no boot line.
    """
    fstab = session.root_mount_path / "etc/fstab"
    if not fstab.is_file():
        return
    lines = []
    for line in fstab.read_text().splitlines():
        fields = line.split()
        if not line.lstrip().startswith("#") and fields[1:2] and fields[1].startswith("/boot"):
            fields[0] = f"UUID={session.boot_partition_uuid}"
            lines.append("  ".join(fields))
        else:
            lines.append(line)
    fstab.write_text("".join(f"{entry}\n" for entry in lines))


def transfer_disk_image(plan: ImagePlan, session: ImageSession) -> None:
    """Copy a full disk image (boot + root partitions) into a fresh encrypted layout.

    Distributions that ship a partitioned .img rather than a rootfs tarball
    (Raspberry Pi OS, moode, RetroPie, Manjaro ARM) are loop-mounted and their
    first two partitions copied into a new LUKS container.
    """
    raw = plan.image_path.with_suffix("")
    ui.info(f"Decompressing {plan.image_path} to {raw}...")
    runner.pipeline(
        decompress_command(plan.image_path),
        ["dd", f"of={raw}", "bs=4M", "conv=fsync", "status=progress"],
        error_msg=f"Decompressing {plan.image_path} failed.",
    )
    loop = loopimg.attach(raw)
    source_boot = session.working_folder / "source-boot"
    source_root = session.working_folder / "source-root"
    try:
        source_boot.mkdir()
        source_root.mkdir()
        runner.run(["mount", "-o", "ro", loopimg.partition(loop, 1), str(source_boot)], sudo=True)
        runner.run(["mount", "-o", "ro", loopimg.partition(loop, 2), str(source_root)], sudo=True)

        _create_encrypted_layout(plan, session)

        ui.info("Copying the root filesystem into the encrypted container...")
        _copy_tree(str(source_root), str(session.root_mount_path), ["-aHAX"])
        ui.info("Copying the boot partition...")
        _copy_tree(str(source_boot), str(session.boot_mount_path), ["-a"])
        runner.sync_disks()
        _fix_boot_fstab(session)
    finally:
        runner.run(["umount", "-v", str(source_boot)], sudo=True, check=False)
        runner.run(["umount", "-v", str(source_root)], sudo=True, check=False)
        loopimg.detach(loop)
        for path in (source_boot, source_root):
            runner.run(["rmdir", str(path)], sudo=True, check=False)


def transfer_image(plan: ImagePlan, session: ImageSession, *, interactive: bool = True) -> None:
    if interactive:
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
    if plan.encrypt_system:
        # Non-tarball distros ship a full .img; copy it into a LUKS container.
        transfer_disk_image(plan, session)
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
