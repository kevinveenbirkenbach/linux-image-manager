import pytest

from lim import catalog, cli
from lim.device import Device
from lim.errors import LimError
from lim.image import choosers, transfer, wizard
from lim.image.initramfs.initramfs_tools import InitramfsToolsBackend
from lim.image.plan import ImagePlan
from lim.image.session import ImageSession


def _session(tmp_path):
    session = ImageSession(Device("sda"))
    session.working_folder = tmp_path
    session.boot_mount_path = tmp_path / "boot"
    session.root_mount_path = tmp_path / "root"
    session.boot_mount_path.mkdir()
    session.root_mount_path.mkdir()
    return session


class TestCatalogAndChooser:
    def test_catalog_exposes_raspios_latest_endpoints(self):
        images = catalog.raspios_images()
        assert images["lite64"]["source_url"].endswith("raspios_lite_arm64_latest")
        assert images["lite64"]["image"].endswith(".img.xz")

    def test_choose_raspios_sets_source_and_defaults(self, answers):
        answers("lite64")
        plan = ImagePlan(distribution="raspios")
        choosers.choose_raspios(plan)
        assert plan.source_url.endswith("raspios_lite_arm64_latest")
        assert plan.image_name.endswith(".img.xz")
        assert plan.root_filesystem == "ext4"
        assert plan.boot_size == "+512M"

    def test_unknown_variant_raises(self, answers):
        answers("lite999")
        with pytest.raises(LimError, match="isn't supported"):
            choosers.choose_raspios(ImagePlan(distribution="raspios"))

    def test_raspios_is_registered(self):
        assert choosers.DISTRIBUTION_CHOOSERS["raspios"] is choosers.choose_raspios


class TestSourceUrlOverride:
    def test_source_url_wins_over_derived(self):
        plan = ImagePlan(
            base_download_url="http://x/", image_name="a.img.xz", source_url="http://latest"
        )
        assert plan.download_url == "http://latest"

    def test_falls_back_to_base_plus_name(self):
        plan = ImagePlan(base_download_url="http://x/", image_name="a.img.xz")
        assert plan.download_url == "http://x/a.img.xz"


class TestTransferDiskImage:
    def test_builds_encrypted_layout_and_copies_partitions(
        self, tmp_path, fake_runner, monkeypatch
    ):
        monkeypatch.setattr(transfer.shutil, "which", lambda _name: None)  # force cp branch
        fake_runner.outputs = {
            "losetup -Pf": "/dev/loop9",
            "-s TYPE": "crypto_LUKS",
            "-s UUID": "ROOTUUID",
        }
        session = _session(tmp_path)
        plan = ImagePlan(
            distribution="raspios",
            image_name="raspios_lite_arm64_latest.img.xz",
            root_filesystem="ext4",
            boot_size="+512M",
        )
        plan.image_folder = tmp_path

        transfer.transfer_disk_image(plan, session)

        assert fake_runner.find("losetup", "-Pf", "--show")
        assert fake_runner.find("mount", "-o", "ro", "/dev/loop9p1")
        assert fake_runner.find("mount", "-o", "ro", "/dev/loop9p2")
        assert fake_runner.find("fdisk", "/dev/sda")
        assert fake_runner.find("mkfs.vfat", "/dev/sda1")
        assert fake_runner.find("cryptsetup", "luksFormat")
        assert fake_runner.find("cryptsetup", "luksOpen")
        assert fake_runner.find("mkfs.ext4")
        assert fake_runner.find("cp", "-a", "source-root")
        assert fake_runner.find("cp", "-a", "source-boot")
        assert fake_runner.find("losetup", "-d", "/dev/loop9")

    def test_copy_tree_uses_rsync_with_progress(self, fake_runner, monkeypatch):
        monkeypatch.setattr(transfer.shutil, "which", lambda _name: "/usr/bin/rsync")
        transfer._copy_tree("/src", "/dst", ["-aHAX"])
        assert fake_runner.find("rsync", "-aHAX", "--info=progress2", "/src/", "/dst/")

    def test_copy_tree_falls_back_to_cp(self, fake_runner, monkeypatch):
        monkeypatch.setattr(transfer.shutil, "which", lambda _name: None)
        transfer._copy_tree("/src", "/dst", ["-a"])
        assert fake_runner.find("cp", "-a", "/src/.", "/dst")

    def test_encrypted_non_arch_dispatches_to_disk_image(
        self, tmp_path, fake_runner, answers, monkeypatch
    ):
        calls = []
        monkeypatch.setattr(
            transfer, "transfer_disk_image", lambda plan, session: calls.append(plan.distribution)
        )
        answers("N", "N")  # keep partition table, skip zero-overwrite
        plan = ImagePlan(distribution="moode", encrypt_system=True)
        transfer.transfer_image(plan, _session(tmp_path))
        assert calls == ["moode"]

    def test_arch_uses_tarball_path_not_disk_image(
        self, tmp_path, fake_runner, answers, monkeypatch
    ):
        disk, arch = [], []
        monkeypatch.setattr(transfer, "transfer_disk_image", lambda p, s: disk.append(p))
        monkeypatch.setattr(transfer, "transfer_arch_image", lambda p, s: arch.append(p))
        answers("N", "N")
        plan = ImagePlan(distribution="arch", encrypt_system=True)
        transfer.transfer_image(plan, _session(tmp_path))
        assert len(arch) == 1
        assert disk == []

    def test_non_interactive_transfer_skips_erase_prompts(self, tmp_path, fake_runner, monkeypatch):
        monkeypatch.setattr(transfer, "transfer_disk_image", lambda p, s: None)
        plan = ImagePlan(distribution="raspios", encrypt_system=True)
        transfer.transfer_image(plan, _session(tmp_path), interactive=False)
        assert not fake_runner.find("wipefs")  # no prompt, no destructive pre-step

    def test_download_without_force_prompt_does_not_ask(self, tmp_path, fake_runner):
        plan = ImagePlan(distribution="raspios", image_name="x.img.xz", source_url="http://h/x")
        plan.image_folder = tmp_path
        transfer.download_image(plan, force_prompt=False)  # no answers fixture => must not prompt
        assert fake_runner.find("wget", "http://h/x")


