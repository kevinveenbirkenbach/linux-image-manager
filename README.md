# Linux Image Manager 🖥️🛠️

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach) [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) [![GitHub stars](https://img.shields.io/github/stars/kevinveenbirkenbach/linux-image-manager.svg?style=social)](https://github.com/kevinveenbirkenbach/linux-image-manager/stargazers)

Linux Image Manager (lim) is a Python tool for downloading, configuring, and managing Linux images. Whether you're setting up encrypted storage, configuring a virtual Btrfs RAID1, performing backups, or chrooting into an image, this tool makes Linux image administration simple and efficient. 🚀

## Features ✨

- **Image Download & Setup:** Automatically download, verify (checksum + GPG signature) and prepare Linux distributions.
- **Encrypted Storage:** Configure LUKS encryption for secure image management.
- **Virtual RAID1:** Easily set up virtual Btrfs RAID1 for data redundancy.
- **Backup & Restore:** Create image backups from devices using dd.
- **Chroot Environment:** Easily enter a chroot shell to maintain or modify Linux images.
- **Data Import/Export:** Sync personal data into an encfs-encrypted store and back.
- **Automated Procedures:** Simplify partitioning, formatting, mounting, and more.

## Installation 📦

Install Linux Image Manager quickly using [Kevin's Package Manager](https://github.com/kevinveenbirkenbach/package-manager) under the alias `lim`. Just run:

```bash
package-manager install lim
```

This command makes Linux Image Manager globally available as `lim` in your terminal. The `lim` alias points to the **main.py** entry point.

There are no Python dependencies beyond the standard library. The commands call the usual system tools (`cryptsetup`, `fdisk`, `dd`, `rsync`, `wget`, `gpg`, `encfs`, `pv`, `bsdtar`, ...), so those need to be installed for the command you use.

## Usage ⚙️

`lim` provides a unified interface for all image and storage operations. Commands that need root privileges re-execute themselves with `sudo` automatically. The built-in `--help` option displays detailed usage information.

### Available Command Types

| `--type`      | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `image`       | Download, verify and transfer a Linux image to a device, incl. optional LUKS encryption and Raspberry Pi configuration. |
| `single`      | Set up LUKS encryption with Btrfs on a single drive.                        |
| `raid1`       | Set up an encrypted virtual Btrfs RAID1 across two drives.                  |
| `backup`      | Create an image backup from a memory device using dd.                      |
| `chroot`      | Mount an image and open a shell inside it.                                  |
| `mount`       | Unlock and mount an encrypted drive.                                        |
| `umount`      | Unmount an encrypted drive and close the mapper.                            |
| `single-boot` | Register a single encrypted drive for automount on boot (keyfile, crypttab, fstab). |
| `raid1-boot`  | Register an encrypted RAID1 for automount on boot.                          |
| `unlock`      | Decrypt the encfs data store.                                               |
| `lock`        | Lock the encfs data store.                                                  |
| `import`      | Import personal data from the system into the encrypted store.              |
| `export`      | Export personal data from the encrypted store back to the system.           |

### Command-Line Options

- **`--type`** *(required)*: Choose the command to execute (see table above).
- **`--auto-confirm`** *(optional)*: Bypass the confirmation prompt before execution.
- **`--help`** *(optional)*: Display detailed help information.

### Example Commands

```bash
# Display help
lim --help

# Execute the Linux image setup
lim --type image

# Run the single drive encryption setup without a confirmation prompt
lim --type single --auto-confirm

# Set up an encrypted RAID1
lim --type raid1

# Back up a memory device to an image file
lim --type backup

# Enter a chroot environment for a Linux image
lim --type chroot
```

## Project Structure 🗂️

```
main.py               # entry point (the `lim` alias)
distributions.yml     # single point of truth for the image catalog
lim/
  cli.py              # argument parsing and command dispatch
  catalog.py          # read-only access to distributions.yml
  device.py           # block device selection, dd, blkid helpers
  luks.py             # LUKS keyfiles, crypttab/fstab bookkeeping
  runner.py           # subprocess wrapper used by all modules
  storage/            # single drive and RAID1 encryption setups
  image/              # image setup, backup, chroot, verification
  data/               # encfs lock/unlock and data import/export
configuration/        # package collections used during image setup
tests/unit/           # unit tests (all external commands mocked)
tests/lint/           # architecture guards (e.g. max file length)
```

## Configuration & Customization 🔧

Customize your environment in the `configuration/` folder:
- **General Packages:** Contains common packages for all setup scripts.
- **Server LUKS Packages:** Contains packages needed for setting up LUKS encryption on servers.

## Development & Tests 🧪

The test suite mocks all external commands, so it runs safely on any machine:

```bash
pytest
```

## License 📜

This project is licensed under the GNU General Public License Version 3. See the [LICENSE.txt](./LICENSE.txt) file for details.

## Contact & Support 💬

- **Author:** Kevin Veen-Birkenbach
- **Email:** [kevin@veen.world](mailto:kevin@veen.world)
- **Website:** [https://www.veen.world/](https://www.veen.world/)

Feel free to contribute, report issues, or get in touch. Happy Linux managing! 😊
