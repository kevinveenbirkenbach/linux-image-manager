"""Small file manipulation helpers."""

from pathlib import Path

from lim import ui
from lim.errors import LimError


def replace_in_file(search: str, replace: str, path: str | Path) -> None:
    """Replace every literal occurrence of ``search``; fail when absent."""
    path = Path(path)
    text = path.read_text()
    new_text = text.replace(search, replace)
    if new_text == text:
        raise LimError(f"Search string '{search}' not found in {path}.")
    path.write_text(new_text)


def drop_fstab_mount(mount_point: str, path: str | Path) -> None:
    """Remove any (non-comment) fstab line whose mount point field equals mount_point.

    Lets a fresh mapper/boot entry replace a stock image's existing one instead
    of colliding with it. No-op when the file or a matching line is absent.
    """
    path = Path(path)
    if not path.exists():
        return
    kept = [
        line
        for line in path.read_text().splitlines()
        if line.lstrip().startswith("#") or line.split()[1:2] != [mount_point]
    ]
    path.write_text("".join(f"{line}\n" for line in kept))


def ensure_line_in_file(line: str, path: str | Path) -> bool:
    """Append ``line`` unless already present. Returns True when appended."""
    path = Path(path)
    content = path.read_text() if path.exists() else ""
    if line in content.splitlines():
        ui.warning(f"File {path} already contains the following entry:")
        print(line)
        ui.info("Skipped.")
        return False
    with path.open("a") as handle:
        if content and not content.endswith("\n"):
            handle.write("\n")
        handle.write(line + "\n")
    return True
