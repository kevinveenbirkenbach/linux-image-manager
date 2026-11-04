"""Guided setup: an encrypted, Tor-remote-unlockable Linux image on a device.

All questions are asked up front (``_collect``); the build then runs unattended
(``_execute``): pick a distribution and target block device (the internal SSD of
a USB-booted Pi, or a spare stick to clone later), download the image, copy it
into a LUKS container, create the login user, and bake the initramfs Tor onion
unlock. Works for any distribution with an initramfs backend (Arch/Manjaro via
mkinitcpio, Raspberry Pi OS/moode/RetroPie via initramfs-tools).
"""

import os
import pwd
import shlex
from dataclasses import dataclass
from pathlib import Path

from lim import device as device_module
from lim import ui
from lim.errors import LimError
from lim.image import choosers, crossarch, hostkeys, transfer, unlock
from lim.image.encryption import configure_encryption
from lim.image.initramfs import get_backend
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession, chroot_bash


@dataclass
class _Answers:
    host_user: str
    device: device_module.Device
    pubkey: Path
    hostname: str
    login_user: str
    login_password: str


def _intro() -> None:
    ui.info("Guided encrypted Linux image setup with Tor remote unlock.")
    ui.info("The TARGET must be an attached block device:")
    ui.info("  - internal SSD: boot the Pi from USB, then target /dev/sda or /dev/nvme0n1")
    ui.info("  - golden image: target a spare USB stick, clone it onto the SSD afterwards")
    ui.warning("The target device will be COMPLETELY ERASED.")


def _prepare_image_folder(plan: ImagePlan) -> str:
    """Cache downloads under the invoking (sudo) user's home; return that user."""
    host_user = os.environ.get("SUDO_USER") or "root"
    try:
        home = Path(pwd.getpwnam(host_user).pw_dir)
    except KeyError:
        host_user, home = "root", Path("/root")
    plan.image_folder = home / "Software/Images"
    plan.image_folder.mkdir(parents=True, exist_ok=True)
    ui.info(f"Images are cached in {plan.image_folder}.")
    return host_user


def _select_target() -> device_module.Device:
    device = device_module.select_device()
    if device_module.is_mounted(device.path):
        raise LimError(f"{device.path} is mounted. Unmount it first (umount {device.path}*).")
    ui.warning(f"Everything on {device.path} will be destroyed.")
    answer = ui.ask(f"Retype the device name ({device.name}) to confirm ERASE of {device.path}:")
    if answer.strip().removeprefix("/dev/") != device.name:
        raise LimError("Confirmation did not match. Aborting.")
    return device


def _ask_pubkey() -> Path:
    answer = ui.ask("Path to the SSH PUBLIC key (unlocks AND logs in):").strip()
    if not answer:
        raise LimError("No SSH public key path given.")
    pubkey = Path(answer).expanduser()
    if not pubkey.is_file():
        raise LimError(f"SSH public key {pubkey} not found.")
    return pubkey


def _collect(plan: ImagePlan) -> _Answers | None:
    """Ask everything up front so ``_execute`` can run without prompts."""
    _intro()
    if not ui.confirm("Continue?"):
        return None
    choosers.choose_linux_image(plan)
    plan.root_filesystem = plan.root_filesystem or "ext4"
    device = _select_target()
    hostname = ui.ask("Hostname for the system:").strip()
    login_user = ui.ask("Login username to create on the system (default pi):").strip() or "pi"
    login_password = ui.ask(f"Login password for {login_user} (empty for key-only login):")
    pubkey = _ask_pubkey()
    host_user = _prepare_image_folder(plan)
    crossarch.ensure_ready()  # may install qemu; done here, before the erase in _execute
    ui.success("All questions answered — the build now runs unattended.")
    return _Answers(host_user, device, pubkey, hostname, login_user, login_password)


def _build_authorized_keys(session: ImageSession, pubkey: Path) -> Path:
    authorized_keys = session.working_folder / "authorized_keys"
    authorized_keys.write_text(pubkey.read_text())
    return authorized_keys


def _apply_system_config(session: ImageSession, hostname: str) -> str:
    """Write the hostname and enable the post-boot SSH server; return the hostname."""
    root = session.root_mount_path
    if hostname:
        (root / "etc/hostname").write_text(hostname + "\n")
    # RPi OS enables sshd on first boot when this marker exists on the boot fs.
    (session.boot_mount_path / "ssh").write_text("")
    return (root / "etc/hostname").read_text().strip()


