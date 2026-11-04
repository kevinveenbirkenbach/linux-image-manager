"""The initramfs backend interface.

Encrypted remote-unlock images differ by init system: Arch/Manjaro use
mkinitcpio, Debian/Raspberry Pi OS use initramfs-tools. Each backend owns the
distro-specific bits (package set, crypttab syntax, initramfs generation,
bootloader cmdline, and how the Tor hook is baked in); the encryption flow
orchestrates them the same way for every distro.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from lim.image.plan import ImagePlan
from lim.image.session import ImageSession


class InitramfsBackend(ABC):
    """Distro-specific steps to build an encrypted, remote-unlockable image."""

    @abstractmethod
    def luks_package_collection(self) -> str:
        """Name of the package collection providing the LUKS/unlock stack."""

    @abstractmethod
    def install_authorized_key(self, root: Path, authorized_keys: Path) -> None:
        """Place the SSH public key where the initramfs dropbear reads it."""

    @abstractmethod
    def install_tor_unlock(self, plan: ImagePlan, root: Path) -> str:
        """Bake the Tor onion service into the initramfs; return the address."""

    @abstractmethod
    def register_encrypted_root(self, plan: ImagePlan, session: ImageSession, root: Path) -> None:
        """Write fstab and crypttab in the distro's syntax."""

    @abstractmethod
    def configure_initramfs(self, plan: ImagePlan, root: Path) -> None:
        """Configure the initramfs modules/hooks and (re)generate it."""

    @abstractmethod
    def configure_bootloader(self, plan: ImagePlan, session: ImageSession, root: Path) -> None:
        """Point the bootloader at the encrypted root with early networking."""

    @abstractmethod
    def host_public_keys(self, root: Path) -> list[str]:
        """OpenSSH public key lines of the host keys baked into the initramfs."""
