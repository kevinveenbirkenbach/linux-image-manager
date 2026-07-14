"""Read-only access to the image catalog (distributions.yml in the package)."""

from functools import cache

import yaml

from lim import config

CATALOG_PATH = config.CATALOG_PATH


@cache
def _load() -> dict:
    with CATALOG_PATH.open() as handle:
        return yaml.safe_load(handle)


def arch_rpi_images() -> dict[str, dict[str, str]]:
    return _load()["arch_rpi_images"]


def manjaro_gnome_releases() -> dict[str, dict[str, str]]:
    return _load()["manjaro_gnome_releases"]


def retropie_images() -> dict[str, dict[str, str]]:
    return _load()["retropie_images"]


def mkinitcpio_modules_by_rpi() -> dict[str, str]:
    return _load()["mkinitcpio_modules_by_rpi"]
