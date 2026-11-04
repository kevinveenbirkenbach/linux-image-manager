import os

from lim import cli
from lim.image import hostkeys, unlock


class TestBuildUnlockArgv:
    def test_onion_wraps_torsocks_and_runs_cryptroot_unlock(self):
        argv = unlock.build_unlock_argv("abc.onion", "/k/id", "cryptroot-unlock", "boot.pi")
        assert argv[0] == "torsocks"
        assert "root@abc.onion" in argv
        assert argv[argv.index("-i") + 1] == "/k/id"
        assert argv[-1] == "cryptroot-unlock"
        assert "-t" in argv

    def test_direct_target_is_plain_ssh(self):
        argv = unlock.build_unlock_argv("192.168.1.5", "", "", "boot.192.168.1.5")
        assert "torsocks" not in argv
        assert argv[-1] == "root@192.168.1.5"
        assert "-t" not in argv
        assert "-i" not in argv

    def test_host_key_is_checked_against_the_pinned_alias(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        argv = unlock.build_unlock_argv("a.onion", "", "", "boot.pi")
        assert "HostKeyAlias=boot.pi" in argv
        assert f"UserKnownHostsFile={tmp_path / hostkeys.KNOWN_HOSTS_SUBPATH}" in argv
        assert "StrictHostKeyChecking=ask" in argv
        assert not any("/dev/null" in part or part.endswith("=no") for part in argv)

    def test_record_and_manual_entry_pick_their_alias(
        self, tmp_path, answers, fake_runner, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(unlock, "_load_records", lambda: [("pi", {"target": "x.onion"})])
        answers("1")
        unlock.remote_unlock()
        answers("", "10.0.0.9", "", "N")
        unlock.remote_unlock()
        aliases = [arg for cmd in fake_runner.commands() for arg in cmd if "HostKeyAlias" in arg]
        assert aliases == ["HostKeyAlias=boot.pi", "HostKeyAlias=boot.10.0.0.9"]


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
