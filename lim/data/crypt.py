"""Lock/unlock the encfs-encrypted data directory."""

from lim import config, runner, ui


def unlock() -> None:
    ui.info(f"Unlocking directory {config.DECRYPTED_PATH}...")
    if not config.DECRYPTED_PATH.is_dir():
        ui.info(f"Creating directory {config.DECRYPTED_PATH}...")
        config.DECRYPTED_PATH.mkdir()
    ui.info(f"Decrypting directory {config.ENCRYPTED_PATH} to {config.DECRYPTED_PATH}...")
    runner.run(["encfs", str(config.ENCRYPTED_PATH), str(config.DECRYPTED_PATH)])
    print("ATTENTION: DATA IS NOW DECRYPTED!")


def lock() -> None:
    ui.info(f"Locking directory {config.DECRYPTED_PATH}...")
    runner.run(
        ["fusermount", "-u", str(config.DECRYPTED_PATH)],
        error_msg="Unmounting failed.",
    )
    ui.info("Data is now encrypted.")
    ui.info(f"Removing directory {config.DECRYPTED_PATH}...")
    config.DECRYPTED_PATH.rmdir()
