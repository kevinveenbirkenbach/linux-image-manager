"""Mount an image and open an interactive shell inside it."""

from lim import device as device_module
from lim import runner, ui
from lim.image.session import ImageSession


def run_chroot() -> None:
    ui.info("Starting chroot...")
    device = device_module.select_device()
    session = ImageSession(device)
    try:
        session.make_working_folder()
        session.make_mount_folders()
        session.decrypt_root()
        session.mount_partitions()
        session.mount_chroot_binds()
        session.copy_qemu()
        session.copy_resolv_conf()
        ui.info("Bash shell starts...")
        runner.run(["chroot", str(session.root_mount_path), "/bin/bash"], sudo=True)
    finally:
        session.destructor()
