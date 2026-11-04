"""Orchestrate the full virtualized unlock: build -> tor net -> boot -> unlock.

Wires the stages together and owns their teardown. Kept thin so each stage
stays independently testable; the pure command construction lives in
config.py and is unit-tested without any of this running.
"""

import os
import platform
import socket
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from lim.image import hostkeys
from lim.image.initramfs import get_backend
from tests.e2e.qemu import boot_unlock, config, tor_net
from tests.e2e.qemu.config import QemuSpec

IMAGE_ENV_NAME = "image.env"
_SUDO_REFRESH_INTERVAL = 60

DEFAULT_PASSPHRASE = "lim-e2e-luks-passphrase"  # noqa: S105 (throwaway test secret)
DEFAULT_ARCH = "x86_64"
DEFAULT_SOCKS_PORT = 9052


@dataclass
class HarnessConfig:
    repo_root: Path
    work_dir: Path
    arch: str = DEFAULT_ARCH
    passphrase: str = DEFAULT_PASSPHRASE
    chutney_path: Path | None = None
    chutney_network: str = "networks/basic"
    os_family: str = "arch"  # "arch" (pacstrap) or "debian" (debootstrap)
    # "direct" (deterministic; QEMU port-forward to dropbear) or "tor" (full
    # onion transport, opt-in — flaky over public Tor inside QEMU).
    unlock_transport: str = "direct"


class _NullNet:
    """Stand-in tor network for the direct transport: no Tor needed."""

    socks_port = 0
    test_network_conf: Path | None = None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# Per-OS build script and the remote command that delivers the passphrase.
_BUILD_SCRIPT = {"arch": "build_image.sh", "debian": "build_image_debian.sh"}
_UNLOCK_COMMAND = {"arch": "", "debian": "cryptroot-unlock"}
_PIN_DISTRIBUTION = {"arch": "arch", "debian": "raspios"}


def choose_accel(arch: str) -> str:
    """Use KVM only when the guest arch matches the host and /dev/kvm exists."""
    host = "x86_64" if platform.machine() in ("x86_64", "AMD64") else platform.machine()
    if arch == host and Path("/dev/kvm").exists():
        return "kvm"
    return "tcg"


def _generate_ssh_key(work_dir: Path) -> Path:
    key_path = work_dir / "unlock_key"
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(key_path), "-q"],
        check=True,
    )
    return key_path


class _SudoKeepalive:
    """Refresh the cached sudo credential so the long build never re-prompts.

    The password is entered once, up front (before the slow tor bootstrap),
    then a background thread keeps the timestamp warm until stop().
    """

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self._stop.wait(_SUDO_REFRESH_INTERVAL):
            subprocess.run(["sudo", "-n", "-v"], check=False)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def _acquire_sudo() -> _SudoKeepalive | None:
    """Prompt for sudo once now; return a keepalive (None when already root)."""
    if os.geteuid() == 0:
        return None
    print("\n[harness] The build stage needs root — enter your sudo password now.")
    subprocess.run(["sudo", "-v"], check=True)
    keepalive = _SudoKeepalive()
    keepalive.start()
    return keepalive


def _build_image(cfg: HarnessConfig, ssh_key: Path, test_network_conf: Path | None) -> None:
    script = cfg.repo_root / "tests/e2e/qemu" / _BUILD_SCRIPT[cfg.os_family]
    env = {
        **os.environ,
        "WORK_DIR": str(cfg.work_dir),
        "REPO_ROOT": str(cfg.repo_root),
        "ARCH": cfg.arch,
        "PASSPHRASE": cfg.passphrase,
        "SSH_PUBKEY": f"{ssh_key}.pub",
    }
    if test_network_conf is not None:
        env["TOR_TEST_NETWORK_CONF"] = str(test_network_conf)
    # -n: never prompt here; the credential was primed by _acquire_sudo().
    prefix = [] if os.geteuid() == 0 else ["sudo", "-n", "-E"]
    subprocess.run([*prefix, "bash", str(script)], env=env, check=True)
    # Hand the root-built artifacts back so rootless QEMU can read them.
    _reclaim_work_dir(cfg, required=True)


