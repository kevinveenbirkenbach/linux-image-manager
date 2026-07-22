"""Raspberry-Pi-specific configuration of a freshly transferred image."""

from pathlib import Path

from lim import device as device_module
from lim import fsutil, runner, ui
from lim.errors import LimError
from lim.image.encryption import configure_encryption
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession, chroot_bash, install_packages

ADMINISTRATOR_USERNAME = "administrator"


def configure_sudoers(root_mount_path: Path, username: str) -> None:
    sudo_config_dir = root_mount_path / "etc/sudoers.d"
    sudo_config_file = sudo_config_dir / username
    sudo_config_dir.mkdir(parents=True, exist_ok=True)
    try:
        sudo_config_file.write_text(f"{username} ALL=(ALL:ALL) ALL\n")
        sudo_config_file.chmod(0o440)
    except OSError as exc:
        raise LimError(f"Failed to create sudoers file for {username}: {exc}") from exc


def configure_ssh_key(public_key_path: str, target_ssh_folder: Path, authorized_keys: Path) -> None:
    source = Path(public_key_path)
    if not source.is_file():
        raise LimError(
            f'The ssh key "{public_key_path}" can\'t be copied to '
            f'"{authorized_keys}" because it doesn\'t exist.'
        )
    ui.info("Copy ssh key to target...")
    target_ssh_folder.mkdir(parents=True, exist_ok=True)
    authorized_keys.write_text(source.read_text())
    ui.info(f"{authorized_keys} contains the following: {authorized_keys.read_text()}")
    ui.info("Set permissions with chmod...")
    target_ssh_folder.chmod(0o700)
    authorized_keys.chmod(0o600)


def _ensure_image_mounted(session: ImageSession) -> None:
    ui.info("Start regular mounting procedure...")
    if device_module.is_mounted(session.boot_partition_path):
        ui.info(f"{session.boot_partition_path} is allready mounted...")
    elif device_module.is_mounted(session.root_mapper_path):
        ui.info(f"{session.root_mapper_path} is allready mounted...")
    else:
        session.decrypt_root()
        session.mount_partitions()
    if session.boot_partition_uuid is None:
        # Partitions were mounted by an earlier run; fetch what mount_partitions
        # would have provided so fstab/crypttab never see a None UUID.
        session.read_partition_uuids()


def _seed_boot_uuid(session: ImageSession) -> None:
    fstab_path = session.root_mount_path / "etc/fstab"
    if "/dev/mmcblk0p1" not in fstab_path.read_text():
        # PARTUUID=/LABEL= based images (e.g. RetroPie, Manjaro ARM) have
        # nothing to seed — that is a valid state, not an error.
        ui.info(f"{fstab_path} does not reference /dev/mmcblk0p1. Skipping UUID seeding.")
        return
    ui.info(f"Seeding UUID to {fstab_path} to avoid path conflicts...")
    fsutil.replace_in_file("/dev/mmcblk0p1", f"UUID={session.boot_partition_uuid}", fstab_path)
    ui.info(f"Content of {fstab_path}:{fstab_path.read_text()}")


def _select_target_user(root: Path) -> tuple[str, str]:
    """Return (default username, target username), renaming the home on request."""
    target_home_path = root / "home"
    home_entries = sorted(path.name for path in target_home_path.iterdir())
    if not home_entries:
        raise LimError(f"No home directory found under {target_home_path}.")
    default_username = home_entries[0]
    rename = default_username != ADMINISTRATOR_USERNAME and ui.confirm(
        f"Should the {default_username} be renamed to {ADMINISTRATOR_USERNAME}? "
    )
    if not rename:
        return default_username, default_username
    ui.info(
        f"Rename home directory from {target_home_path / default_username} "
        f"to {target_home_path / ADMINISTRATOR_USERNAME}..."
    )
    runner.run(
        [
            "mv",
            "-v",
            str(target_home_path / default_username),
            str(target_home_path / ADMINISTRATOR_USERNAME),
        ],
        sudo=True,
        error_msg="Failed to rename home directory",
    )
    return default_username, ADMINISTRATOR_USERNAME


def _change_passwords(root: Path, target_username: str) -> None:
    password = ui.ask(
        f"Type in new password for user root and {target_username} (leave empty to skip): "
    )
    if not password:
        ui.info("No password change requested, skipped password change...")
        return
    repeated = ui.ask(f'Repeat new password for "{target_username}": ')
    if password != repeated:
        raise LimError("Passwords didn't match.")
    ui.info("Changing passwords on target system...")
    chroot_bash(
        root,
        f"( echo '{password}'; echo '{password}' ) | passwd {target_username}\n"
        f"( echo '{password}'; echo '{password}' ) | passwd\n",
        error_msg="Failed to change password.",
    )


