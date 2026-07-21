# Linux Image Manager 🖥️🛠️

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach) [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) [![GitHub stars](https://img.shields.io/github/stars/kevinveenbirkenbach/linux-image-manager.svg?style=social)](https://github.com/kevinveenbirkenbach/linux-image-manager/stargazers)

Linux Image Manager (lim) is a Python tool for downloading, configuring, and managing Linux images. Whether you're setting up encrypted storage, configuring a virtual Btrfs RAID1, performing backups, or chrooting into an image, this tool makes Linux image administration simple and efficient. 🚀

## Features ✨

- **Image Download & Setup:** Automatically download, verify (checksum + GPG signature) and prepare Linux distributions.
- **Encrypted Storage:** Configure LUKS encryption for secure image management.
- **Tor Onion Unlock:** Optionally bake a Tor onion service into the initramfs so the dropbear LUKS unlock shell stays reachable behind NAT or dynamic IPs.
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

The only Python dependency is **PyYAML** (`>=6`), used to read the image catalog. The pip/wheel install pulls it in automatically; on the `package-manager`/symlink install path make sure it is present (`python-yaml` on Arch). The commands also call the usual system tools (`cryptsetup`, `fdisk`, `dd`, `rsync`, `wget`, `gpg`, `encfs`, `pv`, `bsdtar`, ...), so those need to be installed for the command you use.

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
lim/
  cli.py              # argument parsing and command dispatch
  catalog.py          # read-only access to distributions.yml
  device.py           # block device selection, dd, blkid helpers
  luks.py             # LUKS keyfiles, crypttab/fstab bookkeeping
  runner.py           # subprocess wrapper used by all modules
  storage/            # single drive and RAID1 encryption setups
  image/              # image setup, backup, chroot, verification
  data/               # encfs lock/unlock and data import/export
  distributions.yml   # single point of truth for the image catalog
  configuration/      # package collections used during image setup
tests/unit/           # unit tests (all external commands mocked)
tests/e2e/            # Tor onion unlock end-to-end tests (rootless + QEMU, opt-in)
tests/e2e/qemu/       # full virtualized build+boot+unlock harness
tests/lint/           # architecture guards (e.g. max file length)
```

## Configuration & Customization 🔧

Customize your environment in the `lim/configuration/` folder:
- **General Packages:** Contains common packages for all setup scripts.
- **Server LUKS Packages:** Contains packages needed for setting up LUKS encryption on servers.
- **initcpio Hooks:** The mkinitcpio install/runtime hooks and torrc baked into images for the Tor onion unlock.

## Remote LUKS Unlock via Tor 🧅

When you answer yes to *"Should the system be remotely unlockable via a Tor
onion service?"* during an encrypted `lim --type image` setup, the image gets:

- `tor` and `busybox` installed, plus a custom `tor` mkinitcpio hook ordered
  between `netconf` and `dropbear`.
- A v3 onion service key generated **offline** inside the image chroot; the
  resulting `.onion` address is printed at the end of the setup and stays
  stable across reboots and IP changes.
- An NTP clock sync in early userspace (boards like the Raspberry Pi have no
  RTC and would otherwise boot with a clock Tor rejects). Override the server
  with the kernel parameter `tor_ntp=<host>`.

After booting the device, unlock it from any machine with a running Tor
client:

```bash
torsocks ssh root@<onion-address>
```

Typing the LUKS passphrase into that shell resumes the boot. The direct
`ssh root@<ip>` unlock keeps working as before; Tor is an additional path,
useful behind NAT/CGNAT where no port forwarding is possible.

**Security note:** the onion private key is stored in the initramfs on the
unencrypted boot partition. Anyone with physical access to the SD card can
read it and impersonate the onion service — treat the address as
non-secret. Access control remains the SSH public key
(`/etc/dropbear/root_key`), exactly as with the direct unlock.

## Development & Tests 🧪

The unit suite mocks all external commands, so it runs safely on any machine:

```bash
pytest
```

### Tor unlock end-to-end test

`tests/e2e/test_tor_unlock_e2e.py` reproduces the operator-visible half of the
Tor decryption process **rootless** — no block devices, no `cryptsetup`, no
`chroot`. It generates the v3 onion keys offline (exactly as `lim.image.tor`
does inside the image), starts a real Tor onion service from a torrc mirroring
the baked-in one, then connects to the `.onion` address through Tor and
delivers a passphrase to a dropbear stand-in, asserting it arrives and the
endpoint "unlocks".

It needs the real `tor` binary and live Tor network access (onion bootstrap is
slow), so it is opt-in and skipped otherwise:

```bash
LIM_E2E_TOR=1 pytest tests/e2e/test_tor_unlock_e2e.py -v
```

The offline-only checks in that file (onion keygen, production-flag guard) run
without network. The physical flashing half (`dd`, `cryptsetup luksFormat`,
`mount`, `chroot`, `mkinitcpio`) requires root and a matching CPU/qemu setup and
is not covered by this rootless test.

### Full virtualized unlock (QEMU)

For the *whole* process — build an encrypted image, boot it, run the real
initramfs Tor+dropbear chain, and unlock it — `tests/e2e/qemu/` drives a QEMU
virtual machine end to end and asserts the real system booted only after the
passphrase was delivered over Tor. It is opt-in (`LIM_E2E_QEMU=1`) and needs
QEMU, `arch-install-scripts`, `cryptsetup`, `tor` and `ncat`; the build stage
needs root (ideally inside a throwaway VM to keep the host rootless). A private,
offline Tor network via [chutney](https://gitlab.torproject.org/tpo/core/chutney)
is supported. See [tests/e2e/qemu/README.md](tests/e2e/qemu/README.md).

The harness's pure logic and drift guards run in the normal suite
(`test_qemu_harness_unit.py`) — no QEMU, root, or network needed.

## License 📜

This project is licensed under the GNU General Public License Version 3. See the [LICENSE.txt](./LICENSE.txt) file for details.

## Contact & Support 💬

- **Author:** Kevin Veen-Birkenbach
- **Email:** [kevin@veen.world](mailto:kevin@veen.world)
- **Website:** [https://www.veen.world/](https://www.veen.world/)

Feel free to contribute, report issues, or get in touch. Happy Linux managing! 😊
