from pathlib import Path

from tests.e2e.qemu import config, harness
from tests.e2e.test_qemu_harness_unit import BUILD_SCRIPT, _spec


def test_ssh_argv_checks_the_pinned_host_key_strictly():
    argv = config.ssh_argv(_spec())
    assert f"HostKeyAlias={config.HOST_KEY_ALIAS}" in argv
    assert "UserKnownHostsFile=/work/known_hosts" in argv
    assert "StrictHostKeyChecking=yes" in argv
    assert not any("/dev/null" in part for part in argv)


def test_build_creates_ssh_host_keys_before_the_initramfs_like_lim():
    script = BUILD_SCRIPT.read_text()
    assert script.index('"$ROOTFS" ssh-keygen -A') < script.index('"$ROOTFS" mkinitcpio -P')


def test_pins_the_built_rootfs_keys_with_lim_backend(tmp_path):
    ssh_dir = tmp_path / "rootfs/etc/ssh"
    ssh_dir.mkdir(parents=True)
    (ssh_dir / "ssh_host_ecdsa_key.pub").write_text("ecdsa-sha2-nistp256 AAAA root@x\n")
    harness._pin_host_keys(harness.HarnessConfig(repo_root=Path("/repo"), work_dir=tmp_path))
    pinned = (tmp_path / "known_hosts").read_text()
    assert pinned == f"{config.HOST_KEY_ALIAS} ecdsa-sha2-nistp256 AAAA\n"
