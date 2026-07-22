"""Remote-unlockable LUKS boot configuration.

Distro-agnostic orchestration; the init-system-specific steps live in the
initramfs backends (mkinitcpio for Arch/Manjaro, initramfs-tools for
Debian/Raspberry Pi OS). See lim/image/initramfs/.
"""

from pathlib import Path

from lim import packages, ui
from lim.image.initramfs import get_backend
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession, install_packages


def configure_encryption(
    plan: ImagePlan, session: ImageSession, authorized_keys: Path
) -> str | None:
    """Configure the remote-unlock LUKS stack; return the onion address, if any."""
    root = session.root_mount_path
    backend = get_backend(plan.distribution)
    ui.info("Setup encryption...")
    ui.info("Installing neccessary software...")
    install_packages(
        plan.distribution,
        root,
        " ".join(packages.get_packages(backend.luks_package_collection())),
    )

    backend.install_authorized_key(root, authorized_keys)

    onion_address = None
    if plan.tor_unlock:
        # Hook files and onion keys must exist before the initramfs is baked.
        onion_address = backend.install_tor_unlock(plan, root)

    # crypttab must be written before the initramfs is (re)generated so the
    # Debian cryptsetup hook can bake the mapping in.
    backend.register_encrypted_root(plan, session, root)
    backend.configure_initramfs(plan, root)
    backend.configure_bootloader(plan, session, root)
    return onion_address
