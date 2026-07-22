"""Image integrity (checksums) and authenticity (GPG signatures) checks."""

import hashlib
import re
from pathlib import Path

from lim import runner, ui
from lim.errors import LimError

ALGORITHM_BY_DIGEST_LENGTH = {
    32: "md5",
    40: "sha1",
    64: "sha256",
    128: "sha512",
}


def url_exists(url: str) -> bool:
    return runner.succeeds(["wget", "-q", "--method=HEAD", url])


def resolve_checksum(download_url: str) -> str | None:
    """Try to fetch a published checksum next to the image download."""
    for extension in ("sha1", "sha512", "md5"):
        checksum_url = f"{download_url}.{extension}"
        ui.info(
            f"Image Checksum is not defined. Try to download image signature from {checksum_url}."
        )
        if url_exists(checksum_url):
            content = runner.output(["wget", checksum_url, "-q", "-O", "-"])
            checksum = content.split()[0] if content.split() else ""
            if checksum:
                ui.info(f"Defined image_checksum as {checksum}")
                return checksum
        ui.warning(f"No checksum found under {checksum_url}.")
    return None


def verify_checksum(image_path: str | Path, checksum: str | None) -> None:
    """Verify the image against an md5/sha1/sha256/sha512 hex checksum."""
    if not checksum:
        ui.warning("No checksum is defined. Skipping checksum verification.")
        return
    algorithm = ALGORITHM_BY_DIGEST_LENGTH.get(len(checksum))
    if algorithm is None:
        raise LimError(
            f"Checksum '{checksum}' has no recognized digest length "
            "(expected md5, sha1, sha256 or sha512)."
        )
    ui.info(f"Checking {algorithm} checksum...")
    digest = hashlib.new(algorithm)
    with Path(image_path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != checksum.lower():
        raise LimError("Verification failed. HINT: Force the download of the image.")
    ui.info(f"{algorithm} checksum verified.")


def verify_signature(download_url: str, image_path: str | Path, image_folder: Path) -> None:
    """Best-effort GPG signature verification of the downloaded image."""
    ui.info("Note: Checksums verify integrity but do not confirm authenticity.")
    ui.info(
        "Proceeding to signature verification, which ensures the file comes from a trusted source."
    )
    signature_url = f"{download_url}.sig"
    ui.info(f"Attempting to download the image signature from: {signature_url}")
    if not url_exists(signature_url):
        ui.warning(f"No signature found under {signature_url}.")
        return

    signature_path = image_folder / (Path(str(image_path)).name + ".sig")
    if not runner.succeeds(["wget", "-q", "-O", str(signature_path), signature_url]):
        ui.warning("Failed to download the signature file.")
        return

    ui.info("Extract the key ID from the signature file")
    verification = runner.output(
        ["gpg", "--status-fd", "1", "--verify", str(signature_path), str(image_path)],
        check=False,
    )
    missing_keys = re.findall(r"NO_PUBKEY (\S+)", verification)
    if missing_keys:
        key_id = missing_keys[-1]
        if runner.succeeds(["gpg", "--list-keys", key_id]):
            ui.info(f"Key {key_id} already in keyring.")
        else:
            ui.info("Import the public key")
            runner.run(
                ["gpg", "--keyserver", "keyserver.ubuntu.com", "--recv-keys", key_id],
                check=False,
            )

    ui.info("Verify the signature")
    if runner.succeeds(["gpg", "--verify", str(signature_path), str(image_path)]):
        ui.info("Signature verification succeeded.")
    else:
        ui.warning("Signature verification failed.")
