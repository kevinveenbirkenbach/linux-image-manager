"""Always-on unit tests for the QEMU harness logic.

No QEMU, root, or network: they exercise the pure command builders and guard
the root build script against drifting away from what the harness expects.
Run as part of the normal suite.
"""

from pathlib import Path

import pytest

from lim import config as lim_config
from tests.e2e.qemu import boot_unlock, config, harness, tor_net
from tests.e2e.qemu.config import EXPECTED_HOOKS_ORDER, QemuSpec

BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "tests/e2e/qemu/build_image.sh"


def _spec(**overrides) -> QemuSpec:
    base = {
        "arch": "x86_64",
        "work_dir": Path("/work"),
        "image_path": Path("/work/image.raw"),
        "kernel_path": Path("/work/kernel"),
        "initramfs_path": Path("/work/initramfs"),
        "luks_uuid": "1111-UUID",
        "mapper_name": "cryptroot",
        "passphrase": "secret",
        "ssh_key_path": Path("/work/unlock_key"),
        "onion_address": "abcd.onion",
        "socks_port": 9052,
    }
    base.update(overrides)
    return QemuSpec(**base)


class TestKernelCmdline:
    def test_unlocks_the_luks_root_over_dhcp(self):
        line = config.kernel_cmdline(_spec())
        assert "cryptdevice=UUID=1111-UUID:cryptroot" in line
        assert "root=/dev/mapper/cryptroot" in line
        # Explicit device in the ip= form, else netconf loops on "No such device".
        assert ":eth0:dhcp" in line
        assert "console=ttyS0" in line

    def test_serial_console_is_last_so_marker_reaches_serial_log(self):
        line = config.kernel_cmdline(_spec())
        assert line.index("console=tty0") < line.index("console=ttyS0")

    def test_aarch64_uses_amba_serial(self):
        assert "console=ttyAMA0" in config.kernel_cmdline(_spec(arch="aarch64"))


class TestQemuArgv:
    def test_x86_uses_virtio_net_and_direct_kernel_boot(self):
        argv = config.qemu_argv(_spec())
        assert argv[0] == "qemu-system-x86_64"
        assert "virtio-net-pci,netdev=net0" in argv
        assert "-kernel" in argv
        assert "/work/kernel" in argv
        assert "-initrd" in argv
        assert "/work/initramfs" in argv
        assert "file=/work/image.raw,if=virtio,format=raw" in argv
        assert f"file:{_spec().serial_log}" in argv
        assert "user,id=net0" in argv

    def test_aarch64_uses_virt_machine_and_net_device(self):
        argv = config.qemu_argv(_spec(arch="aarch64"))
        assert argv[0] == "qemu-system-aarch64"
        assert "virt" in argv
        assert "virtio-net-device,netdev=net0" in argv

    def test_kvm_accel_is_emitted_when_requested(self):
        assert "kvm" in config.qemu_argv(_spec(accel="kvm"))
        assert "kvm" not in config.qemu_argv(_spec(accel="tcg"))

    def test_unknown_arch_raises(self):
        with pytest.raises(ValueError, match="Unsupported arch"):
            config.qemu_argv(_spec(arch="riscv64"))


class TestQemuBinary:
    def test_derives_binary_per_arch(self):
        assert config.qemu_binary("x86_64") == "qemu-system-x86_64"
        assert config.qemu_binary("aarch64") == "qemu-system-aarch64"

    def test_unknown_arch_raises(self):
        with pytest.raises(ValueError, match="Unsupported arch"):
            config.qemu_binary("riscv64")


class TestSshInvocation:
    def test_proxy_command_routes_through_socks5(self):
        proxy = config.ssh_proxy_command(9052)
        assert "--proxy 127.0.0.1:9052" in proxy
        assert "--proxy-type socks5" in proxy

    def test_ssh_argv_targets_onion_via_key_and_proxy(self):
        argv = config.ssh_argv(_spec())
        assert "root@abcd.onion" in argv
        assert "-i" in argv
        assert "/work/unlock_key" in argv
        assert any("ProxyCommand=" in part for part in argv)
        assert "StrictHostKeyChecking=no" in argv


class TestBuildScriptStaysAligned:
    """Guards: the root build script must match what the harness assumes."""

    def _script(self) -> str:
        return BUILD_SCRIPT.read_text()

    def test_hooks_place_tor_between_netconf_and_dropbear(self):
        hooks_line = next(
            line for line in self._script().splitlines() if line.startswith("HOOKS=")
        )
        positions = [hooks_line.index(hook) for hook in EXPECTED_HOOKS_ORDER]
        assert positions == sorted(positions), hooks_line

    def test_installs_the_real_lim_initcpio_files(self):
        script = self._script()
        for name in ("tor_install", "tor_hook", "torrc"):
            assert f"$INITCPIO_SRC/{name}" in script
        assert "etc/dropbear/root_key" in script

    def test_uses_virtio_net_and_emits_boot_marker(self):
        script = self._script()
        assert "virtio_net" in script
        assert config.BOOT_OK_MARKER in script

    def test_mounts_devpts_before_dropbear_for_pty(self):
        hooks_line = next(
            line for line in self._script().splitlines() if line.startswith("HOOKS=")
        )
        assert "ptsmount" in hooks_line
        assert hooks_line.index("ptsmount") < hooks_line.index("dropbear")
        assert "mount -t devpts" in self._script()

    def test_real_initcpio_source_directory_exists(self):
        assert (lim_config.CONFIGURATION_PATH / "initcpio" / "tor_hook").is_file()


class TestOrchestratorGlue:
    def test_load_spec_reads_image_env(self, tmp_path):
        (tmp_path / "image.env").write_text(
            "LUKS_UUID=abc-123\n"
            "MAPPER_NAME=cryptroot\n"
            "ONION_ADDRESS=xyz.onion\n"
            "IMAGE=/w/image.raw\n"
            "KERNEL=/w/kernel\n"
            "INITRAMFS=/w/initramfs\n"
        )
        cfg = harness.HarnessConfig(repo_root=Path("/repo"), work_dir=tmp_path)
        spec = harness._load_spec(cfg, ssh_key=tmp_path / "k", socks_port=9052)
        assert spec.luks_uuid == "abc-123"
        assert spec.onion_address == "xyz.onion"
        assert spec.image_path == Path("/w/image.raw")
        assert spec.socks_port == 9052

    def test_env_parser_ignores_comments_and_blanks(self, tmp_path):
        env = tmp_path / "image.env"
        env.write_text("# a comment\n\nKEY=value\n")
        assert boot_unlock.parse_env_file(env) == {"KEY": "value"}

    def test_choose_accel_falls_back_to_tcg_for_foreign_arch(self):
        assert harness.choose_accel("riscv64") == "tcg"


class TestChutneyParsing:
    def test_parse_socks_port_picks_first_nonzero(self, tmp_path):
        torrc = tmp_path / "torrc"
        torrc.write_text("SocksPort 0\nSocksPort 9008\n")
        assert tor_net._parse_socks_port(torrc) == 9008

    def test_find_client_torrc_skips_relays(self, tmp_path):
        (tmp_path / "000a").mkdir()
        (tmp_path / "000a" / "torrc").write_text("SocksPort 0\n")
        (tmp_path / "001c").mkdir()
        (tmp_path / "001c" / "torrc").write_text("SocksPort 9010\n")
        found = tor_net._find_client_torrc(tmp_path)
        assert found == tmp_path / "001c" / "torrc"
