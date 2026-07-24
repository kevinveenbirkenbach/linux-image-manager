"""Mount/unmount lifecycle for working on an image on a block device."""

import time
from pathlib import Path

from lim import device as device_module
from lim import runner, ui
from lim.device import Device
from lim.errors import LimError


class ImageSession:
    """Working folder, partition paths and (chroot) mounts for one device.

    Call ``destructor()`` in a finally block: it unmounts and removes
    everything best-effort, mirroring partially completed setups.
    """

    def __init__(self, device: Device) -> None:
        self.device = device
        self.working_folder: Path | None = None
        self.boot_mount_path: Path | None = None
        self.root_mount_path: Path | None = None
        self.boot_partition_path = device.partition(1)
        self.root_partition_path = device.partition(2)
        # Overridden by decrypt_root() when the root partition is LUKS.
        self.root_mapper_path = self.root_partition_path
        self.root_mapper_name: str | None = None
        self.boot_partition_uuid: str | None = None
        self.root_partition_uuid: str | None = None

    def make_working_folder(self) -> None:
        # Mount points must live on the root fs; mkdir() fails on collisions.
        self.working_folder = Path(f"/tmp/linux-image-manager-{int(time.time())}")  # noqa: S108
        ui.info(f"Create temporary working folder in {self.working_folder}")
        self.working_folder.mkdir(parents=True)

    def make_mount_folders(self) -> None:
        if self.working_folder is None:
            self.make_working_folder()
        ui.info("Preparing mount paths...")
        self.boot_mount_path = self.working_folder / "boot"
        self.root_mount_path = self.working_folder / "root"
        self.boot_mount_path.mkdir()
        self.root_mount_path.mkdir()

    def root_is_luks(self) -> bool:
        return device_module.blkid_value(self.root_partition_path, "TYPE") == "crypto_LUKS"

    def read_partition_uuids(self) -> None:
        """Fetch partition UUIDs via blkid; derive the LUKS mapper name if unset."""
        self.root_partition_uuid = device_module.blkid_value(self.root_partition_path, "UUID")
        self.boot_partition_uuid = device_module.blkid_value(self.boot_partition_path, "UUID")
        if self.root_mapper_name is None and self.root_is_luks():
            # Same deterministic name decrypt_root() would have used.
            self.root_mapper_name = f"linux-image-manager-{self.root_partition_uuid}"
            self.root_mapper_path = f"/dev/mapper/{self.root_mapper_name}"

    def decrypt_root(self) -> None:
        if not self.root_is_luks():
            return
        self.root_partition_uuid = device_module.blkid_value(self.root_partition_path, "UUID")
        self.root_mapper_name = f"linux-image-manager-{self.root_partition_uuid}"
        self.root_mapper_path = f"/dev/mapper/{self.root_mapper_name}"
        ui.info(f"Decrypting of {self.root_partition_path} is neccessary...")
        runner.run(
            [
                "cryptsetup",
                "-v",
                "luksOpen",
                self.root_partition_path,
                self.root_mapper_name,
            ],
            sudo=True,
        )

    def mount_partitions(self) -> None:
        if self.boot_mount_path is None:
            raise LimError("Mount folders are not prepared yet.")
        ui.info("Mount boot and root partition...")
        runner.run(
            ["mount", "-v", self.boot_partition_path, str(self.boot_mount_path)],
            sudo=True,
        )
        runner.run(["mount", "-v", self.root_mapper_path, str(self.root_mount_path)], sudo=True)
        ui.info("Setting uuid variables...")
        self.read_partition_uuids()
        ui.info("The following mounts refering this setup exist:")
        runner.run(["findmnt", "-R", str(self.working_folder)], check=False)

    def boot_bind_target(self) -> str:
        """Where the FAT partition belongs inside the chroot.

        Raspberry Pi OS Bookworm keeps it at /boot/firmware (the raspi-firmware
        post-update hook syncs the initramfs there); older layouts use /boot.
        Binding it wrong sends update-initramfs's output to the ext4 root, so the
        firmware boots a stock initramfs without cryptsetup -> initramfs shell.
        """
        if (self.root_mount_path / "boot/firmware").is_dir():
            return f"{self.root_mount_path}/boot/firmware"
        return f"{self.root_mount_path}/boot"

    def mount_chroot_binds(self) -> None:
        ui.info("Mount chroot environments...")
        root = self.root_mount_path
        runner.run(
            ["mount", "--bind", str(self.boot_mount_path), self.boot_bind_target()], sudo=True
        )
        runner.run(["mount", "--bind", "/dev", f"{root}/dev"], sudo=True)
        runner.run(["mount", "--bind", "/sys", f"{root}/sys"], sudo=True)
        runner.run(["mount", "--bind", "/proc", f"{root}/proc"], sudo=True)
        runner.run(["mount", "--bind", "/dev/pts", f"{root}/dev/pts"], sudo=True)

    def copy_qemu(self) -> None:
        ui.info("Copy qemu binary...")
        runner.run(
            ["cp", "-v", "/usr/bin/qemu-arm-static", f"{self.root_mount_path}/usr/bin/"],
            sudo=True,
        )

    def copy_resolv_conf(self) -> None:
        ui.info("Copy resolv.conf...")
        copied = runner.run(
            [
                "cp",
                "--remove-destination",
                "-v",
                "/etc/resolv.conf",
                f"{self.root_mount_path}/etc/",
            ],
            sudo=True,
            check=False,
        )
        if copied.returncode != 0:
            ui.warning("Failed. Probably there is no internet connection available.")

    def _umount(self, path: str, *, lazy: bool = False) -> None:
        flags = ["-lv"] if lazy else ["-v"]
        result = runner.run(["umount", *flags, path], sudo=True, check=False)
        if result.returncode != 0:
            ui.warning(f"Umounting {path} failed!")

    def _rmdir(self, path: Path | None) -> None:
        if path is None:
            return
        result = runner.run(["rmdir", "-v", str(path)], sudo=True, check=False)
        if result.returncode != 0:
            ui.warning(f"Removing {path} failed!")

    def destructor(self) -> None:
        ui.info("Cleaning up...")
        ui.info("Unmounting everything...")
        root = self.root_mount_path
        if root is not None:
            self._umount(f"{root}/dev/pts", lazy=True)
            self._umount(f"{root}/dev", lazy=True)
            self._umount(f"{root}/proc")
            self._umount(f"{root}/sys")
            self._umount(self.boot_bind_target())
            self._umount(str(root))
        if self.boot_mount_path is not None:
            self._umount(str(self.boot_mount_path))
        ui.info("Deleting mount folders...")
        self._rmdir(self.root_mount_path)
        self._rmdir(self.boot_mount_path)
        self._rmdir(self.working_folder)
        if self.root_mapper_name and self.root_is_luks():
            ui.info(f"Trying to close decrypted {self.root_mapper_name}...")
            closed = runner.run(
                ["cryptsetup", "-v", "luksClose", self.root_mapper_name],
                sudo=True,
                check=False,
            )
            if closed.returncode != 0:
                ui.warning("Failed.")


