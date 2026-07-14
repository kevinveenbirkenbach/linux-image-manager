"""Reads package collections from configuration/packages/."""

from lim import config
from lim.errors import LimError


def get_packages(*collections: str) -> list[str]:
    """Package names from the given collections, comments stripped."""
    names: list[str] = []
    for collection in collections:
        path = config.PACKAGE_PATH / f"{collection}.txt"
        if not path.is_file():
            raise LimError(f"Package collection {path} does not exist.")
        for line in path.read_text().splitlines():
            name = line.split("#", 1)[0].strip()
            if name:
                names.append(name)
    return names