def _configure_hostname(root: Path) -> None:
    hostname_path = root / "etc/hostname"
    hostname = ui.ask("Type in the hostname (leave empty to skip): ")
    if hostname:
        hostname_path.write_text(hostname + "\n")
    else:
        hostname = hostname_path.read_text().strip()
        ui.info("No hostname change requested, skipped hostname change...")
    ui.info(f"Used hostname is: {hostname}")


def _update_system(plan: ImagePlan, root: Path) -> None:
    if not ui.confirm("Should the system be updated?"):
        return
    ui.info("Updating system...")
    if plan.distribution in ("arch", "manjaro"):
        chroot_bash(root, "pacman --noconfirm -Syyu")
    elif plan.distribution in ("moode", "retropie", "raspios"):
        chroot_bash(root, "yes | apt update\nyes | apt upgrade\n")
    else:
        ui.warning(
            f'System update for operation system "{plan.distribution}" '
            "is not supported yet. Skipped."
        )


def _run_retropie_procedures(session: ImageSession, public_key_path: str) -> None:
    if public_key_path:
        (session.boot_mount_path / "ssh").write_text("\n")
    if not ui.confirm("Should the RetroFlag specific procedures be executed?"):
        return
    ui.info("Executing RetroFlag specific procedures...")
    chroot_bash(
        session.root_mount_path,
        'wget -O - "https://raw.githubusercontent.com/RetroFlag/'
        'retroflag-picase/master/install_gpi.sh" | bash\n',
    )


def _configure_users_and_keys(session: ImageSession) -> tuple[str, Path]:
    """Handle user rename, sudo rights and SSH key; return (public key path, authorized_keys)."""
    root = session.root_mount_path
    ui.info("Define target paths...")
    default_username, target_username = _select_target_user(root)
    renamed = default_username != target_username
    target_user_ssh_folder = root / "home" / target_username / ".ssh"
    target_authorized_keys = target_user_ssh_folder / "authorized_keys"

    if ui.confirm(f"Should the {target_username} have sudo rights? "):
        configure_sudoers(root, target_username)

    public_key_path = ui.ask(
        "Enter the path to the SSH key to be added to the image (default: none):"
    )
    if public_key_path:
        configure_ssh_key(public_key_path, target_user_ssh_folder, target_authorized_keys)
    else:
        ui.info("Skipped SSH-key copying..")

    ui.info("Start chroot procedures...")
    session.mount_chroot_binds()
    session.copy_qemu()
    session.copy_resolv_conf()

    chroot_user_home = f"/home/{target_username}/"
    if renamed:
        ui.info("Delete old user and create new user")
        chroot_bash(
            root,
            f"userdel -r {default_username}\n"
            f"useradd -m -d {chroot_user_home} -s /bin/bash {target_username}\n"
            f"chown -R {target_username}:{target_username} {chroot_user_home}\n",
            error_msg="Failed to delete old user and create new user",
        )

    if public_key_path:
        ui.info("Chroot to set ownership...")
        chroot_bash(
            root,
            f"chown -vR {target_username}:{target_username} {chroot_user_home}.ssh\n",
        )

    _change_passwords(root, target_username)
    return public_key_path, target_authorized_keys


def configure_raspberry_image(plan: ImagePlan, session: ImageSession) -> None:
    _ensure_image_mounted(session)
    root = session.root_mount_path
    _seed_boot_uuid(session)

    public_key_path, target_authorized_keys = _configure_users_and_keys(session)

    _configure_hostname(root)

    if plan.distribution in ("arch", "manjaro"):
        ui.info("Populating keys...")
        chroot_bash(
            root,
            "yes | pacman-key --init\nyes | pacman-key --populate archlinuxarm\n",
        )

    _update_system(plan, root)

    ui.info(f"Installing software for filesystem {plan.root_filesystem}...")
    if plan.root_filesystem == "btrfs":
        install_packages(plan.distribution, root, "btrfs-progs")
    else:
        ui.info("Skipped.")

    if plan.encrypt_system:
        configure_encryption(plan, session, target_authorized_keys)

    ui.info("Running system specific procedures...")
    if plan.distribution == "retropie":
        _run_retropie_procedures(session, public_key_path)
