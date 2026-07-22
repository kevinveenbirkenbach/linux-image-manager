"""Offline Tor onion key generation, shared by every initramfs backend.

``tor --DisableNetwork 1`` writes a v3 onion service's keys without touching
the network, so the same stable ``.onion`` address can be baked into the
initramfs whether the distro uses mkinitcpio or initramfs-tools.
"""

from pathlib import Path

from lim import ui
from lim.errors import LimError
from lim.image.session import chroot_bash

# Staged relative to the mounted image root.
ONION_STAGING_DIR = "etc/tor/initramfs-onion"
TORRC_STAGING_PATH = "etc/tor/initramfs-torrc"

# An empty -f torrc keeps the image's /etc/tor/torrc (User tor, ...) out of the
# keygen run, which would otherwise fail as non-root inside the chroot.
_KEYGEN_SCRIPT = f"""
mkdir -p /{ONION_STAGING_DIR}
chmod 0700 /{ONION_STAGING_DIR}
: > /tmp/tor-keygen-torrc
tor -f /tmp/tor-keygen-torrc --DisableNetwork 1 \\
    --DataDirectory /tmp/tor-keygen-data \\
    --HiddenServiceDir /{ONION_STAGING_DIR} \\
    --HiddenServicePort "22 127.0.0.1:22" \\
    --SocksPort 0 --RunAsDaemon 0 --Log "notice stderr" &
tor_pid=$!
for _ in $(seq 1 30); do
    [ -s /{ONION_STAGING_DIR}/hostname ] && break
    sleep 1
done
kill "$tor_pid" 2>/dev/null || true
rm -rf /tmp/tor-keygen-data /tmp/tor-keygen-torrc
[ -s /{ONION_STAGING_DIR}/hostname ]
"""


def generate_onion_keys(root: Path) -> str:
    """Generate the onion keys offline in the chroot; return the .onion address.

    Idempotent: existing keys are kept so the address stays stable across
    re-runs.
    """
    hostname_path = root / ONION_STAGING_DIR / "hostname"
    if hostname_path.is_file():
        ui.info("Onion keys already exist, keeping the existing address.")
    else:
        ui.info("Generating onion service keys (offline, inside the chroot)...")
        chroot_bash(root, _KEYGEN_SCRIPT, error_msg="Onion key generation failed.")
        if not hostname_path.is_file():
            raise LimError(f"Onion key generation produced no {hostname_path}.")
    return hostname_path.read_text().strip()
