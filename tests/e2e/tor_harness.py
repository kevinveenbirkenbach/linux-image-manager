"""Rootless helpers to stand up a real Tor onion service and reach it.

These reproduce, without root/block-devices/chroot, what the "tor"
mkinitcpio hook does at LUKS-decryption time: generate v3 onion keys
offline, run a real Tor onion service that forwards the virtual port 22
to a local "dropbear", and let a client reach that service through Tor.
"""

import socket
import struct
import subprocess
import threading
import time
from pathlib import Path

# Matches lim.image.tor._KEYGEN_SCRIPT: an empty -f torrc keeps the host's
# /etc/tor/torrc out of the run, --DisableNetwork 1 makes the keys appear
# without ever touching the network.
KEYGEN_TIMEOUT = 30
BOOTSTRAP_TIMEOUT = 180
ONION_CONNECT_TIMEOUT = 90


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def generate_onion_keys(onion_dir: Path, data_dir: Path) -> str:
    """Create v3 onion keys offline; return the .onion hostname.

    Mirrors lim.image.tor._KEYGEN_SCRIPT, run directly on the host instead
    of inside the image chroot (the tor invocation is identical).
    """
    onion_dir.mkdir(parents=True, exist_ok=True)
    onion_dir.chmod(0o700)
    empty_torrc = data_dir.parent / "keygen-torrc"
    empty_torrc.write_text("")
    process = subprocess.Popen(
        [
            "tor", "-f", str(empty_torrc), "--DisableNetwork", "1",
            "--DataDirectory", str(data_dir),
            "--HiddenServiceDir", str(onion_dir),
            "--HiddenServicePort", "22 127.0.0.1:22",
            "--SocksPort", "0", "--RunAsDaemon", "0", "--Log", "notice stderr",
        ],
        stderr=subprocess.DEVNULL,
    )
    hostname = onion_dir / "hostname"
    try:
        deadline = time.monotonic() + KEYGEN_TIMEOUT
        while time.monotonic() < deadline:
            if hostname.is_file() and hostname.read_text().strip():
                break
            time.sleep(0.5)
    finally:
        process.terminate()
        process.wait(timeout=10)
    if not (hostname.is_file() and hostname.read_text().strip()):
        raise RuntimeError("Offline onion key generation produced no hostname.")
    return hostname.read_text().strip()


def start_onion_service(
    torrc_path: Path, socks_port: int, log_path: Path
) -> subprocess.Popen:
    """Start Tor with the given torrc (service side) plus a SOCKS port.

    The torrc carries the HiddenServiceDir/HiddenServicePort just like the
    baked-in image torrc; --SocksPort lets the same instance also act as the
    client's entry point so the test needs only one bootstrap.
    """
    return subprocess.Popen(
        [
            "tor", "-f", str(torrc_path),
            "--SocksPort", str(socks_port),
            "--Log", f"notice file {log_path}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_bootstrapped(log_path: Path, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + BOOTSTRAP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Tor exited early (code {process.returncode}).")
        if log_path.is_file() and "Bootstrapped 100%" in log_path.read_text():
            return
        time.sleep(1)
    raise RuntimeError("Tor did not bootstrap in time.")


def _socks5_handshake(sock: socket.socket, onion_host: str, onion_port: int) -> None:
    sock.sendall(b"\x05\x01\x00")  # VER, 1 method, no-auth
    if sock.recv(2) != b"\x05\x00":
        raise RuntimeError("SOCKS5 handshake rejected.")
    host = onion_host.encode()
    request = (
        b"\x05\x01\x00\x03"
        + bytes([len(host)]) + host
        + struct.pack(">H", onion_port)
    )
    sock.settimeout(ONION_CONNECT_TIMEOUT)
    sock.sendall(request)
    header = sock.recv(4)
    if len(header) < 2 or header[1] != 0x00:
        code = header[1] if len(header) >= 2 else -1
        raise RuntimeError(f"SOCKS5 CONNECT failed (reply code {code}).")
    # Drain the bound-address tail so the stream starts at real payload.
    atyp = header[3]
    tail = {0x01: 4, 0x04: 16}.get(atyp)
    if tail is None:  # domain name
        tail = sock.recv(1)[0]
    sock.recv(tail + 2)


def socks5_connect(socks_port: int, onion_host: str, onion_port: int) -> socket.socket:
    """Open a stream to onion_host:onion_port through Tor's SOCKS5 proxy."""
    sock = socket.create_connection(("127.0.0.1", socks_port), timeout=30)
    try:
        _socks5_handshake(sock, onion_host, onion_port)
    except (OSError, RuntimeError):
        sock.close()
        raise
    return sock


class FakeDropbear:
    r"""Stand-in for the initramfs dropbear+cryptsetup unlock endpoint.

    Accepts one connection on 127.0.0.1:<port>, reads a passphrase line, and
    replies "UNLOCKED\n" — the observable proof that a passphrase delivered
    over the onion connection reached the unlock shell.
    """

    def __init__(self, port: int) -> None:
        self.port = port
        self.received: bytes | None = None
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", port))
        self._server.listen(1)
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _serve(self) -> None:
        try:
            self._server.settimeout(BOOTSTRAP_TIMEOUT + ONION_CONNECT_TIMEOUT)
            conn, _ = self._server.accept()
            with conn:
                conn.settimeout(ONION_CONNECT_TIMEOUT)
                self.received = conn.recv(4096).strip()
                conn.sendall(b"UNLOCKED\n")
        except OSError:
            pass

    def stop(self) -> None:
        self._server.close()
        self._thread.join(timeout=5)


def write_test_torrc(path: Path, data_dir: Path, onion_dir: Path, backend_port: int) -> None:
    """Write a torrc mirroring the baked-in one, with test-writable paths.

    The virtual onion port stays 22 (as in production); only the loopback
    backend and the data/key directories move to rootless temp locations.
    """
    path.write_text(
        f"DataDirectory {data_dir}\n"
        f"HiddenServiceDir {onion_dir}\n"
        f"HiddenServicePort 22 127.0.0.1:{backend_port}\n"
        "SocksPort 0\n"
    )
