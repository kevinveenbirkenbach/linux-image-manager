from lim.device import Device
from lim.image.session import ImageSession


def test_partition_paths_for_sd_card():
    session = ImageSession(Device("mmcblk0"))
    assert session.boot_partition_path == "/dev/mmcblk0p1"
    assert session.root_partition_path == "/dev/mmcblk0p2"
    assert session.root_mapper_path == "/dev/mmcblk0p2"


def test_decrypt_root_on_luks_partition(fake_runner):
    fake_runner.outputs["-s TYPE"] = "crypto_LUKS"
    fake_runner.outputs["-s UUID"] = "uuid-1"
    session = ImageSession(Device("sda"))
    session.decrypt_root()
    assert session.root_mapper_name == "linux-image-manager-uuid-1"
    assert session.root_mapper_path == "/dev/mapper/linux-image-manager-uuid-1"
    assert len(fake_runner.find("cryptsetup", "luksOpen", "/dev/sda2")) == 1


def test_decrypt_root_skips_plain_partition(fake_runner):
    fake_runner.outputs["-s TYPE"] = "ext4"
    session = ImageSession(Device("sda"))
    session.decrypt_root()
    assert session.root_mapper_name is None
    assert session.root_mapper_path == "/dev/sda2"
    assert fake_runner.find("cryptsetup") == []


def test_destructor_unmounts_everything_despite_failures(tmp_path, fake_runner):
    session = ImageSession(Device("sda"))
    session.working_folder = tmp_path
    session.boot_mount_path = tmp_path / "boot"
    session.root_mount_path = tmp_path / "root"
    fake_runner.failures.add("umount")  # every umount fails; cleanup must go on

    session.destructor()

    umounted = [cmd[-1] for cmd in fake_runner.find("umount")]
    root = str(session.root_mount_path)
    # chroot binds first (deepest path first), then the partitions
    assert umounted == [
        f"{root}/dev/pts",
        f"{root}/dev",
        f"{root}/proc",
        f"{root}/sys",
        f"{root}/boot",
        root,
        str(session.boot_mount_path),
    ]
    removed = [cmd[-1] for cmd in fake_runner.find("rmdir")]
    assert removed == [root, str(session.boot_mount_path), str(tmp_path)]


def test_destructor_closes_luks_mapper(tmp_path, fake_runner):
    fake_runner.outputs["-s TYPE"] = "crypto_LUKS"
    fake_runner.outputs["-s UUID"] = "uuid-1"
    session = ImageSession(Device("sda"))
    session.decrypt_root()
    session.destructor()
    assert len(fake_runner.find("luksClose", "linux-image-manager-uuid-1")) == 1


def test_boot_bind_target_bookworm_uses_boot_firmware(tmp_path):
    session = ImageSession(Device("sda"))
    session.root_mount_path = tmp_path
    (tmp_path / "boot/firmware").mkdir(parents=True)
    assert session.boot_bind_target() == f"{tmp_path}/boot/firmware"


def test_boot_bind_target_legacy_uses_boot(tmp_path):
    session = ImageSession(Device("sda"))
    session.root_mount_path = tmp_path
    (tmp_path / "boot").mkdir()
    assert session.boot_bind_target() == f"{tmp_path}/boot"
