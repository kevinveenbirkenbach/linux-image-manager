"""Shared path derivation for encrypted storage setups."""

from dataclasses import dataclass

from lim import device as device_module
from lim import ui
from lim.device import Device


@dataclass(frozen=True)
class StorageTarget:
    """An encrypted drive plus all derived mapper/mount/partition paths."""

    device: Device

    @property
    def mapper_name(self) -> str:
        return f"encrypteddrive-{self.device.name}"

    @property
    def mapper_path(self) -> str:
        return f"/dev/mapper/{self.mapper_name}"

    @property
    def mount_path(self) -> str:
        return f"/media/{self.mapper_name}"

    @property
    def partition_path(self) -> str:
        return self.device.partition(1)


def select_storage_target() -> StorageTarget:
    target = StorageTarget(device_module.select_device())
    ui.info(f"mapper name set to : {target.mapper_name}")
    ui.info(f"mapper path set to : {target.mapper_path}")
    ui.info(f"mount path set to : {target.mount_path}")
    return target
