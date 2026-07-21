import pytest

from lim import config
from lim.device import Device
from lim.errors import LimError
from lim.image import encryption, tor
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession


@pytest.fixture
def plan():
    return ImagePlan(distribution="arch", raspberry_pi_version="4", tor_unlock=True)


def _write_onion_hostname(root, address="abcdefghijklmnop.onion"):
    onion_dir = root / tor.ONION_DIR
    onion_dir.mkdir(parents=True)
    (onion_dir / "hostname").write_text(f"{address}\n")


class TestConfigureTorUnlock:
    def test_installs_hooks_and_returns_address(self, tmp_path, plan, fake_runner):
        _write_onion_hostname(tmp_path, "stableaddress.onion")

        address = tor.configure_tor_unlock(plan, tmp_path)

        assert address == "stableaddress.onion"
        package_installs = [
            input_text
            for _, _, input_text in fake_runner.calls
            if input_text and "pacman" in input_text and "tor busybox" in input_text
        ]
        assert len(package_installs) == 1
        assert len(fake_runner.find("install", "tor_install", "etc/initcpio/install/tor")) == 1
        assert len(fake_runner.find("install", "tor_hook", "etc/initcpio/hooks/tor")) == 1
        assert len(fake_runner.find("install", "torrc", "etc/tor/initramfs-torrc")) == 1
        # Existing keys must be kept: no keygen chroot run.
        assert fake_runner.find("chroot", "DisableNetwork") == []

    def test_generates_keys_when_missing(self, tmp_path, plan, fake_runner):
        with pytest.raises(LimError, match="produced no"):
            tor.configure_tor_unlock(plan, tmp_path)
        # FakeRunner executes nothing, so the hostname file never appears —
        # but the keygen chroot script must have been issued exactly once.
        keygen_calls = [
            (kind, cmd, input_text)
            for kind, cmd, input_text in fake_runner.calls
            if input_text and "DisableNetwork" in input_text
        ]
        assert len(keygen_calls) == 1
        assert "HiddenServiceDir" in keygen_calls[0][2]

    def test_hook_resources_exist(self):
        source_dir = config.CONFIGURATION_PATH / "initcpio"
        for name in ("tor_install", "tor_hook", "torrc"):
            assert (source_dir / name).is_file()


class TestInitcpioHookHardening:
    """Guards for review findings in the shipped initramfs hooks."""

    def _read(self, name):
        return (config.CONFIGURATION_PATH / "initcpio" / name).read_text()

    def test_install_bakes_the_dns_resolver(self):
        # Without the NSS module the NTP hostname never resolves and the clock
        # stays at 1970, so Tor rejects the consensus and never publishes.
        assert "libnss_dns.so.2" in self._read("tor_install")

    def test_hook_never_sources_dhcp_lease_files(self):
        # Sourcing /tmp/net-*.conf would run attacker-controlled DHCP option
        # strings as root before the LUKS root is unlocked.
        hook = self._read("tor_hook")
        assert '. "$conf"' not in hook
        assert "sed -n 's/^IPV4DNS" in hook

    def test_hook_attempts_ntp_without_gating_on_dhcp_dns(self):
        # NTP must run even when tor_ntp is an IP literal (no DNS needed).
        hook = self._read("tor_hook")
        assert "skipping NTP sync" not in hook


class TestBootloaderNetworking:
    """The cmdline.txt boot path (RPi4-class) must set ip= for remote unlock."""

    def _session(self, tmp_path):
        session = ImageSession(Device("mmcblk0"))
        session.root_partition_uuid = "ROOT-UUID"
        session.root_mapper_name = "cryptroot"
        session.root_mapper_path = "/dev/mapper/cryptroot"
        session.boot_mount_path = tmp_path / "boot"
        session.boot_mount_path.mkdir()
        return session

    def test_cmdline_txt_gets_network_params(self, tmp_path, plan):
        root = tmp_path / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("myhost\n")
        session = self._session(tmp_path)
        (session.boot_mount_path / "cmdline.txt").write_text(
            "root=/dev/mmcblk0p2 rw rootwait\n"
        )

        encryption._configure_bootloader(plan, session, root)

        content = (session.boot_mount_path / "cmdline.txt").read_text()
        assert "ip=::::myhost:eth0:dhcp" in content
        assert "net.ifnames=0" in content
        assert "cryptdevice=UUID=ROOT-UUID:cryptroot" in content
        assert "root=/dev/mmcblk0p2" not in content


class TestMkinitcpioHooksLine:
    def _mkinitcpio_conf(self, root):
        path = root / "etc/mkinitcpio.conf"
        path.parent.mkdir(parents=True)
        path.write_text(
            "MODULES=()\n"
            "BINARIES=()\n"
            f"HOOKS=({encryption.MKINITCPIO_HOOKS_PREFIX} "
            f"{encryption.MKINITCPIO_HOOKS_SUFFIX})\n"
        )
        return path

    def test_tor_hook_between_netconf_and_dropbear(self, tmp_path, plan, fake_runner):
        path = self._mkinitcpio_conf(tmp_path)
        encryption._configure_mkinitcpio(plan, tmp_path)
        assert "netconf tor dropbear encryptssh" in path.read_text()

    def test_no_tor_hook_when_disabled(self, tmp_path, plan, fake_runner):
        plan.tor_unlock = False
        path = self._mkinitcpio_conf(tmp_path)
        encryption._configure_mkinitcpio(plan, tmp_path)
        content = path.read_text()
        assert "netconf dropbear encryptssh" in content
        assert " tor " not in content
