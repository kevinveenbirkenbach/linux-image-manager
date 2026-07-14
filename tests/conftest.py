import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lim import runner, ui
from lim.errors import LimError


class FakeRunner:
    """Records every command instead of executing it.

    ``outputs``/``success_by_fragment``/``failures`` map a substring of the
    joined command to the canned behavior.
    """

    def __init__(self):
        self.calls: list[tuple[str, list, str | None]] = []
        self.outputs: dict[str, str] = {}
        self.failures: set[str] = set()
        self.success_by_fragment: dict[str, bool] = {}
        self.sudo_log: list[tuple[list[str], bool]] = []

    def _fails(self, cmd: list[str]) -> bool:
        joined = " ".join(cmd)
        return any(fragment in joined for fragment in self.failures)

    def run(self, cmd, *, sudo=False, input_text=None, check=True, error_msg=None):
        cmd = [str(part) for part in cmd]
        self.calls.append(("run", cmd, input_text))
        self.sudo_log.append((cmd, sudo))
        returncode = 1 if self._fails(cmd) else 0
        if check and returncode != 0:
            raise LimError(error_msg or f"Command failed: {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, returncode)

    def output(self, cmd, *, sudo=False, check=True, error_msg=None):
        cmd = [str(part) for part in cmd]
        self.calls.append(("output", cmd, None))
        joined = " ".join(cmd)
        for fragment, value in self.outputs.items():
            if fragment in joined:
                return value
        return ""

    def succeeds(self, cmd, *, sudo=False):
        cmd = [str(part) for part in cmd]
        self.calls.append(("succeeds", cmd, None))
        joined = " ".join(cmd)
        for fragment, value in self.success_by_fragment.items():
            if fragment in joined:
                return value
        return False

    def pipeline(self, *cmds, sudo_last=False, error_msg=None):
        cmds = [[str(part) for part in cmd] for cmd in cmds]
        self.calls.append(("pipeline", cmds, None))
        for cmd in cmds:
            if self._fails(cmd):
                raise LimError(error_msg or "Pipeline failed")

    def sync_disks(self):
        self.calls.append(("run", ["sync"], None))

    def commands(self) -> list[list[str]]:
        return [cmd for _, cmd, _ in self.calls]

    def find(self, *fragments: str) -> list[list[str]]:
        """All recorded commands whose joined form contains every fragment."""
        result = []
        for command in self.commands():
            joined = " ".join(
                " ".join(part) if isinstance(part, list) else part for part in command
            )
            if all(fragment in joined for fragment in fragments):
                result.append(command)
        return result


@pytest.fixture
def fake_runner(monkeypatch):
    fake = FakeRunner()
    monkeypatch.setattr(runner, "run", fake.run)
    monkeypatch.setattr(runner, "output", fake.output)
    monkeypatch.setattr(runner, "succeeds", fake.succeeds)
    monkeypatch.setattr(runner, "pipeline", fake.pipeline)
    monkeypatch.setattr(runner, "sync_disks", fake.sync_disks)
    return fake


@pytest.fixture
def answers(monkeypatch):
    """Feed scripted answers to ui.ask (and thereby ui.confirm)."""
    queue: list[str] = []

    def fake_ask(prompt: str) -> str:
        assert queue, f"No scripted answer left for prompt: {prompt}"
        return queue.pop(0)

    monkeypatch.setattr(ui, "ask", fake_ask)

    def feed(*items: str) -> None:
        queue.extend(items)

    return feed
