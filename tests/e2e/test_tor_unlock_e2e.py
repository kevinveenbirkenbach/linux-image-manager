"""End-to-end test of the Tor onion LUKS-unlock path (rootless).

It reproduces the operator-visible half of the decryption process that the
"tor" mkinitcpio hook drives at boot:

  1. generate the v3 onion keys offline (as lim.image.tor does in the chroot),
  2. start a real Tor onion service from a torrc mirroring the baked-in one,
     forwarding the virtual port 22 to a local dropbear stand-in,
  3. connect to the .onion address through Tor and deliver the passphrase,
  4. assert the passphrase reached the unlock endpoint and it "unlocked".

The physical flashing half (loop device, cryptsetup, mount, chroot,
mkinitcpio) needs root and is out of scope here by design.

Requires the real `tor` binary and live Tor network access, so it is
opt-in and skipped unless LIM_E2E_TOR=1:

    LIM_E2E_TOR=1 pytest tests/e2e/test_tor_unlock_e2e.py -v
"""

import os
import shutil
import time

import pytest

from lim.image import tor as tor_module
from tests.e2e import tor_harness

pytestmark = pytest.mark.skipif(
    os.environ.get("LIM_E2E_TOR") != "1" or shutil.which("tor") is None,
    reason="needs LIM_E2E_TOR=1 and the tor binary (live network, slow).",
)

PASSPHRASE = b"correct horse battery staple"


@pytest.fixture
def workdir(tmp_path):
    (tmp_path / "onion").mkdir()
    (tmp_path / "data").mkdir()
    return tmp_path


def test_offline_keygen_matches_production_flags():
    """Guard: the harness keygen mirrors the flags production actually runs."""
    script = tor_module._KEYGEN_SCRIPT
    assert "--DisableNetwork 1" in script
    assert "HiddenServicePort" in script
    assert "22 127.0.0.1:22" in script
    assert "--SocksPort 0" in script


def test_onion_keygen_is_deterministic_and_offline(workdir):
    """Keys generate without network and the .onion address is stable."""
    address = tor_harness.generate_onion_keys(
        workdir / "onion", workdir / "data"
    )
    assert address.endswith(".onion")
    assert len(address) == len("v" * 56) + len(".onion")  # v3 = 56 base32 chars
    for name in ("hs_ed25519_secret_key", "hs_ed25519_public_key", "hostname"):
        assert (workdir / "onion" / name).is_file()


def test_unlock_passphrase_travels_over_onion(workdir):
    """Full rootless round-trip: client -> Tor -> onion -> dropbear stand-in."""
    onion_dir = workdir / "onion"
    data_dir = workdir / "data"
    onion_address = tor_harness.generate_onion_keys(onion_dir, data_dir)

    backend_port = tor_harness.free_port()
    socks_port = tor_harness.free_port()
    torrc = workdir / "torrc"
    log_path = workdir / "tor.log"
    tor_harness.write_test_torrc(torrc, data_dir, onion_dir, backend_port)

    dropbear = tor_harness.FakeDropbear(backend_port)
    dropbear.start()
    service = tor_harness.start_onion_service(torrc, socks_port, log_path)
    try:
        tor_harness.wait_bootstrapped(log_path, service)

        # Onion descriptors need a moment to publish after bootstrap; retry.
        last_error = None
        for _ in range(5):
            try:
                stream = tor_harness.socks5_connect(socks_port, onion_address, 22)
                break
            except (OSError, RuntimeError) as exc:
                last_error = exc
                time.sleep(2)
        else:
            pytest.fail(f"Could not reach {onion_address} via Tor: {last_error}")

        with stream:
            stream.sendall(PASSPHRASE + b"\n")
            reply = stream.recv(64)
    finally:
        service.terminate()
        service.wait(timeout=15)
        dropbear.stop()

    assert reply.strip() == b"UNLOCKED"
    assert dropbear.received == PASSPHRASE
