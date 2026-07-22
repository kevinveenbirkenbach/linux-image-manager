"""Boot a built image in QEMU and unlock its LUKS root over Tor.

This is the live half of the harness. QEMU runs rootless (user-mode net);
the passphrase is delivered exactly as an operator would: SSH through Tor to
the initramfs dropbear, piping the passphrase into the encryptssh prompt.
Success is observed on the serial console, not inferred.
"""

import contextlib
import subprocess
import threading
import time
from pathlib import Path

from tests.e2e.qemu import config
from tests.e2e.qemu.config import QemuSpec

# One generous budget covers guest boot + tor bootstrap + onion publish +
# unlock. TCG (no KVM) is slow, so keep it roomy.
UNLOCK_TIMEOUT = 480
DELIVERY_INTERVAL = 8
# Hold off the first delivery until the guest onion has had time to publish.
# A connect to a not-yet-published onion makes the client Tor cache the failed
# descriptor fetch and back off, so early hammering can lock us out for
# minutes; waiting until the onion is up means the first fetch succeeds.
INITIAL_DELIVERY_DELAY = 100
_SSH_ATTEMPT_TIMEOUT = 45
_POLL_INTERVAL = 2
_PROMPT_WAIT = 4  # let the encryptssh prompt appear before sending


def _serial_contains(spec: QemuSpec, needle: str) -> bool:
    log = spec.serial_log
    return log.is_file() and needle in log.read_text(errors="replace")


def _stream_new_serial(spec: QemuSpec, offset: int) -> int:
    """Print serial output written since ``offset``; return the new offset.

    Streams the guest's boot messages (netconf, the tor hook, dropbear,
    encryptssh) live so the operator sees the VM working, not a black box.
    """
    log = spec.serial_log
    if not log.is_file():
        return offset
    data = log.read_bytes()
    if len(data) > offset:
        print(data[offset:].decode(errors="replace"), end="", flush=True)
    return len(data)


def _serial_tail(spec: QemuSpec, lines: int = 15) -> str:
    if not spec.serial_log.is_file():
        return "(no serial output captured)"
    tail = spec.serial_log.read_text(errors="replace").splitlines()[-lines:]
    return "serial tail:\n  " + "\n  ".join(tail)


def _qemu_stderr_path(spec: QemuSpec) -> Path:
    return spec.work_dir / "qemu.stderr.log"


def _qemu_stderr_tail(spec: QemuSpec, lines: int = 10) -> str:
    path = _qemu_stderr_path(spec)
    if not path.is_file() or not path.read_text(errors="replace").strip():
        return ""
    tail = path.read_text(errors="replace").splitlines()[-lines:]
    return "\nqemu stderr:\n  " + "\n  ".join(tail)


def _ssh_log_path(spec: QemuSpec) -> Path:
    return spec.work_dir / "ssh-delivery.log"


def _ssh_log_tail(spec: QemuSpec, lines: int = 15) -> str:
    path = _ssh_log_path(spec)
    if not path.is_file() or not path.read_text(errors="replace").strip():
        return ""
    tail = path.read_text(errors="replace").splitlines()[-lines:]
    return "\nssh delivery log:\n  " + "\n  ".join(tail)


def _client_tor_tail(spec: QemuSpec, lines: int = 20) -> str:
    """Return the host Tor client's HS log — onion descriptor fetch/rendezvous."""
    path = spec.work_dir / "tor-client-hs.log"
    if not path.is_file() or not path.read_text(errors="replace").strip():
        return ""
    lines_out = [
        line
        for line in path.read_text(errors="replace").splitlines()
        if any(k in line.lower() for k in ("desc", "rend", "intro", "hs_", "onion"))
    ][-lines:]
    return "\nclient tor HS log:\n  " + "\n  ".join(lines_out)


