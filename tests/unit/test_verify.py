import hashlib

import pytest

from lim.errors import LimError
from lim.image import verify

CONTENT = b"fake image content"


@pytest.fixture
def image(tmp_path):
    path = tmp_path / "image.img"
    path.write_bytes(CONTENT)
    return path


@pytest.mark.parametrize("algorithm", ["md5", "sha1", "sha256", "sha512"])
def test_matching_checksum_passes(image, algorithm):
    checksum = hashlib.new(algorithm, CONTENT).hexdigest()
    verify.verify_checksum(image, checksum)


def test_uppercase_checksum_passes(image):
    checksum = hashlib.sha256(CONTENT).hexdigest().upper()
    verify.verify_checksum(image, checksum)


def test_wrong_checksum_raises(image):
    checksum = hashlib.sha256(b"other content").hexdigest()
    with pytest.raises(LimError):
        verify.verify_checksum(image, checksum)


def test_unrecognized_digest_length_raises(image):
    with pytest.raises(LimError):
        verify.verify_checksum(image, "abc123")


def test_missing_checksum_is_skipped(image):
    verify.verify_checksum(image, None)  # must not raise


def test_resolve_checksum_takes_first_available(fake_runner):
    fake_runner.success_by_fragment["image.img.sha1"] = False
    fake_runner.success_by_fragment["image.img.sha512"] = True
    fake_runner.outputs["-q -O -"] = "deadbeef  image.img"
    assert verify.resolve_checksum("https://example.org/image.img") == "deadbeef"


def test_resolve_checksum_returns_none_without_sources(fake_runner):
    assert verify.resolve_checksum("https://example.org/image.img") is None
