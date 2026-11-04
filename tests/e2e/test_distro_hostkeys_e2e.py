"""Opt-in, needs Docker: LIM_E2E_DOCKER=1 pytest tests/e2e/test_distro_hostkeys_e2e.py -v."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKER = shutil.which("docker")
_TIMEOUT = 900

pytestmark = pytest.mark.skipif(
    DOCKER is None or os.environ.get("LIM_E2E_DOCKER") != "1",
    reason="needs docker and LIM_E2E_DOCKER=1 (pulls images, installs packages)",
)

_SERVE_AND_SCAN = """
dropbear -F -E -p 127.0.0.1:2222 {keys} 2>/dev/null &
sleep 2
ssh-keyscan -p 2222 127.0.0.1 2>/dev/null | grep -v '^#' | sed 's/^[^ ]* /SERVED /'
"""

_PIN = """
python3 -c '
from pathlib import Path
from lim.image.initramfs.{module} import {backend}
for key in {backend}().host_public_keys(Path("/")):
    print("PINNED", key)
'
"""

ARCH_SCRIPT = (
    """
set -e
pacman -Sy --noconfirm --needed mkinitcpio-dropbear openssh python python-yaml >/dev/null
. /usr/lib/initcpio/install/dropbear
ssh-keygen -A
copy_openssh_keys || generate_keys
"""
    + _PIN.format(module="mkinitcpio", backend="MkinitcpioBackend")
    + """
ssh-keygen -A
copy_openssh_keys || generate_keys
"""
    + _SERVE_AND_SCAN.format(
        keys="-r /etc/dropbear/dropbear_ecdsa_host_key -r /etc/dropbear/dropbear_rsa_host_key"
    )
)

DEBIAN_SCRIPT = (
    """
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq dropbear-initramfs openssh-client python3 python3-yaml >/dev/null
"""
    + _PIN.format(module="initramfs_tools", backend="InitramfsToolsBackend")
    + _SERVE_AND_SCAN.format(
        keys=" ".join(
            f"-r /etc/dropbear/initramfs/dropbear_{kind}_host_key"
            for kind in ("ed25519", "ecdsa", "rsa")
        )
    )
)


def _keys(output: str, prefix: str) -> set[str]:
    return {" ".join(line.split()[1:3]) for line in output.splitlines() if line.startswith(prefix)}


@pytest.mark.parametrize(
    ("image", "script"),
    [
        ("archlinux:latest", ARCH_SCRIPT),
        ("debian:bookworm", DEBIAN_SCRIPT),
        ("debian:trixie", DEBIAN_SCRIPT),
    ],
    ids=["arch", "bookworm", "trixie"],
)
def test_pinned_keys_equal_the_keys_dropbear_serves(image, script):
    result = subprocess.run(
        [
            DOCKER,
            "run",
            "--rm",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-v",
            f"{REPO_ROOT}:/src:ro",
            "-w",
            "/src",
            image,
            "bash",
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    served = _keys(result.stdout, "SERVED ")
    pinned = _keys(result.stdout, "PINNED ")
    assert served, f"dropbear served no key:\n{result.stdout}{result.stderr}"
    assert pinned == served, result.stdout
