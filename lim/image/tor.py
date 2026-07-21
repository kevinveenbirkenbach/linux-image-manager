"""Tor onion service in the initramfs for remote LUKS unlock.

The onion keys are generated offline inside the image chroot
(``tor --DisableNetwork 1`` writes them without touching the network)
and baked into the initramfs by the "tor" mkinitcpio hook, so the
dropbear unlock shell stays reachable under a stable .onion address
even behind NAT or a dynamic IP.
"""

from pathlib import Path

from lim import config, packages, runner, ui
from lim.errors import LimError
from lim.image.plan import ImagePlan
from lim.image.session import chroot_bash, install_packages

# Paths inside the image (relative to the mounted root).
ONION_DIR = "etc/tor/initramfs-onion"
TORRC_PATH = "etc/tor/initramfs-torrc"

# An empty -f torrc keeps the image's /etc/tor/torrc (User tor, ...) out of
# the keygen run; with DisableNetwork the keys appear within a second, the
# loop only cushions slow qemu-emulated chroots.
_KEYGEN_SCRIPT = f"""
mkdir -p /{ONION_DIR}
chmod 0700 /{ONION_DIR}
: > /tmp/tor-keygen-torrc
tor -f /tmp/tor-keygen-torrc --DisableNetwork 1 \\
    --DataDirectory /tmp/tor-keygen-data \\
    --HiddenServiceDir /{ONION_DIR} \\
    --HiddenServicePort "22 127.0.0.1:22" \\
    --SocksPort 0 --RunAsDaemon 0 --Log "notice stderr" &
tor_pid=$!
for _ in $(seq 1 30); do
    [ -s /{ONION_DIR}/hostname ] && break
    sleep 1
done
kill "$tor_pid" 2>/dev/null || true
rm -rf /tmp/tor-keygen-data /tmp/tor-keygen-torrc
[ -s /{ONION_DIR}/hostname ]
"""


def _install_initcpio_files(root: Path) -> None:
    source_dir = config.CONFIGURATION_PATH / "initcpio"
    for source, target in (
        (source_dir / "tor_install", root / "etc/initcpio/install/tor"),
        (source_dir / "tor_hook", root / "etc/initcpio/hooks/tor"),
        (source_dir / "torrc", root / TORRC_PATH),
    ):
        ui.info(f"Installing {target}...")
        runner.run(
            ["install", "-D", "-m", "0644", str(source), str(target)], sudo=True
        )


def _generate_onion_keys(root: Path) -> str:
    hostname_path = root / ONION_DIR / "hostname"
    if hostname_path.is_file():
        ui.info("Onion keys already exist, keeping the existing address.")
    else:
        ui.info("Generating onion service keys (offline, inside the chroot)...")
        chroot_bash(root, _KEYGEN_SCRIPT, error_msg="Onion key generation failed.")
        if not hostname_path.is_file():
            raise LimError(f"Onion key generation produced no {hostname_path}.")
    return hostname_path.read_text().strip()


def configure_tor_unlock(plan: ImagePlan, root: Path) -> str:
    """Install everything the "tor" mkinitcpio hook bakes in; return the onion address."""
    ui.info("Setting up remote unlock via Tor onion service...")
    install_packages(
        plan.distribution, root, " ".join(packages.get_packages("server/tor"))
    )
    _install_initcpio_files(root)
    onion_address = _generate_onion_keys(root)
    ui.success(f"Onion unlock address: {onion_address}")
    ui.info(f"Unlock later with: torsocks ssh root@{onion_address}")
    return onion_address
