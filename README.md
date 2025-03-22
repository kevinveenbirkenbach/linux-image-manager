# Linux Image Manager 🖥️🛠️

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach) [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) [![GitHub stars](https://img.shields.io/github/stars/kevinveenbirkenbach/linux-image-manager.svg?style=social)](https://github.com/kevinveenbirkenbach/linux-image-manager/stargazers)

Linux Image Manager (lim) is a powerful collection of shell scripts for downloading, configuring, and managing Linux images. Whether you're setting up encrypted storage, configuring a virtual Btrfs RAID1, performing backups, or chrooting into an image, this tool makes Linux image administration simple and efficient. 🚀

> **Note:** In this project, `lim` is an alias for the **main.py** wrapper script which orchestrates the execution of the various shell scripts.

## Features ✨

- **Image Download & Setup:** Automatically download and prepare Linux distributions.
- **Encrypted Storage:** Configure LUKS encryption for secure image management.
- **Virtual RAID1:** Easily set up virtual Btrfs RAID1 for data redundancy.
- **Backup & Restore:** Create image backups from devices using dd.
- **Chroot Environment:** Easily enter a chroot shell to maintain or modify Linux images.
- **Automated Procedures:** Simplify partitioning, formatting, mounting, and more.

## Installation 📦

Install Linux Image Manager quickly using [Kevin's Package Manager](https://github.com/kevinveenbirkenbach/package-manager) under the alias `lim`. Just run:

```bash
package-manager install lim
```

This command makes Linux Image Manager globally available as `lim` in your terminal. The `lim` alias points to the **main.py** wrapper script.

## Usage ⚙️

The **main.py** wrapper provides a unified interface to run the different shell scripts included in this project. It supports various script types and allows you to pass additional parameters. The built-in `--help` option displays detailed usage information.

### Available Script Types

- **Image Setup (`--type image`):**  
  Executes the Linux image setup located at `scripts/image/setup.sh`. This setup:
  - Creates partitions and formats them.
  - Transfers the Linux image file to the device.
  - Configures boot and root partitions.

- **Single Drive Encryption Setup (`--type single`):**  
  Executes the single-drive encryption setup from `scripts/encryption/storage/single_drive/setup.sh`. This setup:
  - Sets up disk encryption using LUKS on one drive.
  - Configures a Btrfs file system for secure storage.

- **RAID1 Encryption Setup (`--type raid1`):**  
  Executes the RAID1 encryption setup found at `scripts/encryption/storage/raid1/setup.sh`. This setup:
  - Configures a virtual RAID1 with two drives.
  - Uses LUKS encryption and a Btrfs RAID1 file system for redundancy.

- **Backup Image Setup (`--type backup`):**  
  Executes the backup image setup located at `scripts/image/backup.sh`. This setup:
  - Creates an image backup from a memory device to a file.
  - Uses `dd` to transfer the image from the specified device to an image file.

- **Chroot Environment Setup (`--type chroot`):**  
  Executes the chroot setup from `scripts/image/chroot.sh`. This setup:
  - Mounts partitions and configures the chroot environment for a Linux image.
  - Provides a shell within the Linux image for system maintenance.

### Command-Line Options

- **`--type`**  
  **(Required)** Choose the type of script to execute. Options include: `image`, `single`, `raid1`, `backup`, and `chroot`.

- **`--extra`**  
  **(Optional)** Pass any extra parameters directly to the selected shell script.

- **`--auto-confirm`**  
  **(Optional)** Automatically bypass the confirmation prompt before executing the selected script.

- **`--help`**  
  **(Optional)** Displays detailed help information about the command-line options and usage of the wrapper. Simply run:
  ```bash
  lim --help
  ```
  to view the complete help message.

### Example Commands

- **Display Help:**  
  ```bash
  lim --help
  ```

- **Show Information About the Image Setup:**  
  ```bash
  lim --type image --info
  ```

- **Execute the Linux Image Setup (with extra parameters):**  
  ```bash
  lim --type image --extra --some-option value
  ```

- **Run the Single Drive Encryption Setup without a confirmation prompt:**  
  ```bash
  lim --type single --auto-confirm
  ```

- **Execute the RAID1 Encryption Setup:**  
  ```bash
  lim --type raid1
  ```

- **Perform a Backup of an Image:**  
  ```bash
  lim --type backup
  ```

- **Enter a Chroot Environment for a Linux Image:**  
  ```bash
  lim --type chroot
  ```

For additional details on each script and further configuration options, please refer to the `scripts/` and `configuration/` directories.

## Configuration & Customization 🔧

Customize your environment in the `configuration/` folder:
- **General Packages:** Contains common packages for all setup scripts.
- **Server LUKS Packages:** Contains packages needed for setting up LUKS encryption on servers.

## License 📜

This project is licensed under the GNU General Public License Version 3. See the [LICENSE.txt](./LICENSE.txt) file for details.

## Contact & Support 💬

- **Author:** Kevin Veen-Birkenbach  
- **Email:** [kevin@veen.world](mailto:kevin@veen.world)  
- **Website:** [https://www.veen.world/](https://www.veen.world/)

Feel free to contribute, report issues, or get in touch. Happy Linux managing! 😊
```