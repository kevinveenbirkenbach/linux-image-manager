import pytest

from lim import config
from lim.device import Device
from lim.errors import LimError
from lim.image.initramfs import get_backend, keygen, mkinitcpio
from lim.image.initramfs.initramfs_tools import InitramfsToolsBackend
from lim.image.initramfs.mkinitcpio import MkinitcpioBackend
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession


@pytest.fixture
def plan():
    return ImagePlan(distribution="arch", raspberry_pi_version="4", tor_unlock=True)


@pytest.fixture
def debian_plan():
    return ImagePlan(distribution="raspios", root_filesystem="ext4", tor_unlock=True)


def _write_onion_hostname(root, address="abcdefghijklmnop.onion"):
    onion_dir = root / keygen.ONION_STAGING_DIR
    onion_dir.mkdir(parents=True)
    (onion_dir / "hostname").write_text(f"{address}\n")


def _session(tmp_path, mapper="cryptroot"):
    session = ImageSession(Device("mmcblk0"))
    session.root_partition_uuid = "ROOT-UUID"
    session.root_mapper_name = mapper
    session.root_mapper_path = f"/dev/mapper/{mapper}"
    session.boot_mount_path = tmp_path / "boot"
    session.boot_mount_path.mkdir()
    return session


class TestBackendDispatch:
    def test_arch_and_manjaro_use_mkinitcpio(self):
        assert isinstance(get_backend("arch"), MkinitcpioBackend)
        assert isinstance(get_backend("manjaro"), MkinitcpioBackend)

    def test_raspios_uses_initramfs_tools(self):
        assert isinstance(get_backend("raspios"), InitramfsToolsBackend)

    def test_unknown_distribution_raises(self):
        with pytest.raises(LimError, match="No initramfs backend"):
            get_backend("gentoo")


class TestMkinitcpioTorUnlock:
    def test_installs_hooks_and_returns_address(self, tmp_path, plan, fake_runner):
        _write_onion_hostname(tmp_path, "stableaddress.onion")

        address = MkinitcpioBackend().install_tor_unlock(plan, tmp_path)

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
        assert fake_runner.find("chroot", "DisableNetwork") == []

    def test_generates_keys_when_missing(self, tmp_path, plan, fake_runner):
        with pytest.raises(LimError, match="produced no"):
            MkinitcpioBackend().install_tor_unlock(plan, tmp_path)
        keygen_calls = [
            input_text
            for _, _, input_text in fake_runner.calls
            if input_text and "DisableNetwork" in input_text
        ]
        assert len(keygen_calls) == 1
        assert "HiddenServiceDir" in keygen_calls[0]


class TestInitcpioHookHardening:
    """Guards for review findings in the shipped mkinitcpio hooks."""

    def _read(self, name):
        return (config.CONFIGURATION_PATH / "initcpio" / name).read_text()

    def test_hook_resources_exist(self):
        for name in ("tor_install", "tor_hook", "torrc"):
            assert (config.CONFIGURATION_PATH / "initcpio" / name).is_file()

    def test_install_bakes_the_dns_resolver(self):
        assert "libnss_dns.so.2" in self._read("tor_install")

    def test_hook_never_sources_dhcp_lease_files(self):
        hook = self._read("tor_hook")
        assert '. "$conf"' not in hook
        assert "sed -n 's/^IPV4DNS" in hook

    def test_hook_attempts_ntp_without_gating_on_dhcp_dns(self):
        assert "skipping NTP sync" not in self._read("tor_hook")


