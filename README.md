# Core System
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt)

This repository contains scripts to set up an working client system, maintain it and to save the data on an USB stick.
It's adapted to the needs of Kevin Veen-Birkenbach aka. Frantz.
## Requirements
This script is optimized for a [Manjaro Linux](https://manjaro.org) with [GNOME desktop](https://www.gnome.org/?).
Specific system requirements are described in the [.travis file](./.travis).

## Functions
### System Setup
To setup the customized software on a system you have to execute:
```bash
bash ./scripts/system-setup.sh
```
### Import Data
To import configuration files from the system you have to execute:
```bash
bash ./scripts/import-data-from-system.sh
```
### Export Data
To export configuration files to the system you have to execute:
```bash
bash ./scripts/export-data-to-system.sh
```
### Unlock Data
To decrypt the data you have to execute:
```bash
bash ./scripts/unlock.sh
```
### Lock Data
To encrypt the data you have to execute:
```bash
bash ./scripts/lock.sh
```

### Change Data Password
To change the encryption password you have to type in:
```bash
encfsctl passwd .encrypted
```
## License
The ["GNU GENERAL PUBLIC LICENSE Version 3"](./LICENSE.txt) applies to this project.
