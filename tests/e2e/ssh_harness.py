import getpass
import shutil
import socket
import subprocess
import time
from pathlib import Path

SSHD = shutil.which("sshd")
SSH = shutil.which("ssh")
SSH_KEYGEN = shutil.which("ssh-keygen")
PASSPHRASE = "correct horse battery staple"  # noqa: S105 (throwaway test secret)
_START_TIMEOUT = 10


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def keygen(path: Path, kind: str) -> str:
    """Create an unencrypted key pair at ``path``; return its public key line."""
    subprocess.run([SSH_KEYGEN, "-q", "-t", kind, "-N", "", "-C", "", "-f", str(path)], check=True)
    return path.with_suffix(".pub").read_text().strip()


class FakeInitramfs:
    """sshd serving one host key and an encryptssh-like passphrase prompt.

    Args:
        work_dir: scratch directory for keys, config, script and the received file.
        client_public_key: public key line authorized to log in.

    """

    def __init__(self, work_dir: Path, client_public_key: str) -> None:
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.port = free_port()
        self.received = work_dir / "received"
        self.host_public_key = keygen(work_dir / "host_key", "ecdsa")
        (work_dir / "authorized_keys").write_text(client_public_key + "\n")
        script = work_dir / "unlock.sh"
        script.write_text(
            "#!/bin/sh\n"
            "printf 'Enter passphrase for /dev/md1: '\n"
            "IFS= read -r line\n"
            f"printf '%s' \"$line\" > {self.received}\n"
            "echo UNLOCKED\n"
        )
        script.chmod(0o755)
        self.config = work_dir / "sshd_config"
        self.config.write_text(
            f"Port {self.port}\n"
            "ListenAddress 127.0.0.1\n"
            f"HostKey {work_dir / 'host_key'}\n"
            "PidFile none\n"
            "UsePAM no\n"
            "StrictModes no\n"
            f"AuthorizedKeysFile {work_dir / 'authorized_keys'}\n"
            "PasswordAuthentication no\n"
            "KbdInteractiveAuthentication no\n"
            f"ForceCommand {script}\n"
        )
        self.log = work_dir / "sshd.log"
        self.process: subprocess.Popen | None = None

    def __enter__(self):
        self.process = subprocess.Popen(
            [SSHD, "-D", "-e", "-f", str(self.config)],
            stdout=subprocess.DEVNULL,
            stderr=self.log.open("w"),
        )
        deadline = time.monotonic() + _START_TIMEOUT
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"sshd exited early:\n{self.log.read_text()}")
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=1).close()
            except OSError:
                time.sleep(0.1)
                continue
            return self
        raise RuntimeError(f"sshd never listened on {self.port}:\n{self.log.read_text()}")

    def __exit__(self, *_exc: object) -> None:
        if self.process is not None:
            self.process.terminate()
            self.process.wait(timeout=10)

    def passphrase_received(self) -> str | None:
        return self.received.read_text() if self.received.is_file() else None


def hermetic(argv: list[str], port: int, identity: Path, config: str) -> list[str]:
    """Rewrite a production ssh argv to reach the stand-in sshd as the invoking user.

    Args:
        argv: ssh argv as lim builds it, starting with ``ssh``.
        port: stand-in sshd port.
        identity: client private key.
        config: ssh config file for ``-F``.

    """
    user = getpass.getuser()
    rewritten = [part.replace("root@", f"{user}@", 1) for part in argv[1:]]
    return [
        SSH,
        "-F",
        config,
        "-p",
        str(port),
        "-l",
        user,
        "-i",
        str(identity),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        *rewritten,
    ]


def deliver(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        input=PASSPHRASE + "\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
