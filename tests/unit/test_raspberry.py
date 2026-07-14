import pytest

from lim.device import Device
from lim.image import raspberry
from lim.image.session import ImageSession


@pytest.fixture
def session(tmp_path):
    session = ImageSession(Device("mmcblk0"))
    session.root_mount_path = tmp_path
    session.boot_partition_uuid = "BOOT-UUID"
    return session


class TestSeedBootUuid:
    def test_replaces_mmcblk_reference(self, tmp_path, session):
        fstab = tmp_path / "etc/fstab"
        fstab.parent.mkdir()
        fstab.write_text("/dev/mmcblk0p1  /boot  vfat  defaults  0  0\n")
        raspberry._seed_boot_uuid(session)
        assert fstab.read_text() == "UUID=BOOT-UUID  /boot  vfat  defaults  0  0\n"

    def test_skips_partuuid_based_images(self, tmp_path, session):
        fstab = tmp_path / "etc/fstab"
        fstab.parent.mkdir()
        content = "PARTUUID=6c586e13-01  /boot  vfat  defaults  0  0\n"
        fstab.write_text(content)
        raspberry._seed_boot_uuid(session)  # must not raise
        assert fstab.read_text() == content


class TestEnsureImageMounted:
    def test_reads_uuids_when_boot_already_mounted(self, fake_runner):
        session = ImageSession(Device("sda"))
        fake_runner.outputs["mount"] = "/dev/sda1 on /tmp/x/boot type vfat (rw)"
        # Distinct per-partition values so a boot/root swap cannot pass.
        fake_runner.outputs["/dev/sda1 -s UUID"] = "boot-uuid"
        fake_runner.outputs["/dev/sda2 -s UUID"] = "root-uuid"
        fake_runner.outputs["-s TYPE"] = "crypto_LUKS"

        raspberry._ensure_image_mounted(session)

        assert session.boot_partition_uuid == "boot-uuid"
        assert session.root_partition_uuid == "root-uuid"
        assert session.root_mapper_name == "linux-image-manager-root-uuid"
        assert session.root_mapper_path == "/dev/mapper/linux-image-manager-root-uuid"

    def test_plain_root_keeps_partition_as_mapper(self, fake_runner):
        session = ImageSession(Device("sda"))
        fake_runner.outputs["mount"] = "/dev/sda1 on /tmp/x/boot type vfat (rw)"
        fake_runner.outputs["-s UUID"] = "uuid-7"
        fake_runner.outputs["-s TYPE"] = "ext4"

        raspberry._ensure_image_mounted(session)

        assert session.root_mapper_name is None
        assert session.root_mapper_path == "/dev/sda2"

    def test_mounts_when_nothing_is_mounted(self, fake_runner, tmp_path):
        session = ImageSession(Device("sda"))
        session.boot_mount_path = tmp_path / "boot"
        session.root_mount_path = tmp_path / "root"
        fake_runner.outputs["-s TYPE"] = "ext4"
        fake_runner.outputs["/dev/sda1 -s UUID"] = "boot-uuid"
        fake_runner.outputs["/dev/sda2 -s UUID"] = "root-uuid"

        raspberry._ensure_image_mounted(session)

        assert len(fake_runner.find("mount", "-v")) == 2
        assert session.boot_partition_uuid == "boot-uuid"
        assert session.root_partition_uuid == "root-uuid"
