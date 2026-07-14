import pytest

from lim import device
from lim.device import Device
from lim.storage import raid1, single_drive
from lim.storage.common import StorageTarget


@pytest.fixture
def block_devices(monkeypatch):
    monkeypatch.setattr(device, "is_block_device", lambda path: True)
    monkeypatch.setattr(Device, "optimal_blocksize", property(lambda self: "4K"))


def test_storage_target_derives_all_paths():
    target = StorageTarget(Device("sdb"))
    assert target.mapper_name == "encrypteddrive-sdb"
    assert target.mapper_path == "/dev/mapper/encrypteddrive-sdb"
    assert target.mount_path == "/media/encrypteddrive-sdb"
    assert target.partition_path == "/dev/sdb1"


def test_single_drive_setup_command_sequence(
    fake_runner, answers, block_devices, monkeypatch
):
    monkeypatch.setattr("lim.system.real_user", lambda: "kevin")
    answers("sdb", "N")  # device name, skip overwrite

    single_drive.setup()

    fdisk_calls = [
        (cmd, input_text)
        for kind, cmd, input_text in fake_runner.calls
        if kind == "run" and cmd[0] == "fdisk"
    ]
    assert [input_text for _, input_text in fdisk_calls] == [
        single_drive.CREATE_GPT_TABLE_INPUT,
        single_drive.CREATE_PARTITION_INPUT,
    ]
    assert len(fake_runner.find("cryptsetup", "-y", "luksFormat", "/dev/sdb1")) == 1
    assert len(fake_runner.find("cryptsetup", "luksOpen", "encrypteddrive-sdb")) == 1
    assert len(fake_runner.find("mkfs.btrfs", "/dev/mapper/encrypteddrive-sdb")) == 1
    assert len(fake_runner.find("mount", "/media/encrypteddrive-sdb")) == 1
    assert len(fake_runner.find("chown", "kevin:kevin")) == 1


def test_single_drive_umount(fake_runner, answers, block_devices):
    answers("sdb")
    single_drive.umount()
    assert len(fake_runner.find("umount", "/dev/mapper/encrypteddrive-sdb")) == 1
    assert len(fake_runner.find("cryptsetup", "luksClose", "encrypteddrive-sdb")) == 1


def test_raid1_setup_uses_both_whole_devices(fake_runner, answers, block_devices):
    answers("sdb", "sdc")
    raid1.setup()
    assert len(fake_runner.find("cryptsetup", "luksFormat", "/dev/sdb")) == 1
    assert len(fake_runner.find("cryptsetup", "luksFormat", "/dev/sdc")) == 1
    mkfs = fake_runner.find("mkfs.btrfs", "-m raid1", "-d raid1")
    assert mkfs == [
        [
            "mkfs.btrfs",
            "-m",
            "raid1",
            "-d",
            "raid1",
            "/dev/mapper/encrypteddrive-sdb",
            "/dev/mapper/encrypteddrive-sdc",
        ]
    ]
