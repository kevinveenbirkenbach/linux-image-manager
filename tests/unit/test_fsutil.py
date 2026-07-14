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
