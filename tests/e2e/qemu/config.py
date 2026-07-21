"""Pure, side-effect-free builders for the QEMU unlock harness.

Everything here is deterministic string/list construction so it can be
unit-tested without QEMU, root, or a network (see test_qemu_harness_unit.py).
The stages that actually touch the system live in build_image.sh,
chutney.py and boot_unlock.py.
"""

from dataclasses import dataclass
from pathlib import Path

# Printed to /dev/console by a oneshot service baked into the image; its
# appearance on the serial log is the proof that the LUKS root actually
# unlocked and the real system finished booting.
BOOT_OK_MARKER = "LIM_UNLOCK_BOOT_OK"

# The HOOKS the built image must carry — the tor hook sits between netconf
# and dropbear, exactly as lim.image.encryption wires it for real images.
EXPECTED_HOOKS_ORDER = ("netconf", "tor", "dropbear", "encryptssh")

# Serial console device per architecture (kernel console= and getty).
_SERIAL_CONSOLE = {"x86_64": "ttyS0", "aarch64": "ttyAMA0"}
_QEMU_BINARY = {"x86_64": "qemu-system-x86_64", "aarch64": "qemu-system-aarch64"}


@dataclass
class QemuSpec:
    """Everything needed to boot one built image and unlock it."""

    arch: str
    work_dir: Path
    image_path: Path
    kernel_path: Path
    initramfs_path: Path
    luks_uuid: str
    mapper_name: str
    passphrase: str
    ssh_key_path: Path
    onion_address: str = ""
    socks_port: int = 9050
    # 2 GiB so the LUKS argon2 KDF has enough memory to unlock in the guest
    # (build_image.sh also caps --pbkdf-memory to keep this headroom).
    memory_mb: int = 2048
    accel: str = "tcg"  # "kvm" when the host arch matches and /dev/kvm exists

    @property
    def serial_log(self) -> Path:
        return self.work_dir / "serial.log"


def qemu_binary(arch: str) -> str:
    """Return the qemu-system-* binary for an arch (raises on unsupported)."""
    if arch not in _QEMU_BINARY:
        raise ValueError(f"Unsupported arch: {arch}")
    return _QEMU_BINARY[arch]


def kernel_cmdline(spec: QemuSpec) -> str:
    """Kernel command line unlocking the LUKS root over the mkinitcpio hooks.

    ``ip=dhcp`` is what the netconf hook consumes to bring up virtio-net in
    early userspace; the Pi images use USB-gadget networking instead, which
    QEMU cannot emulate — hence virtio here (we model the stack, not the board).
    """
    console = _SERIAL_CONSOLE[spec.arch]
    # The netconf hook needs the explicit ip= form
    # <client>:<server>:<gw>:<netmask>:<host>:<device>:<proto> — the device
    # name is mandatory (as lim's own boot config uses it); a bare "ip=dhcp"
    # leaves netconf looping on "SIOCGIFFLAGS: No such device". net.ifnames=0
    # keeps the virtio NIC named eth0.
    # The LAST console= owns /dev/console, which the boot-ok marker echoes to
    # and QEMU captures via -serial file, so the serial console must come last.
    return (
        f"cryptdevice=UUID={spec.luks_uuid}:{spec.mapper_name} "
        f"root=/dev/mapper/{spec.mapper_name} rw "
        f"ip=::::lim-e2e:eth0:dhcp net.ifnames=0 console=tty0 console={console}"
    )


def qemu_argv(spec: QemuSpec) -> list[str]:
    """Full QEMU command: direct kernel boot, virtio disk/net, serial to log.

    User-mode networking (``-netdev user``) needs no root and no tap device;
    it is enough for a Tor onion service, whose rendezvous is outbound from
    both ends, so no inbound host port forward is required.
    """
    argv = [qemu_binary(spec.arch)]  # validates the arch
    net_device = "virtio-net-pci" if spec.arch == "x86_64" else "virtio-net-device"
    if spec.arch == "x86_64":
        argv += ["-machine", "q35"]
    else:
        argv += ["-machine", "virt", "-cpu", "cortex-a72"]
    if spec.accel == "kvm":
        argv += ["-cpu", "host", "-accel", "kvm"]
    elif spec.arch == "x86_64":
        argv += ["-cpu", "max", "-accel", "tcg"]
    argv += [
        "-m", str(spec.memory_mb),
        "-kernel", str(spec.kernel_path),
        "-initrd", str(spec.initramfs_path),
        "-append", kernel_cmdline(spec),
        "-drive", f"file={spec.image_path},if=virtio,format=raw",
        "-netdev", "user,id=net0",
        "-device", f"{net_device},netdev=net0",
        "-nographic",
        "-serial", f"file:{spec.serial_log}",
        "-no-reboot",
    ]
    return argv


def ssh_proxy_command(socks_port: int) -> str:
    """ncat-based SOCKS5 ProxyCommand routing the SSH stream through Tor."""
    return f"ncat --proxy 127.0.0.1:{socks_port} --proxy-type socks5 %h %p"


def ssh_argv(spec: QemuSpec) -> list[str]:
    """Non-interactive SSH into the initramfs dropbear via the onion address.

    ``-tt`` forces a pty so the cryptsetup askpass inside the encryptssh
    session reads the passphrase we pipe on stdin. Host-key checking is off
    because a throwaway onion has no known_hosts entry.
    """
    return [
        "ssh", "-tt",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "BatchMode=yes",
        "-o", f"ProxyCommand={ssh_proxy_command(spec.socks_port)}",
        "-i", str(spec.ssh_key_path),
        f"root@{spec.onion_address}",
    ]
