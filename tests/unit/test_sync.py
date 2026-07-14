from pathlib import Path

import pytest

from lim import config, system
from lim.data import sync
from lim.errors import LimError


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "home/kevin"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh/id_rsa").write_text("key")
    (home / ".gitconfig").write_text("[user]")
    return home


@pytest.fixture
def data_path(tmp_path):
    return tmp_path / "decrypted/data"


@pytest.fixture
def backup_folder(tmp_path):
    return tmp_path / "decrypted/backup/import/20260707000000"


def test_import_plan_only_covers_existing_items(home, data_path, backup_folder):
    operations = sync.build_sync_plan("import", home, data_path, backup_folder)
    sources = [operation.source for operation in operations]
    assert sources == [f"{home}/.ssh/", f"{home}/.gitconfig"]
    for operation in operations:
        assert operation.destination.startswith(str(data_path))


def test_export_swaps_source_and_destination(home, data_path, backup_folder):
    exported = Path(f"{data_path}{home}/.gitconfig")
    exported.parent.mkdir(parents=True)
    exported.write_text("[user]")
    operations = sync.build_sync_plan("export", home, data_path, backup_folder)
    assert operations == [
        sync.SyncOperation(
            source=str(exported),
            destination=f"{home}/.gitconfig",
            backup_dir=str(Path(f"{backup_folder}{home}")),
            is_directory=False,
        )
    ]


def test_unknown_mode_raises(home, data_path, backup_folder):
    with pytest.raises(LimError):
        sync.build_sync_plan("sideways", home, data_path, backup_folder)


def test_rsync_command_uses_delete_only_for_directories():
    directory_op = sync.SyncOperation("src/", "dst/", "backup", is_directory=True)
    file_op = sync.SyncOperation("src", "dst", "backup", is_directory=False)
    assert sync.rsync_command(directory_op) == [
        "rsync", "-abcEPuvW", "--delete", "--backup-dir=backup", "src/", "dst/"
    ]
    assert sync.rsync_command(file_op) == [
        "rsync", "-abcEPuvW", "--backup-dir=backup", "src", "dst"
    ]


def test_import_syncs_from_real_home(tmp_path, fake_runner, monkeypatch):
    real_home = tmp_path / "home/kevin"
    real_home.mkdir(parents=True)
    (real_home / ".gitconfig").write_text("[user]")
    monkeypatch.setattr(system, "real_home", lambda: real_home)
    monkeypatch.setattr(config, "DECRYPTED_PATH", tmp_path / "decrypted")
    monkeypatch.setattr(config, "DATA_PATH", tmp_path / "decrypted/data")
    monkeypatch.setattr(config, "BACKUP_PATH", tmp_path / "decrypted/backup")
    fake_runner.outputs["mount"] = f"encfs on {tmp_path / 'decrypted'} type fuse"

    sync.import_from_system()

    rsync_calls = fake_runner.find("rsync")
    assert len(rsync_calls) == 1
    assert rsync_calls[0][-2] == str(real_home / ".gitconfig")


def test_export_chowns_real_home_without_sudo(tmp_path, fake_runner, monkeypatch):
    real_home = tmp_path / "home/kevin"
    (real_home / ".ssh").mkdir(parents=True)
    (real_home / ".ssh/id_rsa").write_text("key")
    monkeypatch.setattr(system, "real_home", lambda: real_home)
    monkeypatch.setattr(system, "real_user", lambda: "kevin")
    monkeypatch.setattr(config, "DECRYPTED_PATH", tmp_path / "decrypted")
    monkeypatch.setattr(config, "DATA_PATH", tmp_path / "decrypted/data")
    monkeypatch.setattr(config, "BACKUP_PATH", tmp_path / "decrypted/backup")
    fake_runner.outputs["mount"] = f"encfs on {tmp_path / 'decrypted'} type fuse"

    sync.export_to_system()

    chown_calls = [
        (cmd, sudo) for cmd, sudo in fake_runner.sudo_log if cmd[0] == "chown"
    ]
    assert chown_calls == [
        (["chown", "-R", "kevin:kevin", str(real_home)], False)
    ]
    assert (real_home / ".ssh/id_rsa").stat().st_mode & 0o777 == 0o600


def test_execute_sync_plan_creates_folders_and_runs_rsync(
    tmp_path, fake_runner
):
    operation = sync.SyncOperation(
        source=str(tmp_path / "src.txt"),
        destination=str(tmp_path / "deep/nested/dst.txt"),
        backup_dir=str(tmp_path / "backup/deep"),
        is_directory=False,
    )
    sync.execute_sync_plan([operation])
    assert (tmp_path / "deep/nested").is_dir()
    assert (tmp_path / "backup/deep").is_dir()
    assert len(fake_runner.find("rsync", "-abcEPuvW")) == 1
