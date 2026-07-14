from lim import catalog


def test_catalog_contains_all_sections():
    assert catalog.arch_rpi_images()
    assert catalog.manjaro_gnome_releases()
    assert catalog.retropie_images()
    assert catalog.mkinitcpio_modules_by_rpi()


def test_arch_entries_are_complete():
    for version, entry in catalog.arch_rpi_images().items():
        assert entry["image"], version
        assert entry["luks_memory_cost"].isdigit(), version


def test_mkinitcpio_covers_every_arch_rpi_version():
    assert set(catalog.mkinitcpio_modules_by_rpi()) == set(catalog.arch_rpi_images())


def test_manjaro_entries_have_url_and_image():
    for release, entry in catalog.manjaro_gnome_releases().items():
        assert entry["url"].startswith("https://"), release
        assert entry["image"], release
