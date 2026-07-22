import pytest

from lim import fsutil
from lim.errors import LimError


def test_replace_in_file_replaces_all_occurrences(tmp_path):
    target = tmp_path / "conf"
    target.write_text("MODULES=()\nHOOKS=(base)\nMODULES=()\n")
    fsutil.replace_in_file("MODULES=()", "MODULES=(x)", target)
    assert target.read_text() == "MODULES=(x)\nHOOKS=(base)\nMODULES=(x)\n"


def test_replace_in_file_fails_when_search_missing(tmp_path):
    target = tmp_path / "conf"
    target.write_text("nothing here\n")
    with pytest.raises(LimError):
        fsutil.replace_in_file("MODULES=()", "MODULES=(x)", target)
    assert target.read_text() == "nothing here\n"


def test_ensure_line_appends_once(tmp_path):
    target = tmp_path / "fstab"
    target.write_text("existing entry\n")
    assert fsutil.ensure_line_in_file("new entry", target) is True
    assert fsutil.ensure_line_in_file("new entry", target) is False
    assert target.read_text() == "existing entry\nnew entry\n"


def test_ensure_line_creates_file_and_handles_missing_newline(tmp_path):
    target = tmp_path / "crypttab"
    assert fsutil.ensure_line_in_file("first", target) is True
    target.write_text("no newline at end")
    assert fsutil.ensure_line_in_file("second", target) is True
    assert target.read_text() == "no newline at end\nsecond\n"


def test_drop_fstab_mount_removes_matching_mount_only(tmp_path):
    target = tmp_path / "fstab"
    target.write_text(
        "# comment / stays\n"
        "PARTUUID=aa-02  /  ext4  defaults  0  1\n"
        "PARTUUID=aa-01  /boot/firmware  vfat  defaults  0  2\n"
    )
    fsutil.drop_fstab_mount("/", target)
    remaining = target.read_text()
    assert "PARTUUID=aa-02" not in remaining
    assert "# comment / stays" in remaining
    assert "/boot/firmware" in remaining


def test_drop_fstab_mount_is_noop_when_absent(tmp_path):
    target = tmp_path / "fstab"
    target.write_text("PARTUUID=aa-01  /boot  vfat  defaults  0  2\n")
    fsutil.drop_fstab_mount("/", target)
    assert target.read_text() == "PARTUUID=aa-01  /boot  vfat  defaults  0  2\n"
    fsutil.drop_fstab_mount("/", tmp_path / "missing")  # no crash
