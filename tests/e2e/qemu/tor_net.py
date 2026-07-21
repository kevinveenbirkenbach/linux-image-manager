"""Tor network providers for the QEMU unlock harness.

Two interchangeable ways to give the harness a working SOCKS port that can
reach the guest's onion service:

* PublicTorClient - a local tor client on the public network (default, both
  the guest's baked-in torrc and this client use the real Tor authorities).
* ChutneyNetwork - a private, deterministic, offline Tor network via the
  official `chutney` tool. Fully private operation also needs the image
  built against the same authorities; test_network_conf() emits the file
  build_image.sh consumes for that (see README.md).

Both expose ``socks_port``, ``start()`` and ``stop()``.
"""

import subprocess
import time
from pathlib import Path

BOOTSTRAP_TIMEOUT = 180
_GUEST_HOST_ALIAS = "10.0.2.2"  # QEMU user-net alias for the host's 127.0.0.1


class PublicTorClient:
    """A throwaway tor client bootstrapped against the public network."""

    def __init__(self, work_dir: Path, socks_port: int) -> None:
        self.socks_port = socks_port
        self.test_network_conf: Path | None = None
        self._work_dir = work_dir
        self._log = work_dir / "tor-client.log"
        self._data = work_dir / "tor-client-data"
        self._process: subprocess.Popen | None = None

    def start(self) -> None:
        self._data.mkdir(parents=True, exist_ok=True)
        self._data.chmod(0o700)
        # An empty -f keeps the system /etc/tor/torrc (User tor, ...) out of
        # this rootless client, which would otherwise refuse to start.
        empty_torrc = self._work_dir / "tor-client-torrc"
        empty_torrc.write_text("")
        self._process = subprocess.Popen(
            [
                "tor", "-f", str(empty_torrc),
                "--SocksPort", str(self.socks_port),
                "--DataDirectory", str(self._data),
                "--Log", f"notice file {self._log}",
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _wait_for_bootstrap(self._log, self._process)

    def stop(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            # Never leak a tor holding the fixed SOCKS port into the next run.
            self._process.kill()
            self._process.wait(timeout=5)


class ChutneyNetwork:
    """A private Tor network managed by the chutney tool."""

    def __init__(self, chutney_path: Path, work_dir: Path, network: str) -> None:
        self._chutney = chutney_path
        self._network = network
        self._work_dir = work_dir
        self.socks_port = 0
        self.test_network_conf: Path | None = None

    def _run(self, *args: str) -> None:
        subprocess.run(
            [str(self._chutney / "chutney"), *args, self._network],
            cwd=self._chutney, check=True,
        )

    def start(self) -> None:
        self._run("configure")
        self._run("start")
        self._run("wait_for_bootstrap")
        client_torrc = _find_client_torrc(self._chutney / "net" / "nodes")
        self.socks_port = _parse_socks_port(client_torrc)
        self.test_network_conf = self._emit_network_conf(client_torrc)

    def _emit_network_conf(self, client_torrc: Path) -> Path:
        """Distil the authority/test-network lines the guest image needs.

        127.0.0.1 authority addresses are rewritten to the QEMU user-net host
        alias so the guest's initramfs tor can reach them through user-mode
        networking.
        """
        wanted = ("TestingTorNetwork", "DirAuthority", "DirServer", "AlternateDirAuthority")
        lines = [
            line.replace("127.0.0.1", _GUEST_HOST_ALIAS)
            for line in client_torrc.read_text().splitlines()
            if line.strip().startswith(wanted)
        ]
        conf = self._work_dir / "tor-test-network.conf"
        conf.write_text("\n".join(lines) + "\n")
        return conf

    def stop(self) -> None:
        self._run("stop")


def _wait_for_bootstrap(log_path: Path, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + BOOTSTRAP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"tor exited early (code {process.returncode}).\n{_log_tail(log_path)}"
            )
        if log_path.is_file() and "Bootstrapped 100%" in log_path.read_text():
            return
        time.sleep(1)
    raise RuntimeError(f"tor client did not bootstrap in time.\n{_log_tail(log_path)}")


def _log_tail(log_path: Path, lines: int = 8) -> str:
    if not log_path.is_file():
        return "(no tor log written)"
    tail = log_path.read_text().splitlines()[-lines:]
    return "tor log:\n  " + "\n  ".join(tail)


def _find_client_torrc(nodes_dir: Path) -> Path:
    for torrc in sorted(nodes_dir.glob("*/torrc")):
        if _parse_socks_port(torrc):
            return torrc
    raise RuntimeError(f"No chutney client with a SocksPort under {nodes_dir}.")


def _parse_socks_port(torrc: Path) -> int:
    if not torrc.is_file():
        return 0
    for line in torrc.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "SocksPort" and parts[1].isdigit():
            port = int(parts[1])
            if port:
                return port
    return 0
