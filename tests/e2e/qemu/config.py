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
    # "arch" (mkinitcpio/encryptssh) or "debian" (initramfs-tools/cryptroot-unlock).
    os_family: str = "arch"
    # Remote command the unlock SSH session runs; empty means the session
    # presents the passphrase prompt itself (Arch encryptssh).
    unlock_command: str = ""
    # >0 selects the deterministic direct transport: QEMU forwards this host
    # port to the guest's dropbear (:22) and the passphrase is delivered over a
    # plain SSH (no Tor). 0 uses the Tor onion transport (onion_address).
    direct_ssh_port: int = 0

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
    # Arch's mkinitcpio encrypt/encryptssh finds the LUKS device from the
    # cryptdevice= param; Debian's cryptsetup-initramfs reads /etc/crypttab
    # baked into the initramfs, so it needs only root=/dev/mapper/<name>.
    if spec.os_family == "debian":
        crypt = f"root=/dev/mapper/{spec.mapper_name} rw"
    else:
        crypt = (
            f"cryptdevice=UUID={spec.luks_uuid}:{spec.mapper_name} "
            f"root=/dev/mapper/{spec.mapper_name} rw"
        )
    # The netconf/dropbear-initramfs hooks need the explicit ip= form
    # <client>:<server>:<gw>:<netmask>:<host>:<device>:<proto> — the device
    # name is mandatory; a bare "ip=dhcp" leaves netconf looping on
    # "SIOCGIFFLAGS: No such device". net.ifnames=0 keeps the NIC named eth0.
    # The LAST console= owns /dev/console, which the boot-ok marker echoes to
    # and QEMU captures via -serial file, so the serial console must come last.
    return f"{crypt} ip=::::lim-e2e:eth0:dhcp net.ifnames=0 console=tty0 console={console}"


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
    netdev = "user,id=net0"
    if spec.direct_ssh_port:
        # Forward a host port to the guest's dropbear for the direct transport.
        netdev += f",hostfwd=tcp:127.0.0.1:{spec.direct_ssh_port}-:22"
    argv += [
        "-m",
        str(spec.memory_mb),
        "-kernel",
        str(spec.kernel_path),
        "-initrd",
        str(spec.initramfs_path),
        "-append",
        kernel_cmdline(spec),
        "-drive",
        f"file={spec.image_path},if=virtio,format=raw",
        "-netdev",
        netdev,
        "-device",
        f"{net_device},netdev=net0",
        "-nographic",
        "-serial",
        f"file:{spec.serial_log}",
        "-no-reboot",
    ]
    return argv


def ssh_proxy_command(socks_port: int) -> str:
    """ncat-based SOCKS5 ProxyCommand routing the SSH stream through Tor."""
    return f"ncat --proxy 127.0.0.1:{socks_port} --proxy-type socks5 %h %p"


def ssh_argv(spec: QemuSpec) -> list[str]:
    """Non-interactive SSH into the initramfs dropbear to feed the passphrase.

    ``-tt`` forces a pty so the askpass inside the session reads the passphrase
    we pipe on stdin. Host-key checking is off (throwaway host key). On Debian
    the session runs ``cryptroot-unlock``; on Arch encryptssh presents the
    prompt on login. The direct transport connects to a forwarded host port;
    the Tor transport routes through the onion via a SOCKS ProxyCommand.
    """
    argv = [
        "ssh",
        "-tt",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "BatchMode=yes",
        "-i",
        str(spec.ssh_key_path),
    ]
    if spec.direct_ssh_port:
        argv += ["-p", str(spec.direct_ssh_port), "root@127.0.0.1"]
    else:
        argv += [
            "-o",
            f"ProxyCommand={ssh_proxy_command(spec.socks_port)}",
            f"root@{spec.onion_address}",
        ]
    if spec.unlock_command:
        argv.append(spec.unlock_command)
    return argv
