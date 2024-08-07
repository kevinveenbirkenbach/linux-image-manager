# Linux Image Manager
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) 

This repository contains some shell scripts to download and configure linux images and to transfer them to a storage.

## Virtual Btrfs RAID1 Setup

To setup a virtual btrfs encrypted raid 1 execute: 

```bash
  bash scripts/encryption/storage/raid1/setup.sh
```

## Setup

To install a Linux distribution execute:

```bash
  sudo bash ./scripts/image/setup.sh
```

### Cleanup

To cleanup the image setup execute:
```bash
fuser -k /dev/mapper/linux-image-manager-*; 
umount -f /dev/mapper/linux-image-manager-*; 
fuser -k /tmp/linux-image-manager-*; 
umount -f /tmp/linux-image-manager-*;
```

Additional you can unmount the device with a command like

```bash
umount -f /dev/sd*;
```

### Verification
To verify that the unmounting was successfull, check the result of
```bash
mount
```

## Chroot

To chroot into a Linux distribution on a storage execute:

```bash
  sudo bash ./scripts/image/chroot.sh
```

## Backup

To backup a image execute:

```bash
  sudo bash ./scripts/image/backup.sh
```

## License

The ["GNU GENERAL PUBLIC LICENSE Version 3"](./LICENSE.txt) applies to this project.