class TestBootFstabFix:
    def test_repoints_boot_line_to_new_uuid(self, tmp_path):
        session = _session(tmp_path)
        session.boot_partition_uuid = "BOOTUUID"
        (session.root_mount_path / "etc").mkdir()
        (session.root_mount_path / "etc/fstab").write_text(
            "PARTUUID=aa-02  /  ext4  defaults  0  1\n"
            "PARTUUID=aa-01  /boot/firmware  vfat  defaults  0  2\n"
        )
        transfer._fix_boot_fstab(session)
        fstab = (session.root_mount_path / "etc/fstab").read_text()
        assert "UUID=BOOTUUID  /boot/firmware" in fstab
        assert "PARTUUID=aa-01" not in fstab
        assert "PARTUUID=aa-02  /  ext4" in fstab  # root line untouched here


class TestRegisterEncryptedRootStockFstab:
    def test_existing_root_line_is_replaced_not_duplicated(self, tmp_path):
        session = ImageSession(Device("sda"))
        session.root_mapper_name = "cryptroot"
        session.root_partition_uuid = "ROOT-UUID"
        root = tmp_path / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc/fstab").write_text("PARTUUID=aa-02  /  ext4  defaults  0  1\n")
        plan = ImagePlan(distribution="raspios", root_filesystem="ext4")

        InitramfsToolsBackend().register_encrypted_root(plan, session, root)

        fstab = (root / "etc/fstab").read_text()
        assert fstab.count("  /  ") == 1
        assert "/dev/mapper/cryptroot  /  ext4" in fstab
        assert "PARTUUID=aa-02" not in fstab


class TestWizardSteps:
    def test_build_authorized_keys_copies_pubkey(self, tmp_path):
        pubkey = tmp_path / "id.pub"
        pubkey.write_text("ssh-ed25519 AAAA user@host\n")
        result = wizard._build_authorized_keys(_session(tmp_path), pubkey)
        assert result.read_text() == "ssh-ed25519 AAAA user@host\n"

    def test_ask_pubkey_rejects_missing(self, tmp_path, answers):
        answers(str(tmp_path / "nope.pub"))
        with pytest.raises(LimError, match="not found"):
            wizard._ask_pubkey()

    def test_ask_pubkey_rejects_empty(self, answers):
        answers("")
        with pytest.raises(LimError, match="No SSH public key"):
            wizard._ask_pubkey()

    def test_apply_system_config_sets_hostname_and_enables_ssh(self, tmp_path):
        session = _session(tmp_path)
        (session.root_mount_path / "etc").mkdir()
        hostname = wizard._apply_system_config(session, "pi-tor")
        assert hostname == "pi-tor"
        assert (session.root_mount_path / "etc/hostname").read_text() == "pi-tor\n"
        assert (session.boot_mount_path / "ssh").is_file()

    def test_configure_login_user_renames_default_and_installs_key(self, tmp_path, fake_runner):
        pubkey = tmp_path / "id.pub"
        pubkey.write_text("ssh-ed25519 AAAA user@host\n")
        wizard._configure_login_user(_session(tmp_path), "kevin", "secret", pubkey)
        script = next(text for _, cmd, text in fake_runner.calls if cmd[0] == "chroot" and text)
        assert "for old in pi alarm" in script
        assert 'usermod -l "$target" "$old"' in script
        assert "target=kevin" in script
        assert 'useradd -m -s /bin/bash "$target"' in script
        assert "ssh-ed25519 AAAA" in script
        assert "chpasswd" in script

    def test_configure_login_user_without_password_skips_chpasswd(self, tmp_path, fake_runner):
        pubkey = tmp_path / "id.pub"
        pubkey.write_text("ssh-ed25519 AAAA user@host\n")
        wizard._configure_login_user(_session(tmp_path), "pi", "", pubkey)
        script = next(text for _, cmd, text in fake_runner.calls if cmd[0] == "chroot" and text)
        assert "chpasswd" not in script

    def test_select_target_aborts_on_mismatch(self, answers, monkeypatch):
        monkeypatch.setattr(wizard.device_module, "select_device", lambda: Device("sda"))
        monkeypatch.setattr(wizard.device_module, "is_mounted", lambda _p: False)
        answers("typo")
        with pytest.raises(LimError, match="did not match"):
            wizard._select_target()

    @pytest.mark.parametrize("confirmation", ["sda", "/dev/sda"])
    def test_select_target_accepts_name_or_path(self, confirmation, answers, monkeypatch):
        monkeypatch.setattr(wizard.device_module, "select_device", lambda: Device("sda"))
        monkeypatch.setattr(wizard.device_module, "is_mounted", lambda _p: False)
        answers(confirmation)
        assert wizard._select_target().name == "sda"


class TestCliRegistration:
    def test_guided_command_registered(self):
        command = cli.COMMANDS["guided"]
        assert command.func is wizard.run_guided
        assert command.needs_root is True
