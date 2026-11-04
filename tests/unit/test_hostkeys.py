import os
import pwd

from lim.image import hostkeys, unlock, wizard
from lim.image.initramfs import mkinitcpio
from lim.image.initramfs.initramfs_tools import InitramfsToolsBackend
from lim.image.initramfs.mkinitcpio import MkinitcpioBackend
from lim.image.plan import ImagePlan

ECDSA = "ecdsa-sha2-nistp256 AAAAE2VjZHNh root@pi"
RSA = "ssh-rsa AAAAB3NzaC1yc2E root@pi"


def _owner(home):
    return pwd.struct_passwd(("op", "x", os.getuid(), os.getgid(), "", str(home), "/bin/sh"))


class TestKnownHosts:
    def test_replaces_only_the_alias_and_drops_comments(self):
        text = "boot.pi ssh-rsa OLD\nboot.other ssh-rsa KEEP\n"
        result = hostkeys.replace_known_hosts(text, "boot.pi", [ECDSA])
        assert result == "boot.other ssh-rsa KEEP\nboot.pi ecdsa-sha2-nistp256 AAAAE2VjZHNh\n"


class TestConfigBlock:
    def test_rerun_replaces_block_and_keeps_user_config(self):
        user = "Host galaxyserver\n  User administrator"
        once = hostkeys.replace_config_block(user, "boot.pi", "Host boot.pi\n  HostName a\n")
        twice = hostkeys.replace_config_block(once, "boot.pi", "Host boot.pi\n  HostName b\n")
        assert twice.startswith("Host galaxyserver\n  User administrator\n")
        assert twice.count("Host boot.pi") == 1
        assert "HostName b" in twice
        assert "HostName a" not in twice

    def test_block_checks_strictly_against_the_lim_known_hosts(self, tmp_path):
        block = hostkeys.config_block("boot.pi", "x.onion", "/k/id", tmp_path / "kh")
        assert "HostKeyAlias boot.pi" in block
        assert f"UserKnownHostsFile {tmp_path / 'kh'}" in block
        assert "StrictHostKeyChecking yes" in block
        assert "IdentityFile /k/id" in block


class TestPin:
    def test_writes_private_files_under_the_owner_home(self, tmp_path):
        alias = hostkeys.pin(_owner(tmp_path), "pi", "x.onion", "", [ECDSA])
        known_hosts = tmp_path / hostkeys.KNOWN_HOSTS_SUBPATH
        ssh_config = tmp_path / hostkeys.SSH_CONFIG_SUBPATH
        assert alias == "boot.pi"
        assert known_hosts.read_text() == "boot.pi ecdsa-sha2-nistp256 AAAAE2VjZHNh\n"
        assert "Host boot.pi\n  HostName x.onion\n" in ssh_config.read_text()
        assert "IdentityFile" not in ssh_config.read_text()
        assert known_hosts.stat().st_mode & 0o777 == 0o600
        assert ssh_config.stat().st_mode & 0o777 == 0o600

    def test_wizard_pins_under_the_alias_remote_unlock_uses(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.pwd, "getpwnam", lambda _name: _owner(tmp_path))
        answers = wizard._Answers("op", None, tmp_path / "id.pub", "pi", "pi", "")
        plan = ImagePlan(distribution="arch")
        wizard._save_unlock_record(plan, answers, "pi", "x.onion", [ECDSA])
        name = next((tmp_path / unlock.RECORDS_SUBPATH).glob("*.json")).stem
        pinned = (tmp_path / hostkeys.KNOWN_HOSTS_SUBPATH).read_text()
        assert pinned.startswith(f"{hostkeys.host_key_alias(name)} ")


class TestBackendHostKeys:
    def test_mkinitcpio_creates_ssh_keys_before_the_build(self, tmp_path, fake_runner):
        (tmp_path / "etc").mkdir()
        hooks = f"{mkinitcpio.MKINITCPIO_HOOKS_PREFIX} {mkinitcpio.MKINITCPIO_HOOKS_SUFFIX}"
        (tmp_path / "etc/mkinitcpio.conf").write_text(f"MODULES=()\nBINARIES=()\nHOOKS=({hooks})\n")
        MkinitcpioBackend().configure_initramfs(ImagePlan(raspberry_pi_version="4"), tmp_path)
        script = next(text for _, cmd, text in fake_runner.calls if text and "mkinitcpio" in text)
        assert script.index("ssh-keygen -A") < script.index("mkinitcpio -vP")

    def test_mkinitcpio_reads_the_keys_dropbear_converts(self, tmp_path):
        ssh_dir = tmp_path / "etc/ssh"
        ssh_dir.mkdir(parents=True)
        (ssh_dir / "ssh_host_ecdsa_key.pub").write_text(ECDSA + "\n")
        (ssh_dir / "ssh_host_ed25519_key.pub").write_text("ssh-ed25519 NOT_SERVED\n")
        assert MkinitcpioBackend().host_public_keys(tmp_path) == [ECDSA]

    def test_initramfs_tools_reads_dropbear_keys_in_the_chroot(self, tmp_path, fake_runner):
        key_dir = tmp_path / "etc/dropbear/initramfs"
        key_dir.mkdir(parents=True)
        (key_dir / "dropbear_rsa_host_key").write_bytes(b"binary")
        fake_runner.outputs = {"dropbearkey": f"Public key portion is:\n{RSA}\nFingerprint: x"}
        assert InitramfsToolsBackend().host_public_keys(tmp_path) == [RSA]
        assert fake_runner.find("chroot", "dropbearkey", "/etc/dropbear/initramfs/")
