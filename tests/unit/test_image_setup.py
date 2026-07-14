import pytest

from lim.errors import LimError
from lim.image import choosers, raspberry, transfer
from lim.image.plan import ImagePlan
from lim.image.session import install_packages


@pytest.fixture
def plan():
    return ImagePlan()


class TestDistributionChoosers:
    def test_arch_rpi4_uses_aarch64_and_high_memory_cost(self, plan, answers):
        answers("4")
        choosers.choose_arch(plan)
        assert plan.image_name == "ArchLinuxARM-rpi-aarch64-latest.tar.gz"
        assert plan.luks_memory_cost == "256000"
        assert plan.raspberry_pi_version == "4"
        assert plan.download_url == (
            "http://os.archlinuxarm.org/os/ArchLinuxARM-rpi-aarch64-latest.tar.gz"
        )

    def test_arch_rpi1_uses_armv7_and_low_memory_cost(self, plan, answers):
        answers("1")
        choosers.choose_arch(plan)
        assert plan.image_name == "ArchLinuxARM-rpi-armv7-latest.tar.gz"
        assert plan.luks_memory_cost == "64000"

    def test_arch_unknown_version_raises(self, plan, answers):
        answers("99")
        with pytest.raises(LimError):
            choosers.choose_arch(plan)

    def test_manjaro_gnome_25(self, plan, answers):
        answers("gnome", "25")
        choosers.choose_manjaro(plan)
        assert plan.image_name == "manjaro-gnome-25.0.10-251013-linux612.iso"
        assert plan.base_download_url == "https://download.manjaro.org/gnome/25.0.10/"
        assert plan.image_checksum is None

    def test_manjaro_raspberrypi_release_sets_rpi_version(self, plan, answers):
        answers("gnome", "raspberrypi")
        choosers.choose_manjaro(plan)
        assert plan.raspberry_pi_version == "4"
        assert plan.luks_memory_cost == "256000"
        assert plan.image_name == "Manjaro-ARM-gnome-rpi4-23.02.img.xz"

    def test_manjaro_unknown_flavour_raises(self, plan, answers):
        answers("kde")
        with pytest.raises(LimError):
            choosers.choose_manjaro(plan)

    def test_retropie_rpi3_shares_rpi2_image(self, plan, answers):
        answers("3")
        choosers.choose_retropie(plan)
        assert plan.image_name == "retropie-buster-4.8-rpi2_3_zero2w.img.gz"
        assert plan.image_checksum == "224e64d8820fc64046ba3850f481c87e"

    def test_unknown_distribution_raises(self, plan, answers):
        answers("gentoo")
        with pytest.raises(LimError):
            choosers.choose_linux_image(plan)


class TestPartitionInput:
    def test_contains_boot_size_and_writes_table(self):
        script = transfer.arch_partition_input("+500M")
        assert script.startswith("o\n")
        assert "\n+500M\n" in script
        assert script.endswith("w\n")


class TestDecompressCommand:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("image.zip", ["unzip", "-p"]),
            ("image.img.gz", ["gunzip", "-c"]),
            ("image.iso", ["pv"]),
            ("image.img.xz", ["unxz", "-c"]),
        ],
    )
    def test_known_formats(self, tmp_path, name, expected):
        path = tmp_path / name
        command = transfer.decompress_command(path)
        assert command[: len(expected)] == expected
        assert command[-1] == str(path)

    def test_unknown_format_raises(self, tmp_path):
        with pytest.raises(LimError):
            transfer.decompress_command(tmp_path / "image.rar")


class TestInstallPackages:
    def test_pacman_for_arch(self, tmp_path, fake_runner):
        install_packages("arch", tmp_path, "btrfs-progs")
        chroot_calls = [
            input_text
            for kind, cmd, input_text in fake_runner.calls
            if kind == "run" and cmd[0] == "chroot"
        ]
        assert chroot_calls == ["pacman --noconfirm -S --needed btrfs-progs"]

    def test_apt_for_retropie(self, tmp_path, fake_runner):
        install_packages("retropie", tmp_path, "btrfs-progs")
        chroot_calls = [
            input_text
            for kind, cmd, input_text in fake_runner.calls
            if kind == "run" and cmd[0] == "chroot"
        ]
        assert chroot_calls == ["yes | apt install btrfs-progs"]

    def test_unsupported_distribution_raises(self, tmp_path, fake_runner):
        with pytest.raises(LimError):
            install_packages("gentoo", tmp_path, "btrfs-progs")


class TestConfigureHelpers:
    def test_configure_sudoers(self, tmp_path):
        raspberry.configure_sudoers(tmp_path, "administrator")
        sudoers = tmp_path / "etc/sudoers.d/administrator"
        assert sudoers.read_text() == "administrator ALL=(ALL:ALL) ALL\n"
        assert (sudoers.stat().st_mode & 0o777) == 0o440

    def test_configure_ssh_key(self, tmp_path):
        public_key = tmp_path / "id_rsa.pub"
        public_key.write_text("ssh-rsa AAAA test@host\n")
        ssh_folder = tmp_path / "root/home/user/.ssh"
        authorized_keys = ssh_folder / "authorized_keys"
        raspberry.configure_ssh_key(str(public_key), ssh_folder, authorized_keys)
        assert authorized_keys.read_text() == "ssh-rsa AAAA test@host\n"
        assert (ssh_folder.stat().st_mode & 0o777) == 0o700
        assert (authorized_keys.stat().st_mode & 0o777) == 0o600

    def test_configure_ssh_key_missing_source_raises(self, tmp_path):
        with pytest.raises(LimError):
            raspberry.configure_ssh_key(
                str(tmp_path / "missing.pub"),
                tmp_path / ".ssh",
                tmp_path / ".ssh/authorized_keys",
            )
