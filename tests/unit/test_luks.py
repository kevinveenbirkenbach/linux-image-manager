import pytest

from lim import luks
from lim.errors import LimError

LUKS_DUMP = """\
LUKS header information
Version:        2
UUID:           1234-abcd-5678
"""


def test_luks_uuid_parsed_from_dump(fake_runner):
    fake_runner.outputs["luksDump"] = LUKS_DUMP
    assert luks.luks_uuid("/dev/sda1") == "1234-abcd-5678"


def test_luks_uuid_missing_raises(fake_runner):
    fake_runner.outputs["luksDump"] = "no uuid here"
    with pytest.raises(LimError):
        luks.luks_uuid("/dev/sda1")


def test_update_fstab_is_idempotent(tmp_path):
    fstab = tmp_path / "fstab"
    fstab.write_text("# existing\n")
    luks.update_fstab("/dev/mapper/x", "/media/x", fstab_path=fstab)
    luks.update_fstab("/dev/mapper/x", "/media/x", fstab_path=fstab)
    lines = fstab.read_text().splitlines()
    assert lines.count("/dev/mapper/x /media/x btrfs   defaults   0       2") == 1


def test_create_luks_key_and_update_crypttab(tmp_path, fake_runner):
    fake_runner.outputs["luksDump"] = LUKS_DUMP
    key_dir = tmp_path / "luks-keys"
    crypttab = tmp_path / "crypttab"

    luks.create_luks_key_and_update_crypttab(
        "encrypteddrive-sda",
        "/dev/sda1",
        key_directory=key_dir,
        crypttab_path=crypttab,
    )

    keyfile = key_dir / "encrypteddrive-sda.keyfile"
    assert len(fake_runner.find("dd", "if=/dev/urandom", f"of={keyfile}")) == 1
    assert len(fake_runner.find("cryptsetup", "luksAddKey", "/dev/sda1")) == 1
    assert len(fake_runner.find("cryptsetup", "luksOpen", f"--key-file={keyfile}")) == 1
    expected_entry = f"encrypteddrive-sda UUID=1234-abcd-5678 {keyfile} luks"
    assert expected_entry in crypttab.read_text().splitlines()

    # A second run must not duplicate the crypttab entry.
    luks.create_luks_key_and_update_crypttab(
        "encrypteddrive-sda",
        "/dev/sda1",
        key_directory=key_dir,
        crypttab_path=crypttab,
    )
    assert crypttab.read_text().splitlines().count(expected_entry) == 1