def _deliver_worker(spec: QemuSpec) -> None:
    """Feed the passphrase over an SSH-through-Tor session, held open.

    Runs in a background thread so the main loop keeps streaming serial. The
    channel is deliberately kept OPEN after sending: closing stdin immediately
    (as a plain pipe does) tears the session down before cryptsetup finishes
    its argon2 KDF, killing the unlock mid-flight. Session output is appended to
    ssh-delivery.log so a failed unlock (onion unreachable, cryptroot-unlock
    error) is diagnosable.
    """
    log_file = _ssh_log_path(spec).open("a")
    log_file.write("--- delivery attempt ---\n")
    log_file.flush()
    proc = subprocess.Popen(
        config.ssh_argv(spec),
        stdin=subprocess.PIPE,
        stdout=log_file,
        stderr=log_file,
        text=True,
    )
    try:
        time.sleep(_PROMPT_WAIT)
        if proc.poll() is None and proc.stdin is not None:
            try:
                proc.stdin.write(spec.passphrase + "\n")
                proc.stdin.flush()
            except OSError:
                pass
        proc.wait(timeout=_SSH_ATTEMPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
    finally:
        if proc.stdin is not None:
            with contextlib.suppress(OSError):
                proc.stdin.close()
        log_file.close()


def boot_and_unlock(spec: QemuSpec) -> None:
    """Boot the image, unlock it over Tor, and confirm the real system booted.

    Returns normally only when the boot-ok marker appears on the serial
    console; the passphrase is (re)delivered on each poll until then. Raises
    with the serial tail on QEMU death or timeout.
    """
    if spec.serial_log.exists():
        spec.serial_log.unlink()
    if spec.direct_ssh_port:
        target = f"127.0.0.1:{spec.direct_ssh_port} -> guest dropbear (direct)"
        # dropbear comes up within seconds; no need to wait for an onion.
        initial_delay = 15
    else:
        target = f"{spec.onion_address}:22 (Tor onion)"
        initial_delay = INITIAL_DELIVERY_DELAY
    print(f"\n========== booting in QEMU ({spec.arch}, accel={spec.accel}) ==========")
    print(f"Unlock target: {target}  (budget {UNLOCK_TIMEOUT}s)")
    print("---- guest serial console ----", flush=True)
    # QEMU's own diagnostics (bad -machine/-cpu, /dev/kvm denied, image busy)
    # go to stderr; capture them so an early exit is debuggable, not opaque.
    qemu_stderr = _qemu_stderr_path(spec).open("wb")
    qemu = subprocess.Popen(
        config.qemu_argv(spec),
        stdout=subprocess.DEVNULL,
        stderr=qemu_stderr,
    )
    try:
        deadline = time.monotonic() + UNLOCK_TIMEOUT
        offset = 0
        # Hold off the first delivery until the unlock endpoint is up (see above).
        next_delivery = time.monotonic() + initial_delay
        print(
            f"[harness] waiting {initial_delay}s for the unlock endpoint before delivering...",
            flush=True,
        )
        delivery: threading.Thread | None = None
        while time.monotonic() < deadline:
            offset = _stream_new_serial(spec, offset)
            if _serial_contains(spec, config.BOOT_OK_MARKER):
                print("\n[harness] boot-ok marker seen — LUKS root unlocked and booted.")
                return
            if qemu.poll() is not None:
                raise RuntimeError(
                    f"QEMU exited early (code {qemu.returncode}).\n"
                    f"{_serial_tail(spec)}{_qemu_stderr_tail(spec)}"
                )
            # One delivery at a time; each holds its SSH session open in the
            # background while we keep streaming serial and watching the marker.
            idle = delivery is None or not delivery.is_alive()
            if idle and time.monotonic() >= next_delivery:
                print("\n[harness] delivering passphrase (holding session open) ...", flush=True)
                delivery = threading.Thread(target=_deliver_worker, args=(spec,), daemon=True)
                delivery.start()
                next_delivery = time.monotonic() + DELIVERY_INTERVAL
            time.sleep(_POLL_INTERVAL)
        raise RuntimeError(
            f"Boot-ok marker never appeared within {UNLOCK_TIMEOUT}s.\n"
            f"{_serial_tail(spec, lines=45)}{_qemu_stderr_tail(spec)}"
            f"{_ssh_log_tail(spec)}{_client_tor_tail(spec)}"
        )
    finally:
        qemu.terminate()
        try:
            qemu.wait(timeout=15)
        except subprocess.TimeoutExpired:
            qemu.kill()
            qemu.wait(timeout=10)
        qemu_stderr.close()


def parse_env_file(path: Path) -> dict[str, str]:
    """Read the KEY=VALUE image.env written by build_image.sh into a dict."""
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result
