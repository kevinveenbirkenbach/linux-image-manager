"""Package and repository paths shared by all modules.

Configuration and the image catalog ship inside the package so that
wheel installs work; the encfs data store stays repository-relative.
"""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIGURATION_PATH = PACKAGE_ROOT / "configuration"
PACKAGE_PATH = CONFIGURATION_PATH / "packages"
CATALOG_PATH = PACKAGE_ROOT / "distributions.yml"

REPOSITORY_PATH = PACKAGE_ROOT.parent
ENCRYPTED_PATH = REPOSITORY_PATH / ".encrypted"
DECRYPTED_PATH = REPOSITORY_PATH / "decrypted"
DATA_PATH = DECRYPTED_PATH / "data"
BACKUP_PATH = DECRYPTED_PATH / "backup"
