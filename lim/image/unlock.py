"""Remote LUKS boot unlock over the initramfs SSH/dropbear session.

Reaches the waiting initramfs either through a Tor onion address (wrapped in
torsocks) or a plain host/IP, then either runs cryptroot-unlock (initramfs-tools
targets) or drops into the passphrase prompt (mkinitcpio encryptssh).
"""

import json
import os
from pathlib import Path

from lim import runner, ui
from lim.errors import LimError

RECORDS_SUBPATH = ".config/lim/unlocks"


def records_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / RECORDS_SUBPATH


def build_unlock_argv(target: str, key: str, unlock_command: str) -> list[str]:
    """SSH invocation for the unlock; torsocks-wrapped for .onion targets.

    The initramfs dropbear key differs from the booted host key, so host-key
    checking is disabled; a v3 onion address authenticates the endpoint itself.
    """
    ssh = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    if key:
        ssh += ["-i", str(Path(key).expanduser())]
    if unlock_command:
        ssh += ["-t"]  # PTY so the remote passphrase prompt is interactive
    ssh += [f"root@{target}"]
    if unlock_command:
        ssh += [unlock_command]
    if target.endswith(".onion"):
        return ["torsocks", *ssh]
    return ssh


def save_record(home: Path, uid: int, gid: int, name: str, record: dict) -> None:
    """Persist an unlock target under the target user's home, owned by them."""
    directory = records_dir(home)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(record, indent=2) + "\n")
    try:
        for entry in (path, directory, directory.parent, directory.parent.parent):
            os.chown(entry, uid, gid)
    except OSError:
        pass


def _read_record(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _load_records() -> list[tuple[str, dict]]:
    directory = records_dir()
    if not directory.is_dir():
        return []
    loaded = ((path.stem, _read_record(path)) for path in sorted(directory.glob("*.json")))
    return [(name, record) for name, record in loaded if record is not None]


def _select_record() -> dict | None:
    records = _load_records()
    if not records:
        return None
    ui.info("Saved unlock targets:")
    for index, (name, record) in enumerate(records, 1):
        ui.info(f"  {index}) {name} -> {record.get('target')}")
    answer = ui.ask("Pick a number, or Enter for manual entry:")
    if answer.isdigit() and 1 <= int(answer) <= len(records):
        return records[int(answer) - 1][1]
    return None


def remote_unlock() -> None:
    record = _select_record()
    if record:
        target = record["target"]
        key = record.get("key", "")
        unlock_command = record.get("unlock_command", "")
    else:
        target = ui.ask("Onion address or host/IP to unlock:")
        if not target:
            raise LimError("No target given.")
        key = ui.ask("Path to the SSH private key (empty for ssh defaults):")
        unlock_command = (
            "cryptroot-unlock"
            if ui.confirm("Debian / Raspberry Pi OS target (run cryptroot-unlock)?")
            else ""
        )
    if target.endswith(".onion"):
        ui.info("Routing through Tor (torsocks); a local tor must be running.")
    runner.run(build_unlock_argv(target, key, unlock_command), check=False)
