"""Repository paths shared by all modules."""

from pathlib import Path

REPOSITORY_PATH = Path(__file__).resolve().parent.parent
CONFIGURATION_PATH = REPOSITORY_PATH / "configuration"
PACKAGE_PATH = CONFIGURATION_PATH / "packages"
ENCRYPTED_PATH = REPOSITORY_PATH / ".encrypted"
DECRYPTED_PATH = REPOSITORY_PATH / "decrypted"
DATA_PATH = DECRYPTED_PATH / "data"
BACKUP_PATH = DECRYPTED_PATH / "backup"
