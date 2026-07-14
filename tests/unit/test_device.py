import pytest

from lim import device
from lim.device import Device
from lim.errors import LimError


class TestPartitionNaming:
    def test_letter_suffix_devices_append_number(self):
        assert Device("sda").partition(1) == "/dev/sda1"
        assert Device("sdb").partition(2) == "/dev/sdb2"

    def test_digit_suffix_devices_get_p_infix(self):
        assert Device("mmcblk0").partition(1) == "/dev/mmcblk0p1"
        assert Device("nvme0n1").partition(2) == "/dev/nvme0n1p2"


class TestOptimalBlocksize:
    def test_uses_64_times_physical_block_size(self, tmp_path):
        queue = tmp_path / "sda" / "queue"
        queue.mkdir(parents=True)
        (queue / "physical_block_size").write_text("512\n")
        assert device.optimal_blocksize("sda", tmp_path) == str(64 * 512)

    def test_falls_back_to_4k_when_missing(self, tmp_path):
        assert device.optimal_blocksize("sda", tmp_path) == "4K"

    def test_falls_back_to_4k_on_garbage(self, tmp_path):
        queue = tmp_path / "sda" / "queue"
        queue.mkdir(parents=True)
        (queue / "physical_block_size").write_text("not-a-number")
        assert device.optimal_blocksize("sda", tmp_path) == "4K"


class TestOverwriteDevice:
    @pytest.fixture
    def sda(self, monkeypatch):
        monkeypatch.setattr(Device, "optimal_blocksize", property(lambda self: "4K"))
        return Device("sda")

    def test_full_overwrite(self, sda, fake_runner, answers):
        answers("y")
        device.overwrite_device(sda)
        dd_calls = fake_runner.find("dd", "if=/dev/zero", "of=/dev/sda")
        assert len(dd_calls) == 1
        assert not any("count=" in part for part in dd_calls[0])

    @pytest.mark.parametrize("answer", ["", "N"])
    def test_skip(self, sda, fake_runner, answers, answer):
        answers(answer)
        device.overwrite_device(sda)
        assert fake_runner.find("dd") == []

    def test_block_count(self, sda, fake_runner, answers):
        answers("34")
        device.overwrite_device(sda)
        assert len(fake_runner.find("dd", "count=34", "bs=4K")) == 1

    def test_invalid_input_raises(self, sda, fake_runner, answers):
        answers("nonsense")
        with pytest.raises(LimError):
            device.overwrite_device(sda)


class TestSelectDevice:
    def test_valid_device(self, fake_runner, answers, monkeypatch):
        answers("sda")
        monkeypatch.setattr(device, "is_block_device", lambda path: path == "/dev/sda")
        assert device.select_device() == Device("sda")

    def test_invalid_device_raises(self, fake_runner, answers, monkeypatch):
        answers("nope")
        monkeypatch.setattr(device, "is_block_device", lambda path: False)
        with pytest.raises(LimError):
            device.select_device()


def test_is_mounted(fake_runner):
    fake_runner.outputs["mount"] = (
        "/dev/sda1 on /boot type vfat (rw)\n/dev/mapper/x on /media/x type btrfs (rw)"
    )
    assert device.is_mounted("/dev/sda1")
    assert device.is_mounted("/media/x")
    assert not device.is_mounted("/dev/sdb")
