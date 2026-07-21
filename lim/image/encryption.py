"""Remote-unlockable LUKS boot configuration (dropbear + mkinitcpio).

See https://gist.github.com/gea0/4fc2be0cb7a74d0e7cc4322aed710d38 and
https://gist.github.com/EnigmaCurry/2f9bed46073da8e38057fe78a61e7994
"""

from pathlib import Path

from lim import catalog, fsutil, packages, runner, ui
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession, chroot_bash, install_packages
from lim.image.tor import configure_tor_unlock

MKINITCPIO_HOOKS_PREFIX = (
    "base udev autodetect microcode modconf kms keyboard keymap consolefont block"
)
MKINITCPIO_HOOKS_SUFFIX = "filesystems fsck"


def _configure_mkinitcpio(plan: ImagePlan, root: Path) -> None:
    # Concerning mkinitcpio warnings, see
    # https://gist.github.com/imrvelj/c65cd5ca7f5505a65e59204f5a3f7a6d
    mkinitcpio_path = root / "etc/mkinitcpio.conf"
    ui.info(f"Configuring {mkinitcpio_path}...")
    additional_modules = catalog.mkinitcpio_modules_by_rpi().get(
        plan.raspberry_pi_version
    )
    if additional_modules is None:
        ui.warning(f"Version {plan.raspberry_pi_version} isn't supported.")
        additional_modules = ""
    modules = f"g_cdc usb_f_acm usb_f_ecm {additional_modules} g_ether".replace("  ", " ")
    fsutil.replace_in_file("MODULES=()", f"MODULES=({modules})", mkinitcpio_path)
    fsutil.replace_in_file(
        "BINARIES=()", "BINARIES=(/usr/lib/libgcc_s.so.1)", mkinitcpio_path
    )
    tor_hook = "tor " if plan.tor_unlock else ""
    fsutil.replace_in_file(
        f"HOOKS=({MKINITCPIO_HOOKS_PREFIX} {MKINITCPIO_HOOKS_SUFFIX})",
        f"HOOKS=({MKINITCPIO_HOOKS_PREFIX} sleep netconf {tor_hook}dropbear encryptssh "
        f"{MKINITCPIO_HOOKS_SUFFIX})",
        mkinitcpio_path,
    )
    ui.info(f"Content of {mkinitcpio_path}:{mkinitcpio_path.read_text()}")
    ui.info("Generating mkinitcpio...")
    chroot_bash(root, "mkinitcpio -vP")


def _register_encrypted_root(plan: ImagePlan, session: ImageSession, root: Path) -> None:
    fstab_path = root / "etc/fstab"
    fstab_line = (
        f"UUID={session.root_partition_uuid}  / {plan.root_filesystem}"
        "    defaults,noatime  0  1"
    )
    ui.info(f"Configuring {fstab_path}...")
    fsutil.ensure_line_in_file(fstab_line, fstab_path)
    ui.info(f"Content of {fstab_path}:{fstab_path.read_text()}")

    crypttab_path = root / "etc/crypttab"
    crypttab_line = (
        f"{session.root_mapper_name} UUID={session.root_partition_uuid} none luks"
    )
    ui.info(f"Configuring {crypttab_path}...")
    fsutil.ensure_line_in_file(crypttab_line, crypttab_path)
    ui.info(f"Content of {crypttab_path}:{crypttab_path.read_text()}")


def _configure_bootloader(plan: ImagePlan, session: ImageSession, root: Path) -> None:
    cryptdevice = (
        f"cryptdevice=UUID={session.root_partition_uuid}:{session.root_mapper_name} "
        f"root={session.root_mapper_path}"
    )
    boot_txt_path = session.boot_mount_path / "boot.txt"
    if boot_txt_path.is_file():
        ui.info(f"Configuring {boot_txt_path}...")
        hostname = (root / "etc/hostname").read_text().strip()
        fsutil.replace_in_file(
            "part uuid ${devtype} ${devnum}:2 uuid", "", boot_txt_path
        )
        fsutil.replace_in_file(
            "setenv bootargs console=ttyS1,115200 console=tty0 root=PARTUUID=${uuid} "
            'rw rootwait smsc95xx.macaddr="${usbethaddr}"',
            f"setenv bootargs console=ttyS1,115200 console=tty0 "
            f"ip=::::{hostname}:eth0:dhcp {cryptdevice} rw rootwait "
            # Concerning issues with network adapter names, see
            # https://forum.iobroker.net/topic/40542/raspberry-pi4-kein-eth0-mehr/16
            'smsc95xx.macaddr="${usbethaddr}" net.ifnames=0 biosdevname=0',
            boot_txt_path,
        )
        ui.info(f"Content of {boot_txt_path}:{boot_txt_path.read_text()}")
        ui.info("Generating...")
        chroot_bash(root, "cd /boot/ && ./mkscr || exit 1")
    else:
        cmdline_txt_path = session.boot_mount_path / "cmdline.txt"
        ui.info(f"Configuring {cmdline_txt_path}...")
        # Firmware-boot boards (e.g. RPi4 cmdline.txt) need the same early
        # networking as the boot.txt branch, or the initramfs netconf hook
        # brings up no interface and remote unlock (dropbear + tor) is
        # unreachable — the onion never even publishes.
        hostname = (root / "etc/hostname").read_text().strip()
        fsutil.replace_in_file(
            "root=/dev/mmcblk0p2",
            f"{cryptdevice} rootfstype={plan.root_filesystem} "
            f"ip=::::{hostname}:eth0:dhcp net.ifnames=0 biosdevname=0",
            cmdline_txt_path,
        )
        ui.info(f"Content of {cmdline_txt_path}:{cmdline_txt_path.read_text()}")


def configure_encryption(
    plan: ImagePlan, session: ImageSession, authorized_keys: Path
) -> None:
    root = session.root_mount_path
    ui.info("Setup encryption...")
    ui.info("Installing neccessary software...")
    install_packages(
        plan.distribution, root, " ".join(packages.get_packages("server/luks"))
    )

    dropbear_root_key_path = root / "etc/dropbear/root_key"
    ui.info(f"Adding {authorized_keys} to dropbear...")
    runner.run(["cp", "-v", str(authorized_keys), str(dropbear_root_key_path)], sudo=True)

    if plan.tor_unlock:
        # Hook files and onion keys must exist before mkinitcpio bakes the image.
        configure_tor_unlock(plan, root)

    _configure_mkinitcpio(plan, root)
    _register_encrypted_root(plan, session, root)
    _configure_bootloader(plan, session, root)
