# Linux Image Manager
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/6e66409513d7451b949afbf0373ba71f)](https://www.codacy.com/manual/kevinveenbirkenbach/core-system?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=kevinveenbirkenbach/core-system&amp;utm_campaign=Badge_Grade) [![Travis CI](https://travis-ci.org/kevinveenbirkenbach/core-system.svg?branch=master)](https://travis-ci.org/kevinveenbirkenbach/core-system)

This repository contains some shell scripts to download and configure linux images and to transfer them to a storage.

## Setup
To install a Linux distribution execute:

```bash
  sudo bash ./scripts/image/setup.sh
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
