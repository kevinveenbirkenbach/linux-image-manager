"""Import personal data from the system into the encrypted store, or export it back."""

import time
from dataclasses import dataclass
from pathlib import Path

from lim import config, runner, system, ui
from lim.data import crypt
from lim.errors import LimError

# Paths relative to $HOME; trailing "/" marks a directory tree.
BACKUP_ITEMS = [
    ".ssh/",
    ".gitconfig",
    ".atom/config.cson",
    ".projectlibre/projectlibre.conf",
    ".local/share/rhythmbox/rhythmdb.xml",
    ".config/keepassxc/keepassxc.ini",
    "Documents/certificates/",
    "Documents/security/",
    "Documents/identity/",
    "Documents/health/",
    "Documents/licenses/",
]


@dataclass(frozen=True)
class SyncOperation:
    source: str
    destination: str
    backup_dir: str
    is_directory: bool


def build_sync_plan(
    mode: str,
    home: Path,
    data_path: Path,
    backup_folder: Path,
) -> list[SyncOperation]:
    """One rsync operation per existing backup item; missing sources are skipped."""
    operations = []
    for item in BACKUP_ITEMS:
        is_directory = item.endswith("/")
        system_path = home / item
        # The store mirrors the absolute system path below DATA_PATH.
        data_path_item = Path(f"{data_path}{system_path}")
        if mode == "export":
            source, destination = data_path_item, system_path
        elif mode == "import":
            source, destination = system_path, data_path_item
        else:
            raise LimError(f"Unknown sync mode: {mode}")
        ui.info(f"{mode.capitalize()} data from {source} to {destination}...")
        if not (source.is_file() or source.is_dir()):
            ui.warning(f"{source} doesn't exist. Copying data is not possible.")
            continue
        if is_directory:
            backup_dir = Path(f"{backup_folder}{system_path}")
        else:
            backup_dir = Path(f"{backup_folder}{system_path}").parent
        operations.append(
            SyncOperation(
                source=f"{source}/" if is_directory else str(source),
                destination=f"{destination}/" if is_directory else str(destination),
                backup_dir=str(backup_dir),
                is_directory=is_directory,
            )
        )
    return operations


def rsync_command(operation: SyncOperation) -> list[str]:
    command = ["rsync", "-abcEPuvW"]
    if operation.is_directory:
        command.append("--delete")
    command += [f"--backup-dir={operation.backup_dir}", operation.source, operation.destination]
    return command


def execute_sync_plan(operations: list[SyncOperation]) -> None:
    for operation in operations:
        Path(operation.backup_dir).mkdir(parents=True, exist_ok=True)
        destination_dir = (
            Path(operation.destination)
            if operation.is_directory
            else Path(operation.destination).parent
        )
        destination_dir.mkdir(parents=True, exist_ok=True)
        if not operation.is_directory and Path(operation.destination).is_file():
            ui.info("The destination file already exists!")
            ui.info("Difference:")
            runner.run(["diff", operation.destination, operation.source], check=False)
        runner.run(rsync_command(operation))


def ensure_unlocked() -> None:
    mounts = runner.output(["mount"], check=False)
    if str(config.DECRYPTED_PATH) not in mounts:
        ui.info(f"The decrypted folder {config.DECRYPTED_PATH} is locked. You need to unlock it!")
        crypt.unlock()


def import_from_system(mode: str = "import") -> None:
    ensure_unlocked()
    backup_folder = config.BACKUP_PATH / mode / time.strftime("%Y%m%d%H%M%S")
    backup_folder.mkdir(parents=True, exist_ok=True)
    operations = build_sync_plan(mode, system.real_home(), config.DATA_PATH, backup_folder)
    execute_sync_plan(operations)


def export_to_system() -> None:
    import_from_system(mode="export")
    user = system.real_user()
    home = system.real_home()
    ui.info("Setting right permissions for imported files...")
    try:
        (home / ".ssh").chmod(0o700)
        for child in (home / ".ssh").rglob("*"):
            child.chmod(0o700 if child.is_dir() else 0o600)
    except OSError as exc:
        raise LimError(f"Failed to set correct ssh permissions: {exc}") from exc
    # Best effort without privilege escalation, like the original script.
    chowned = runner.run(["chown", "-R", f"{user}:{user}", str(home)], check=False)
    if chowned.returncode != 0:
        ui.warning(f'Not all files could be owned by user "{user}"...')
