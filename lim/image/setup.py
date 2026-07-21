"""Interactive Linux image setup: download, verify, transfer, configure.

Reference for encrypted Raspberry Pi images:
https://wiki.polaire.nl/doku.php?id=archlinux-raspberry-encrypted
"""

import pwd
from pathlib import Path

from lim import device as device_module
from lim import system, ui
from lim.errors import LimError
from lim.image import choosers, transfer, verify
from lim.image.plan import ImagePlan
from lim.image.raspberry import configure_raspberry_image
from lim.image.session import ImageSession


def _prepare_image_folder(plan: ImagePlan) -> None:
    ui.info("Configure user...")
    origin_username = ui.ask("Please type in a valid working username:")
    try:
        pwd.getpwnam(origin_username)
    except KeyError:
        raise LimError(f"User {origin_username} doesn't exist.") from None

    ui.info("Image routine starts...")
    plan.image_folder = Path(f"/home/{origin_username}/Software/Images")
    ui.info(f'The images will be stored in "{plan.image_folder}".')
    if not plan.image_folder.is_dir():
        ui.info(f'Folder "{plan.image_folder}" doesn\'t exist. It will be created now.')
        plan.image_folder.mkdir(parents=True)


def _select_unmounted_device() -> device_module.Device:
    device = device_module.select_device()
    if device_module.is_mounted(device.path):
        raise LimError(
            f'Device {device.path} is allready mounted. '
            f'Umount with "umount {device.path}*".'
        )
    return device


def _choose_and_verify_image(plan: ImagePlan) -> None:
    plan.operation_system = ui.ask(
        "Which operation system would you like to use [linux,windows,...]?"
    )
    if plan.operation_system == "linux":
        choosers.choose_linux_image(plan)
        plan.encrypt_system = ui.confirm("Should the system be encrypted?")
        if plan.encrypt_system:
            plan.tor_unlock = ui.confirm(
                "Should the system be remotely unlockable via a Tor onion service?"
            )
        ui.info("Generating os-image...")
        transfer.download_image(plan)
    else:
        choosers.choose_local_image(plan)

    ui.info("Verifying image...")
    ui.info("Verifying checksum...")
    if plan.image_checksum is None and plan.download_url is not None:
        plan.image_checksum = verify.resolve_checksum(plan.download_url)
    verify.verify_checksum(plan.image_path, plan.image_checksum)
    if plan.download_url is not None:
        verify.verify_signature(plan.download_url, plan.image_path, plan.image_folder)


def run_setup() -> None:
    ui.info("Setupscript for images started...")
    ui.info("Checking if root...")
    if not system.is_root():
        raise LimError("This script must be executed as root!")

    plan = ImagePlan()
    _prepare_image_folder(plan)
    device = _select_unmounted_device()
    _choose_and_verify_image(plan)

    session = ImageSession(device)
    try:
        session.make_working_folder()
        session.make_mount_folders()

        plan.root_filesystem = ui.ask(
            "Which filesystem should be used? E.g.:btrfs,ext4... (none):"
        )

        if ui.confirm(f"Should the image be transfered to {device.path}?"):
            transfer.transfer_image(plan, session)
        else:
            ui.info("Skipping image transfer...")

        if plan.raspberry_pi_version:
            configure_raspberry_image(plan, session)
    finally:
        session.destructor()

    ui.success("Setup successfull :)")
