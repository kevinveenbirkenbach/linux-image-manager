"""Interactive selection of the distribution image to install."""

from lim import catalog, runner, ui
from lim.errors import LimError
from lim.image.plan import ImagePlan


def _choose(prompt: str, options: list[str]) -> str:
    """List options numbered; accept either a number or the name itself."""
    ui.info(f"{prompt}:")
    for index, name in enumerate(options, 1):
        ui.info(f"  {index}) {name}")
    answer = ui.ask("Pick a number or name:").strip()
    if answer in options:  # name wins, so numeric names (e.g. arch "4") still work
        return answer
    if answer.isdigit() and 1 <= int(answer) <= len(options):
        return options[int(answer) - 1]
    return answer


def choose_arch(plan: ImagePlan) -> None:
    version = _choose("Which Raspberry Pi version", list(catalog.arch_rpi_images()))
    entry = catalog.arch_rpi_images().get(version)
    if entry is None:
        raise LimError(f"Version {version} isn't supported.")
    plan.raspberry_pi_version = version
    plan.boot_size = "+500M"
    plan.base_download_url = "http://os.archlinuxarm.org/os/"
    plan.image_name = entry["image"]
    plan.luks_memory_cost = entry["luks_memory_cost"]


def choose_manjaro(plan: ImagePlan) -> None:
    plan.boot_size = "+500M"
    flavour = _choose("Which Manjaro version", ["architect", "gnome"])
    if flavour == "architect":
        plan.image_checksum = "6b1c2fce12f244c1e32212767a9d3af2cf8263b2"
        plan.base_download_url = (
            "https://osdn.net/frs/redir.php?m=dotsrc&f=%2Fstorage%2Fg%2Fm%2Fma"
            "%2Fmanjaro%2Farchitect%2F20.0%2F"
        )
        plan.image_name = "manjaro-architect-20.0-200426-linux56.iso"
    elif flavour == "gnome":
        release = _choose("Which Gnome release", list(catalog.manjaro_gnome_releases()))
        entry = catalog.manjaro_gnome_releases().get(release)
        if entry is None:
            raise LimError(f"Gnome release {release} isn't supported.")
        plan.image_checksum = entry.get("checksum")
        plan.base_download_url = entry["url"]
        plan.image_name = entry["image"]
        plan.luks_memory_cost = entry.get("luks_memory_cost")
        plan.raspberry_pi_version = entry.get("raspberry_pi_version")
    else:
        raise LimError(f"Manjaro version {flavour} isn't supported.")


def choose_moode(plan: ImagePlan) -> None:
    plan.boot_size = "+200M"
    plan.image_checksum = "185cbc9a4994534bb7a4bc2744c78197"
    plan.base_download_url = "https://github.com/moode-player/moode/releases/download/r651prod/"
    plan.image_name = "moode-r651-iso.zip"


def choose_retropie(plan: ImagePlan) -> None:
    plan.boot_size = "+500M"
    version = _choose("Which RetroPie version", list(catalog.retropie_images()))
    entry = catalog.retropie_images().get(version)
    if entry is None:
        raise LimError(f"Version {version} isn't supported.")
    plan.raspberry_pi_version = version
    plan.base_download_url = "https://github.com/RetroPie/RetroPie-Setup/releases/download/4.8/"
    plan.image_checksum = entry["checksum"]
    plan.image_name = entry["image"]


def choose_raspios(plan: ImagePlan) -> None:
    plan.boot_size = "+512M"
    plan.root_filesystem = "ext4"
    variant = _choose("Which Raspberry Pi OS image", list(catalog.raspios_images()))
    entry = catalog.raspios_images().get(variant)
    if entry is None:
        raise LimError(f"Raspberry Pi OS variant {variant} isn't supported.")
    plan.source_url = entry["source_url"]
    plan.image_name = entry["image"]


def choose_torbox(plan: ImagePlan) -> None:
    plan.base_download_url = "https://www.torbox.ch/data/"
    plan.image_name = "torbox-20220102-v050.gz"
    plan.image_checksum = "0E1BA7FFD14AAAE5F0462C8293D95B62C3BF1D9E726E26977BD04772C55680D3"
    plan.boot_size = "+200M"


def choose_android_x86(plan: ImagePlan) -> None:
    plan.base_download_url = (
        "https://www.fosshub.com/Android-x86.html?dwl=android-x86_64-9.0-r2.iso"
    )
    plan.image_name = "android-x86_64-9.0-r2.iso"
    plan.image_checksum = "f7eb8fc56f29ad5432335dc054183acf086c539f3990f0b6e9ff58bd6df4604e"
    plan.boot_size = "+500M"


DISTRIBUTION_CHOOSERS = {
    "android-x86": choose_android_x86,
    "torbox": choose_torbox,
    "arch": choose_arch,
    "manjaro": choose_manjaro,
    "moode": choose_moode,
    "retropie": choose_retropie,
    "raspios": choose_raspios,
}


def choose_linux_image(plan: ImagePlan) -> None:
    distribution = _choose("Which distribution", list(DISTRIBUTION_CHOOSERS))
    chooser = DISTRIBUTION_CHOOSERS.get(distribution)
    if chooser is None:
        raise LimError(f"Distribution {distribution} isn't supported.")
    plan.distribution = distribution
    chooser(plan)


def choose_local_image(plan: ImagePlan) -> None:
    ui.info("Available images:")
    runner.run(["ls", "-l", str(plan.image_folder)], check=False)
    plan.image_name = ui.ask("Which image would you like to use?")
