"""Tests against the real runner module (no fake) using harmless commands."""

import subprocess

import pytest

from lim import runner, ui
from lim.errors import LimError

MISSING = "lim-definitely-missing-binary-x"


class TestMissingBinaries:
    def test_run_raises_lim_error(self):
        with pytest.raises(LimError, match="Command not found"):
            runner.run([MISSING])

    def test_run_tolerates_when_check_is_false(self):
        result = runner.run([MISSING], check=False)
        assert result.returncode == runner.COMMAND_NOT_FOUND

    def test_output_raises_lim_error(self):
        with pytest.raises(LimError, match="Command not found"):
            runner.output([MISSING])

    def test_output_tolerates_when_check_is_false(self):
        assert runner.output([MISSING], check=False) == ""

    def test_succeeds_returns_false(self):
        assert runner.succeeds([MISSING]) is False

    def test_tolerated_paths_emit_a_warning(self, monkeypatch):
        warnings = []
        monkeypatch.setattr(ui, "warning", warnings.append)
        runner.run([MISSING], check=False)
        runner.output([MISSING], check=False)
        runner.succeeds([MISSING])
        assert len(warnings) == 3
        assert all("Command not found" in text for text in warnings)

    def test_pipeline_raises_lim_error(self):
        with pytest.raises(LimError, match="Command not found"):
            runner.pipeline(["echo", "x"], [MISSING])

    def test_pipeline_raises_when_first_member_is_missing(self):
        with pytest.raises(LimError, match=f"Command not found: {MISSING}"):
            runner.pipeline([MISSING], ["cat"])

    def test_pipeline_reaps_started_members(self, monkeypatch):
        spawned = []
        original_popen = subprocess.Popen

        def spying_popen(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            spawned.append(process)
            return process

        monkeypatch.setattr(subprocess, "Popen", spying_popen)
        with pytest.raises(LimError, match="Command not found"):
            runner.pipeline(["sleep", "60"], [MISSING])
        assert len(spawned) == 1
        assert spawned[0].poll() is not None  # killed and reaped, not running
        assert spawned[0].stdout.closed

    def test_run_prefers_explicit_error_message(self):
        with pytest.raises(LimError, match="custom message"):
            runner.run([MISSING], error_msg="custom message")

    def test_output_prefers_explicit_error_message(self):
        with pytest.raises(LimError, match="custom message"):
            runner.output([MISSING], error_msg="custom message")


class TestHappyPath:
    def test_run_returns_completed_process(self):
        assert runner.run(["true"]).returncode == 0

    def test_run_raises_on_nonzero_exit(self):
        with pytest.raises(LimError, match="Command failed with code 1"):
            runner.run(["false"])

    def test_output_returns_stripped_stdout(self):
        assert runner.output(["echo", "hello"]) == "hello"

    def test_succeeds_reflects_exit_code(self):
        assert runner.succeeds(["true"]) is True
        assert runner.succeeds(["false"]) is False

    def test_pipeline_runs_and_checks_every_member(self):
        runner.pipeline(["echo", "x"], ["cat"])  # must not raise
        with pytest.raises(LimError, match="Pipeline failed"):
            runner.pipeline(["false"], ["cat"])
