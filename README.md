# Linux Image Manager🖥️🛠️

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) [![GitHub stars](https://img.shields.io/github/stars/kevinveenbirkenbach/linux-image-manager.svg?style=social)](https://github.com/kevinveenbirkenbach/linux-image-manager/stargazers)

Linux Image Manager(lim) is a powerful collection of shell scripts for downloading, configuring, and managing Linux images. Whether you're setting up encrypted storage, configuring a virtual Btrfs RAID1, performing backups, or chrooting into an image, this tool makes Linux image administration simple and efficient. 🚀

## Features ✨

- **Image Download & Setup:** Automatically download and prepare Linux distributions.
- **Encrypted Storage:** Configure LUKS encryption for secure image management.
- **Virtual RAID1:** Easily set up virtual Btrfs RAID1 for data redundancy.
- **Chroot Environment:** Seamlessly chroot into your Linux image for system maintenance.
- **Backup & Restore:** Comprehensive backup and restore options for system images.
- **Automated Procedures:** Simplify partitioning, formatting, mounting, and more.

## Installation 📦

Install Linux Image Manager quickly with [Kevin's Package Manager](https://github.com/kevinveenbirkenbach/package-manager) under the alias `lim`. Just run:

```bash
package-manager install lim
```

This command makes Linux Image Manager globally available as `lim` in your terminal. 🔧

## Usage ⚙️

Linux Image Manager comes with a variety of scripts tailored for different tasks. Here are a few examples:

### Virtual Btrfs RAID1 Setup
```bash
lim raid1/setup.sh
```

### Linux Image Setup
```bash
lim image/setup.sh
```

### Chroot into Linux Image
```bash
lim image/chroot.sh
```

### Backup Image
```bash
lim image/backup.sh
```

Explore the `scripts/` directory for more functionalities and detailed usage instructions.

## Configuration & Customization 🔧

Customize your environment in the `configuration/` folder:
- **General Packages:** Common packages for all setup scripts.
- **Server LUKS Packages:** Packages needed for setting up LUKS encryption on servers.

## License 📜

This project is licensed under the GNU General Public License Version 3. See the [LICENSE.txt](./LICENSE.txt) file for details.

## Contact & Support 💬

- **Author:** Kevin Veen-Birkenbach  
- **Email:** [kevin@veen.world](mailto:kevin@veen.world)  
- **Website:** [https://www.veen.world/](https://www.veen.world/)

Feel free to contribute, report issues, or get in touch. Happy Linux managing! 😊