# The host PATH leaks into the chroot; force one that includes the sbin dirs
# where Debian keeps update-initramfs, useradd, chpasswd, ... (else code 127).
_CHROOT_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def chroot_bash(root_mount_path: Path | str, script: str, error_msg: str | None = None) -> None:
    """Run a bash script inside the image via chroot (with a Debian-safe PATH)."""
    runner.run(
        ["chroot", str(root_mount_path), "/bin/bash"],
        input_text=f"export PATH={_CHROOT_PATH}\n{script}",
        sudo=True,
        error_msg=error_msg,
    )


def install_packages(distribution: str, root_mount_path: Path, package_names: str) -> None:
    """Install packages inside the image with the distribution's package manager."""
    ui.info(f"Installing {package_names}...")
    if distribution in ("arch", "manjaro"):
        chroot_bash(root_mount_path, f"pacman --noconfirm -Sy --needed {package_names}")
    elif distribution in ("moode", "retropie", "raspios"):
        # apt-get update first: a stock image ships stale lists whose old .deb
        # URLs 404 once the mirror has superseded them.
        chroot_bash(
            root_mount_path,
            f"apt-get update\nDEBIAN_FRONTEND=noninteractive apt-get install -y {package_names}",
        )
    else:
        raise LimError("Package manager not supported.")
