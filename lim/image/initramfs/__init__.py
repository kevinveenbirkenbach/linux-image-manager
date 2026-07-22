"""Distro-specific initramfs backends for encrypted remote unlock."""

from lim.errors import LimError
from lim.image.initramfs.base import InitramfsBackend
from lim.image.initramfs.initramfs_tools import InitramfsToolsBackend
from lim.image.initramfs.mkinitcpio import MkinitcpioBackend

_MKINITCPIO = frozenset({"arch", "manjaro"})
_INITRAMFS_TOOLS = frozenset({"raspios", "moode", "retropie"})


def get_backend(distribution: str | None) -> InitramfsBackend:
    """Pick the initramfs backend for a distribution's init system."""
    if distribution in _MKINITCPIO:
        return MkinitcpioBackend()
    if distribution in _INITRAMFS_TOOLS:
        return InitramfsToolsBackend()
    raise LimError(f"No initramfs backend for distribution {distribution!r}.")


__all__ = ["InitramfsBackend", "get_backend"]
