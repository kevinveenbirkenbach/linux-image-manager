import pytest

from lim.errors import LimError
from lim.image import crossarch


class TestCrossArch:
    def test_native_arm_is_ok(self, monkeypatch):
        monkeypatch.setattr(crossarch.platform, "machine", lambda: "aarch64")
        crossarch.ensure_ready()

    def test_cross_arch_with_binfmt_ok(self, monkeypatch):
        monkeypatch.setattr(crossarch.platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(crossarch, "qemu_binfmt_enabled", lambda: True)
        crossarch.ensure_ready()

    def test_declined_auto_install_raises(self, monkeypatch, answers):
        monkeypatch.setattr(crossarch.platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(crossarch, "qemu_binfmt_enabled", lambda: False)
        answers("n")
        with pytest.raises(LimError, match="Cross-architecture"):
            crossarch.ensure_ready()

    def test_auto_install_success_proceeds(self, monkeypatch, answers):
        monkeypatch.setattr(crossarch.platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(crossarch, "qemu_binfmt_enabled", lambda: False)
        monkeypatch.setattr(crossarch, "auto_enable", lambda: True)
        answers("y")
        crossarch.ensure_ready()

    def test_auto_install_failure_raises(self, monkeypatch, answers):
        monkeypatch.setattr(crossarch.platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(crossarch, "qemu_binfmt_enabled", lambda: False)
        monkeypatch.setattr(crossarch, "auto_enable", lambda: False)
        answers("y")
        with pytest.raises(LimError, match="Cross-architecture"):
            crossarch.ensure_ready()

    def test_auto_enable_uses_detected_manager_and_registers(self, monkeypatch, fake_runner):
        monkeypatch.setattr(
            crossarch.shutil, "which", lambda tool: "/bin/pacman" if tool == "pacman" else None
        )
        monkeypatch.setattr(crossarch, "qemu_binfmt_enabled", lambda: True)
        assert crossarch.auto_enable() is True
        assert fake_runner.find("pacman", "-S", "qemu-user-static-binfmt")
        assert fake_runner.find("systemctl", "restart", "systemd-binfmt")

    def test_auto_enable_without_manager_returns_false(self, monkeypatch):
        monkeypatch.setattr(crossarch.shutil, "which", lambda _tool: None)
        assert crossarch.auto_enable() is False
