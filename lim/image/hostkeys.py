import os
import pwd
import re
from pathlib import Path

KNOWN_HOSTS_SUBPATH = ".config/lim/known_hosts"
SSH_CONFIG_SUBPATH = ".ssh/config"


def host_key_alias(name: str) -> str:
    return f"boot.{name}"


def known_hosts_path(home: Path) -> Path:
    return home / KNOWN_HOSTS_SUBPATH


def replace_known_hosts(text: str, alias: str, public_keys: list[str]) -> str:
    kept = [line for line in text.splitlines() if line.split(" ", 1)[0] != alias]
    pinned = [f"{alias} {' '.join(key.split()[:2])}" for key in public_keys]
    return "\n".join([*kept, *pinned]) + "\n"


def replace_config_block(text: str, alias: str, block: str) -> str:
    begin, end = f"# lim:{alias}:begin", f"# lim:{alias}:end"
    pattern = rf"^{re.escape(begin)}\n.*?^{re.escape(end)}\n?"
    kept = re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)
    if kept and not kept.endswith("\n"):
        kept += "\n"
    return f"{kept}{begin}\n{block}{end}\n"


def config_block(alias: str, target: str, identity_file: str, known_hosts: Path) -> str:
    lines = [
        f"Host {alias}",
        f"  HostName {target}",
        "  User root",
        f"  HostKeyAlias {alias}",
        f"  UserKnownHostsFile {known_hosts}",
        "  StrictHostKeyChecking yes",
    ]
    if identity_file:
        lines.append(f"  IdentityFile {identity_file}")
    return "\n".join(lines) + "\n"


def _write_owned(path: Path, text: str, owner: pwd.struct_passwd) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)
    for entry in (path, path.parent):
        os.chown(entry, owner.pw_uid, owner.pw_gid)


def pin(
    owner: pwd.struct_passwd, name: str, target: str, identity_file: str, public_keys: list[str]
) -> str:
    """Write the pinned keys and a ``Host boot.<name>`` ssh config block; return the alias.

    Args:
        owner: passwd entry of the operator whose home receives the files.
        name: unlock record name; the alias becomes ``boot.<name>``.
        target: onion address or host/IP the initramfs answers on.
        identity_file: private key path for the unlock, empty for ssh defaults.
        public_keys: OpenSSH ``type base64 [comment]`` lines the initramfs serves.

    """
    home = Path(owner.pw_dir)
    alias = host_key_alias(name)
    known_hosts = known_hosts_path(home)
    current = known_hosts.read_text() if known_hosts.is_file() else ""
    _write_owned(known_hosts, replace_known_hosts(current, alias, public_keys), owner)
    ssh_config = home / SSH_CONFIG_SUBPATH
    current = ssh_config.read_text() if ssh_config.is_file() else ""
    block = config_block(alias, target, identity_file, known_hosts)
    _write_owned(ssh_config, replace_config_block(current, alias, block), owner)
    return alias
