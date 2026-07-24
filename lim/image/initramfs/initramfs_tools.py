"""initramfs-tools backend (Debian / Raspberry Pi OS).

Debian does not use mkinitcpio; the LUKS unlock stack is cryptsetup-initramfs
(reads /etc/crypttab, option ``initramfs``) + dropbear-initramfs (serves the
passphrase prompt over SSH). Raspberry Pi OS ships without an initramfs, so we
enable one in config.txt and regenerate with update-initramfs.

NOTE: the exact dropbear-initramfs key path, the boot-partition mount point
(/boot vs /boot/firmware) and the initramfs enable knob vary across Raspberry
Pi OS releases; verify on the target release. This path is not exercised by the
QEMU harness yet.
"""

import re
from pathlib import Path

from lim import config, fsutil, packages, runner, ui
from lim.image.initramfs import keygen
from lim.image.initramfs.base import InitramfsBackend
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession, chroot_bash, install_packages

# Numeric IP, not a hostname: the initramfs has no DNS resolver.
_DEFAULT_NTP = "162.159.200.123"


class InitramfsToolsBackend(InitramfsBackend):
    def luks_package_collection(self) -> str:
        return "server/luks-debian"

    def install_authorized_key(self, root: Path, authorized_keys: Path) -> None:
        # dropbear-initramfs (bookworm) reads /etc/dropbear/initramfs/authorized_keys.
        target = root / "etc/dropbear/initramfs/authorized_keys"
        ui.info(f"Adding {authorized_keys} to {target}...")
        runner.run(
            ["install", "-D", "-m", "0600", str(authorized_keys), str(target)],
            sudo=True,
        )

    def install_tor_unlock(self, plan: ImagePlan, root: Path) -> str:
        ui.info("Setting up remote unlock via Tor onion service (initramfs-tools)...")
        install_packages(
            plan.distribution, root, " ".join(packages.get_packages("server/tor-debian"))
        )
        source_dir = config.CONFIGURATION_PATH / "initramfs-tools"
        for source, target, mode in (
            (source_dir / "tor_hook", root / "etc/initramfs-tools/hooks/tor", "0755"),
            (
                source_dir / "tor_premount",
                root / "etc/initramfs-tools/scripts/init-premount/tor",
                "0755",
            ),
            (
                source_dir / "tor_bottom",
                root / "etc/initramfs-tools/scripts/init-bottom/tor",
                "0755",
            ),
            (source_dir / "torrc", root / keygen.TORRC_STAGING_PATH, "0644"),
        ):
            ui.info(f"Installing {target}...")
            runner.run(["install", "-D", "-m", mode, str(source), str(target)], sudo=True)
        onion_address = keygen.generate_onion_keys(root)
        ui.success(f"Onion unlock address: {onion_address}")
        ui.info(f"Unlock later with: torsocks ssh root@{onion_address}")
        return onion_address

    def register_encrypted_root(self, plan: ImagePlan, session: ImageSession, root: Path) -> None:
        fstab_path = root / "etc/fstab"
        fstab_line = (
            f"/dev/mapper/{session.root_mapper_name}  /  {plan.root_filesystem}"
            "  defaults,noatime  0  1"
        )
        ui.info(f"Configuring {fstab_path}...")
        # A stock image already mounts / by PARTUUID; drop it so the mapper wins.
        fsutil.drop_fstab_mount("/", fstab_path)
        fsutil.ensure_line_in_file(fstab_line, fstab_path)

        crypttab_path = root / "etc/crypttab"
        # `initramfs` bakes the mapping into the initramfs so cryptsetup-initramfs
        # unlocks the root before the pivot.
        crypttab_line = (
            f"{session.root_mapper_name} UUID={session.root_partition_uuid} none luks,initramfs"
        )
        ui.info(f"Configuring {crypttab_path}...")
        fsutil.ensure_line_in_file(crypttab_line, crypttab_path)

    def configure_initramfs(self, plan: ImagePlan, root: Path) -> None:  # noqa: ARG002
        ui.info("Regenerating the Debian initramfs (update-initramfs)...")
        # Create for all installed kernels when none exists yet (Raspberry Pi OS
        # ships without one), else update the existing one. `-k all` avoids the
        # build host's `uname -r` leaking into the chroot.
        chroot_bash(
            root,
            "update-initramfs -c -k all 2>/dev/null || update-initramfs -u -k all",
        )

    def configure_bootloader(self, plan: ImagePlan, session: ImageSession, root: Path) -> None:
        hostname = (root / "etc/hostname").read_text().strip()
        boot = session.boot_mount_path

        config_txt = boot / "config.txt"
        if config_txt.is_file():
            ui.info(f"Enabling an initramfs in {config_txt}...")
            fsutil.ensure_line_in_file("auto_initramfs=1", config_txt)

        cmdline_txt = boot / "cmdline.txt"
        ui.info(f"Configuring {cmdline_txt}...")
        text = cmdline_txt.read_text().strip()
        text = re.sub(r"root=\S+", f"root=/dev/mapper/{session.root_mapper_name}", text)
        if "ip=" not in text:
            text = f"{text} ip=::::{hostname}:eth0:dhcp"
        if "net.ifnames=0" not in text:
            text = f"{text} net.ifnames=0"
        if plan.tor_unlock and "tor_ntp=" not in text:
            text = f"{text} tor_ntp={_DEFAULT_NTP}"
        cmdline_txt.write_text(text + "\n")
        ui.info(f"Content of {cmdline_txt}:{cmdline_txt.read_text()}")