class TestMkinitcpioBootloader:
    """The cmdline.txt boot path (RPi4-class) must set ip= for remote unlock."""

    def test_cmdline_txt_gets_network_params(self, tmp_path, plan):
        root = tmp_path / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("myhost\n")
        session = _session(tmp_path)
        (session.boot_mount_path / "cmdline.txt").write_text("root=/dev/mmcblk0p2 rw rootwait\n")

        MkinitcpioBackend().configure_bootloader(plan, session, root)

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
            f"HOOKS=({mkinitcpio.MKINITCPIO_HOOKS_PREFIX} "
            f"{mkinitcpio.MKINITCPIO_HOOKS_SUFFIX})\n"
        )
        return path

    def test_tor_hook_between_netconf_and_dropbear(self, tmp_path, plan, fake_runner):
        path = self._mkinitcpio_conf(tmp_path)
        MkinitcpioBackend().configure_initramfs(plan, tmp_path)
        assert "netconf tor dropbear encryptssh" in path.read_text()

    def test_no_tor_hook_when_disabled(self, tmp_path, plan, fake_runner):
        plan.tor_unlock = False
        path = self._mkinitcpio_conf(tmp_path)
        MkinitcpioBackend().configure_initramfs(plan, tmp_path)
        content = path.read_text()
        assert "netconf dropbear encryptssh" in content
        assert " tor " not in content


class TestInitramfsToolsBackend:
    """The Debian / Raspberry Pi OS backend."""

    def test_crypttab_uses_initramfs_option(self, tmp_path, debian_plan):
        root = tmp_path / "root"
        (root / "etc").mkdir(parents=True)
        session = _session(tmp_path)
        InitramfsToolsBackend().register_encrypted_root(debian_plan, session, root)
        crypttab = (root / "etc/crypttab").read_text()
        assert "cryptroot UUID=ROOT-UUID none luks,initramfs" in crypttab
        assert "/dev/mapper/cryptroot" in (root / "etc/fstab").read_text()

    def test_cmdline_points_at_mapper_with_network(self, tmp_path, debian_plan):
        root = tmp_path / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("pi\n")
        session = _session(tmp_path)
        (session.boot_mount_path / "cmdline.txt").write_text(
            "console=serial0,115200 root=PARTUUID=abcd-02 rootfstype=ext4 rootwait\n"
        )
        (session.boot_mount_path / "config.txt").write_text("dtparam=audio=on\n")

        InitramfsToolsBackend().configure_bootloader(debian_plan, session, root)

        cmdline = (session.boot_mount_path / "cmdline.txt").read_text()
        assert "root=/dev/mapper/cryptroot" in cmdline
        assert "root=PARTUUID=abcd-02" not in cmdline
        assert "ip=::::pi:eth0:dhcp" in cmdline
        assert "tor_ntp=" in cmdline
        assert cmdline.count("\n") == 1  # cmdline must stay a single line
        assert "auto_initramfs=1" in (session.boot_mount_path / "config.txt").read_text()

    def test_install_tor_unlock_places_initramfs_tools_scripts(
        self, tmp_path, debian_plan, fake_runner
    ):
        _write_onion_hostname(tmp_path, "debianonion.onion")
        address = InitramfsToolsBackend().install_tor_unlock(debian_plan, tmp_path)
        assert address == "debianonion.onion"
        assert len(fake_runner.find("install", "tor_hook", "hooks/tor")) == 1
        assert len(fake_runner.find("tor_premount", "init-premount/tor")) == 1
        assert len(fake_runner.find("tor_bottom", "init-bottom/tor")) == 1
        apt = [
            text
            for _, _, text in fake_runner.calls
            if text and "apt-get install" in text and "tor busybox" in text
        ]
        assert len(apt) == 1


class TestInitramfsToolsHookHardening:
    def _read(self, name):
        return (config.CONFIGURATION_PATH / "initramfs-tools" / name).read_text()

    def test_hook_files_exist(self):
        for name in ("tor_hook", "tor_premount", "tor_bottom", "torrc"):
            assert (config.CONFIGURATION_PATH / "initramfs-tools" / name).is_file()

    def test_hook_bakes_dns_resolver(self):
        assert "libnss_dns.so.2" in self._read("tor_hook")

    def test_premount_does_not_source_lease_files(self):
        premount = self._read("tor_premount")
        assert '. "$conf"' not in premount
        assert "sed -n 's/^IPV4DNS" in premount

    def test_hook_stamps_a_clock_floor(self):
        assert "/etc/tor-clock-floor" in self._read("tor_hook")

    def test_premount_raises_clock_to_floor_before_ntp(self):
        premount = self._read("tor_premount")
        assert "/etc/tor-clock-floor" in premount
        assert premount.index("tor-clock-floor") < premount.index("ntpd")
