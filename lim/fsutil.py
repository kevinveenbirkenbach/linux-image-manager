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