def _reclaim_work_dir(cfg: HarnessConfig, *, required: bool = False) -> None:
    """Reclaim the root-built work dir for the invoking user via chown.

    Needed before boot so rootless QEMU can read the image, and again in the
    finally so a failed build never leaves root-owned files that the pytest
    tmp cleanup then cannot remove.
    """
    if os.geteuid() == 0 or not cfg.work_dir.exists():
        return
    subprocess.run(
        ["sudo", "-n", "chown", "-R", str(os.getuid()), str(cfg.work_dir)],
        check=required,
    )


def _pin_host_keys(cfg: HarnessConfig) -> None:
    distribution = _PIN_DISTRIBUTION[cfg.os_family]
    keys = get_backend(distribution).host_public_keys(cfg.work_dir / "rootfs")
    if not keys:
        raise RuntimeError("lim found no initramfs host key in the built rootfs.")
    known_hosts = cfg.work_dir / "known_hosts"
    known_hosts.write_text(hostkeys.replace_known_hosts("", config.HOST_KEY_ALIAS, keys))


def _make_tor_net(cfg: HarnessConfig):
    if cfg.unlock_transport == "direct":
        return _NullNet()
    if cfg.chutney_path is not None:
        return tor_net.ChutneyNetwork(cfg.chutney_path, cfg.work_dir, cfg.chutney_network)
    return tor_net.PublicTorClient(cfg.work_dir, DEFAULT_SOCKS_PORT)


def _load_spec(cfg: HarnessConfig, ssh_key: Path, socks_port: int) -> QemuSpec:
    env = boot_unlock.parse_env_file(cfg.work_dir / IMAGE_ENV_NAME)
    direct_port = _free_port() if cfg.unlock_transport == "direct" else 0
    return QemuSpec(
        arch=cfg.arch,
        work_dir=cfg.work_dir,
        image_path=Path(env["IMAGE"]),
        kernel_path=Path(env["KERNEL"]),
        initramfs_path=Path(env["INITRAMFS"]),
        luks_uuid=env["LUKS_UUID"],
        mapper_name=env["MAPPER_NAME"],
        onion_address=env["ONION_ADDRESS"],
        passphrase=cfg.passphrase,
        ssh_key_path=ssh_key,
        socks_port=socks_port,
        accel=choose_accel(cfg.arch),
        os_family=cfg.os_family,
        unlock_command=_UNLOCK_COMMAND[cfg.os_family],
        direct_ssh_port=direct_port,
    )


def run(cfg: HarnessConfig) -> QemuSpec:
    """Execute every stage; return the QemuSpec on a fully verified unlock.

    A chutney network must exist before the build so the image can be wired
    to its authorities; a public client only needs to be up before boot.
    """
    cfg.work_dir.mkdir(parents=True, exist_ok=True)
    ssh_key = _generate_ssh_key(cfg.work_dir)
    # Prime sudo before the slow tor bootstrap so the prompt is the first thing
    # the operator sees, not a surprise five minutes in.
    sudo = _acquire_sudo()
    net = _make_tor_net(cfg)
    try:
        if cfg.unlock_transport != "direct":
            print("\n[harness] bootstrapping Tor client (~30-60s)...", flush=True)
        net.start()
        print(
            f"[harness] transport={cfg.unlock_transport}, building encrypted "
            "image (several minutes)...",
            flush=True,
        )
        _build_image(cfg, ssh_key, net.test_network_conf)
        _pin_host_keys(cfg)
        spec = _load_spec(cfg, ssh_key, net.socks_port)
        boot_unlock.boot_and_unlock(spec)
        return spec
    finally:
        # Reclaim ownership FIRST so a slow/failing teardown can never leave
        # root-owned files behind, and isolate each step so none masks the
        # real error propagating out of the try or skips the others.
        _reclaim_work_dir(cfg)
        try:
            net.stop()
        except Exception as exc:  # noqa: BLE001 - teardown must not mask the real failure
            print(f"[harness] tor network teardown failed: {exc}", flush=True)
        if sudo is not None:
            try:
                sudo.stop()
            except Exception as exc:  # noqa: BLE001 - teardown must not mask the real failure
                print(f"[harness] sudo keepalive teardown failed: {exc}", flush=True)
