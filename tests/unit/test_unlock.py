import os

from lim import cli
from lim.image import unlock


class TestBuildUnlockArgv:
    def test_onion_wraps_torsocks_and_runs_cryptroot_unlock(self):
        argv = unlock.build_unlock_argv("abc.onion", "/k/id", "cryptroot-unlock")
        assert argv[0] == "torsocks"
        assert "root@abc.onion" in argv
        assert argv[argv.index("-i") + 1] == "/k/id"
        assert argv[-1] == "cryptroot-unlock"
        assert "-t" in argv

    def test_direct_target_is_plain_ssh(self):
        argv = unlock.build_unlock_argv("192.168.1.5", "", "")
        assert "torsocks" not in argv
        assert argv[-1] == "root@192.168.1.5"
        assert "-t" not in argv
        assert "-i" not in argv

    def test_host_key_checking_disabled(self):
        assert "StrictHostKeyChecking=no" in unlock.build_unlock_argv("a.onion", "", "")


class TestRecords:
    def test_save_and_load_record_roundtrip(self, tmp_path, monkeypatch):
        record = {"target": "xyz.onion", "key": "/k/id", "unlock_command": "cryptroot-unlock"}
        unlock.save_record(tmp_path, os.getuid(), os.getgid(), "myhost", record)
        assert (tmp_path / unlock.RECORDS_SUBPATH / "myhost.json").is_file()
        monkeypatch.setattr(
            unlock, "records_dir", lambda home=None: tmp_path / unlock.RECORDS_SUBPATH
        )
        assert unlock._load_records() == [("myhost", record)]


class TestCliRegistration:
    def test_remote_unlock_registered_without_root(self):
        command = cli.COMMANDS["remote-unlock"]
        assert command.func is unlock.remote_unlock
        assert command.needs_root is False
