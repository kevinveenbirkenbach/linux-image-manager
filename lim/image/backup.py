"""Create an image backup from a memory device into a file."""

from pathlib import Path

from lim import device as device_module
from lim import runner, ui


def run_backup() -> None:
    ui.info("Backupscript for memory devices started...")
    print()
    device = device_module.select_device()

    working_dir = Path.cwd()
    path = ""
    while not path:
        path = ui.ask(f"Please type in backup image path+name relative to {working_dir}:")
    output_file = f"{path}.img" if path.startswith("/") else f"{working_dir}/{path}.img"

    ui.info(f"Input file: {device.path}")
    ui.info(f"Output file: {output_file}")
    ui.ask('Please confirm by pushing "Enter". To cancel use "Ctrl + C"')

    ui.info("Imagetransfer starts. This can take a while...")
    runner.run(
        ["dd", f"if={device.path}", f"of={output_file}", "bs=1M", "status=progress"],
        sudo=True,
        error_msg='"dd" failed.',
    )
    runner.sync_disks()

    ui.success("Imagetransfer successfull.")
