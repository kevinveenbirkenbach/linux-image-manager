import pytest

from lim import cli, system
from lim.cli import Command
from lim.errors import LimError


@pytest.fixture(autouse=True)
def no_input(monkeypatch):
    monkeypatch.setattr(
        "builtins.input", lambda *args: (_ for _ in ()).throw(AssertionError("unexpected prompt"))
    )


def test_every_command_dispatches_to_its_function(monkeypatch):
    executed = []
    monkeypatch.setitem(
        cli.COMMANDS, "lock", Command(lambda: executed.append("lock"), "d", needs_root=False)
    )
    cli.main(["--type", "lock", "--auto-confirm"])
    assert executed == ["lock"]


def test_needs_root_command_requests_root(monkeypatch):
    escalated = []
    monkeypatch.setattr(system, "ensure_root", lambda: escalated.append(True))
    monkeypatch.setitem(cli.COMMANDS, "backup", Command(lambda: None, "d", needs_root=True))
    cli.main(["--type", "backup", "--auto-confirm"])
    assert escalated == [True]


def test_confirmation_prompt_waits_for_enter(monkeypatch):
    prompts = []
    executed = []
    monkeypatch.setattr("builtins.input", lambda *args: prompts.append(args) or "")
    monkeypatch.setitem(
        cli.COMMANDS, "lock", Command(lambda: executed.append(True), "d", needs_root=False)
    )
    cli.main(["--type", "lock"])
    assert len(prompts) == 1
    assert executed == [True]


def test_lim_error_exits_with_code_1(monkeypatch):
    def failing():
        raise LimError("boom")

    monkeypatch.setitem(cli.COMMANDS, "lock", Command(failing, "d", needs_root=False))
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--type", "lock", "--auto-confirm"])
    assert excinfo.value.code == 1


def test_unknown_type_is_rejected_by_argparse():
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--type", "does-not-exist"])
    assert excinfo.value.code == 2


def test_all_registered_commands_have_descriptions():
    for name, command in cli.COMMANDS.items():
        assert command.description, name
        assert callable(command.func), name
