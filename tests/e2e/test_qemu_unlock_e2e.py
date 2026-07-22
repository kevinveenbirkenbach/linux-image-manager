"""Full virtualized end-to-end test: build -> boot in QEMU -> unlock over Tor.

Models the whole process the way lim runs it, on a QEMU-bootable virtio
machine (the Raspberry Pi's USB-gadget net can't be emulated, so we model
the software stack, not the board):

  1. build a LUKS image carrying the REAL lim initcpio tor artifacts,
  2. boot it in QEMU (rootless, user-mode net),
  3. its initramfs runs the real netconf/tor/dropbear/encryptssh chain and
     publishes the onion service,
  4. deliver the LUKS passphrase by SSHing to that onion through Tor,
  5. assert the boot-ok marker appears on the serial console — i.e. the real
     root actually unlocked and booted.

Heavy and privileged (QEMU + a tor network; the build needs root, ideally in
a throwaway VM). Opt-in and skipped unless LIM_E2E_QEMU=1:

    LIM_E2E_QEMU=1 pytest tests/e2e/test_qemu_unlock_e2e.py -v -s

Environment knobs: LIM_E2E_ARCH (x86_64|aarch64), CHUTNEY_PATH (use a private
chutney network instead of the public one). See tests/e2e/qemu/README.md.
"""

import os
import shutil
from pathlib import Path

import pytest

from tests.e2e.qemu import config as qemu_config
from tests.e2e.qemu.harness import HarnessConfig, run

REPO_ROOT = Path(__file__).resolve().parents[2]

# The QEMU binary is arch-specific, so derive it from LIM_E2E_ARCH instead of
# hardcoding x86_64 — otherwise the documented aarch64 run is never reachable.
_ARCH = os.environ.get("LIM_E2E_ARCH", "x86_64")
# The OS family selects the build tool: pacstrap (Arch) or debootstrap (Debian).
_OS = os.environ.get("LIM_E2E_OS", "arch")
# "direct" (deterministic port-forward) is the default; "tor" runs the full,
# opt-in onion transport (flaky over public Tor inside QEMU).
_TRANSPORT = os.environ.get("LIM_E2E_TRANSPORT", "direct")
_BUILD_TOOL = {"arch": "pacstrap", "debian": "debootstrap"}
_REQUIRED = [
    qemu_config.qemu_binary(_ARCH),
    _BUILD_TOOL.get(_OS, "pacstrap"),
    "cryptsetup",
    "ssh",
]
if _TRANSPORT == "tor":  # the onion transport also needs a Tor client + ncat
    _REQUIRED += ["tor", "ncat"]


def _missing_tools() -> list[str]:
    return [tool for tool in _REQUIRED if shutil.which(tool) is None]


pytestmark = pytest.mark.skipif(
    os.environ.get("LIM_E2E_QEMU") != "1" or bool(_missing_tools()),
    reason=(
        "needs LIM_E2E_QEMU=1 and " + ", ".join(_REQUIRED) + " (build stage needs root; slow)."
    ),
)


def test_full_build_boot_and_unlock(tmp_path):
    chutney_path = os.environ.get("CHUTNEY_PATH")
    cfg = HarnessConfig(
        repo_root=REPO_ROOT,
        work_dir=tmp_path / "qemu-e2e",
        arch=_ARCH,
        os_family=_OS,
        unlock_transport=_TRANSPORT,
        chutney_path=Path(chutney_path) if chutney_path else None,
    )

    spec = run(cfg)

    # run() only returns after the boot-ok marker was observed on the console.
    serial = spec.serial_log.read_text(errors="replace")
    assert qemu_config.BOOT_OK_MARKER in serial
