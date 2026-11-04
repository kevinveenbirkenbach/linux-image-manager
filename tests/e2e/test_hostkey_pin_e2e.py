import os
import pwd

import pytest

from lim import runner
from lim.image import hostkeys, unlock, wizard
from lim.image.plan import ImagePlan
from tests.e2e import ssh_harness
from tests.e2e.ssh_harness import PASSPHRASE, FakeInitramfs

pytestmark = pytest.mark.skipif(
    None in (ssh_harness.SSH, ssh_harness.SSHD, ssh_harness.SSH_KEYGEN),
    reason="needs ssh, sshd and ssh-keygen",
)

TARGET = "127.0.0.1"


@pytest.fixture
def operator(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    key = tmp_path / "client_key"
    public_key = ssh_harness.keygen(key, "ed25519")
    owner = pwd.struct_passwd(("op", "x", os.getuid(), os.getgid(), "", str(home), "/bin/sh"))
    monkeypatch.setattr(wizard.pwd, "getpwnam", lambda _name: owner)
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    return {"home": home, "key": key, "pub": public_key, "env": env}


def _create_image_record(operator, host_public_key):
    answers = wizard._Answers("op", None, operator["key"].with_suffix(".pub"), "pi", "pi", "")
    plan = ImagePlan(distribution="arch")
    wizard._save_unlock_record(plan, answers, "pi", TARGET, [host_public_key])


def _remote_unlock(monkeypatch, operator, server, env):
    results = []

    def run_against_stand_in(argv, **_kwargs):
        argv = ssh_harness.hermetic(argv, server.port, operator["key"], "/dev/null")
        results.append(ssh_harness.deliver(argv, env))
        return results[-1]

    monkeypatch.setattr(runner, "run", run_against_stand_in)
    unlock.remote_unlock()
    return results[-1]


def test_pinned_key_unlocks(tmp_path, operator, answers, monkeypatch):
    with FakeInitramfs(tmp_path / "real", operator["pub"]) as server:
        _create_image_record(operator, server.host_public_key)
        answers("1")
        result = _remote_unlock(monkeypatch, operator, server, operator["env"])
        assert result.returncode == 0, result.stderr
        assert "UNLOCKED" in result.stdout
        assert server.passphrase_received() == PASSPHRASE


def test_impostor_is_refused_before_the_passphrase_prompt(tmp_path, operator, answers, monkeypatch):
    with FakeInitramfs(tmp_path / "real", operator["pub"]) as real:
        _create_image_record(operator, real.host_public_key)
    with FakeInitramfs(tmp_path / "impostor", operator["pub"]) as impostor:
        answers("1")
        result = _remote_unlock(monkeypatch, operator, impostor, operator["env"])
        assert result.returncode != 0
        assert "REMOTE HOST IDENTIFICATION HAS CHANGED" in result.stderr
        assert impostor.passphrase_received() is None


def test_generated_ssh_config_block_pins_the_key(tmp_path, operator):
    config = str(operator["home"] / hostkeys.SSH_CONFIG_SUBPATH)
    with FakeInitramfs(tmp_path / "real", operator["pub"]) as server:
        _create_image_record(operator, server.host_public_key)
        argv = ssh_harness.hermetic(["ssh", "boot.pi"], server.port, operator["key"], config)
        result = ssh_harness.deliver(argv, operator["env"])
        assert result.returncode == 0, result.stderr
        assert server.passphrase_received() == PASSPHRASE
    with FakeInitramfs(tmp_path / "impostor", operator["pub"]) as impostor:
        argv = ssh_harness.hermetic(["ssh", "boot.pi"], impostor.port, operator["key"], config)
        result = ssh_harness.deliver(argv, operator["env"])
        assert result.returncode != 0
        assert impostor.passphrase_received() is None


def test_manual_target_asks_once_then_stays_trusted(tmp_path, operator, answers, monkeypatch):
    asked = tmp_path / "asked"
    askpass = tmp_path / "askpass.sh"
    askpass.write_text(f"#!/bin/sh\necho asked >> {asked}\necho yes\n")
    askpass.chmod(0o755)
    env = {**operator["env"], "SSH_ASKPASS": str(askpass), "SSH_ASKPASS_REQUIRE": "force"}
    with FakeInitramfs(tmp_path / "real", operator["pub"]) as server:
        answers(TARGET, "", "N")
        first = _remote_unlock(monkeypatch, operator, server, env)
        assert first.returncode == 0, first.stderr
        answers(TARGET, "", "N")
        second = _remote_unlock(monkeypatch, operator, server, env)
        assert second.returncode == 0, second.stderr
        assert asked.read_text().splitlines() == ["asked"], first.stderr
        assert server.passphrase_received() == PASSPHRASE
