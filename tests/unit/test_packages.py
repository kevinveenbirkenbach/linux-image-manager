import pytest

from lim import config, packages
from lim.errors import LimError


@pytest.fixture
def package_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PACKAGE_PATH", tmp_path)
    return tmp_path


def test_strips_comments_and_blank_lines(package_dir):
    (package_dir / "general.txt").write_text(
        "# header comment\nnano\ntree# inline comment\n\nhtop\n"
    )
    assert packages.get_packages("general") == ["nano", "tree", "htop"]


def test_multiple_collections_are_concatenated(package_dir):
    (package_dir / "a.txt").write_text("one\n")
    subdir = package_dir / "server"
    subdir.mkdir()
    (subdir / "luks.txt").write_text("two\nthree\n")
    assert packages.get_packages("a", "server/luks") == ["one", "two", "three"]


def test_missing_collection_raises(package_dir):
    with pytest.raises(LimError):
        packages.get_packages("does-not-exist")