def _configure_login_user(session: ImageSession, user: str, password: str, pubkey: Path) -> None:
    """Rename a stock default user to the chosen one (or create it); add sudo + key.

    Renaming pi/alarm reuses the account (uid, sudoers) and leaves no lingering
    default; a fresh useradd covers images without one (e.g. RPi OS Bookworm).
    """
    key = shlex.quote(pubkey.read_text().strip())
    ui.info(f"Configuring login user {user}...")
    script = f"""\
target={shlex.quote(user)}
for old in pi alarm; do
  id "$old" >/dev/null 2>&1 || continue
  [ "$old" = "$target" ] && continue
  id "$target" >/dev/null 2>&1 && continue
  usermod -l "$target" "$old"
  usermod -d "/home/$target" -m "$target"
  groupmod -n "$target" "$old" 2>/dev/null || true
  break
done
id "$target" >/dev/null 2>&1 || useradd -m -s /bin/bash "$target"
usermod -aG sudo "$target" 2>/dev/null || true
install -d -m 700 "/home/$target/.ssh"
printf '%s\\n' {key} > "/home/$target/.ssh/authorized_keys"
chmod 600 "/home/$target/.ssh/authorized_keys"
chown -R "$target:$target" "/home/$target/.ssh"
"""
    if password:
        script += f"printf '%s' {shlex.quote(f'{user}:{password}')} | chpasswd\n"
    chroot_bash(session.root_mount_path, script)


def _record_name(hostname: str) -> str:
    return hostname or "device"


def _pin_host_keys(
    entry: pwd.struct_passwd, name: str, target: str, private_key: str, host_keys: list[str]
) -> None:
    if not host_keys:
        ui.warning("No initramfs host key found; the first unlock asks to confirm it.")
        return
    try:
        alias = hostkeys.pin(entry, name, target, private_key, host_keys)
    except OSError as exc:
        ui.warning(f"Could not pin the initramfs host key: {exc}")
        return
    ui.info(f"Pinned the initramfs host key as {alias} in ~/{hostkeys.SSH_CONFIG_SUBPATH}.")


def _save_unlock_record(
    plan: ImagePlan, answers: _Answers, hostname: str, onion: str | None, host_keys: list[str]
) -> None:
    if not onion:
        return
    name = _record_name(hostname)
    private_key = str(answers.pubkey).removesuffix(".pub")
    unlock_command = "" if plan.distribution in ("arch", "manjaro") else "cryptroot-unlock"
    record = {
        "target": onion,
        "key": private_key,
        "unlock_command": unlock_command,
        "hostname": hostname,
    }
    entry = pwd.getpwnam(answers.host_user)
    try:
        unlock.save_record(Path(entry.pw_dir), entry.pw_uid, entry.pw_gid, name, record)
        ui.info("Saved unlock target; run later with: lim --type remote-unlock")
    except OSError as exc:
        ui.warning(f"Could not save unlock record: {exc}")
    _pin_host_keys(entry, name, onion, private_key, host_keys)


def _print_summary(answers: _Answers, hostname: str, onion: str | None) -> None:
    ui.success("Encrypted Linux image is ready.")
    ui.info(f"Target device : {answers.device.path}  (hostname: {hostname})")
    if onion:
        alias = hostkeys.host_key_alias(_record_name(hostname))
        ui.info(f"Onion address : {onion}")
        ui.info(f"Unlock later  : lim --type remote-unlock   (or: torsocks ssh {alias})")
    ui.info(f"After unlock, log in: ssh {answers.login_user}@<the box>")
    ui.info("Golden image? Clone this device onto the SSD, then grow it:")
    ui.info("  parted <ssd> resizepart 2 100% && cryptsetup resize <mapper> && resize2fs <mapper>")


def _execute(plan: ImagePlan, answers: _Answers) -> None:
    transfer.download_image(plan, force_prompt=False)
    session = ImageSession(answers.device)
    authorized_keys = None
    try:
        session.make_working_folder()
        session.make_mount_folders()
        transfer.transfer_image(plan, session, interactive=False)
        authorized_keys = _build_authorized_keys(session, answers.pubkey)
        hostname = _apply_system_config(session, answers.hostname)
        session.mount_chroot_binds()
        session.copy_resolv_conf()
        onion = configure_encryption(plan, session, authorized_keys)
        host_keys = get_backend(plan.distribution).host_public_keys(session.root_mount_path)
        _configure_login_user(session, answers.login_user, answers.login_password, answers.pubkey)
        _save_unlock_record(plan, answers, hostname, onion, host_keys)
        _print_summary(answers, hostname, onion)
    finally:
        if authorized_keys is not None:
            authorized_keys.unlink(missing_ok=True)
        session.destructor()


def run_guided() -> None:
    ui.header()
    plan = ImagePlan(encrypt_system=True, tor_unlock=True)
    answers = _collect(plan)
    if answers is None:
        ui.info("Aborted.")
        return
    _execute(plan, answers)
