"""The image setup plan collected from the user's answers."""

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BOOT_SIZE = "+500M"


@dataclass
class ImagePlan:
    operation_system: str = "linux"
    distribution: str | None = None
    base_download_url: str | None = None
    image_name: str | None = None
    image_checksum: str | None = None
    boot_size: str = ""
    luks_memory_cost: str | None = None
    raspberry_pi_version: str | None = None
    encrypt_system: bool = False
    tor_unlock: bool = False
    root_filesystem: str = ""
    image_folder: Path = field(default_factory=Path)

    @property
    def download_url(self) -> str | None:
        if self.base_download_url is None or self.image_name is None:
            return None
        return f"{self.base_download_url}{self.image_name}"

    @property
    def image_path(self) -> Path:
        return self.image_folder / self.image_name
