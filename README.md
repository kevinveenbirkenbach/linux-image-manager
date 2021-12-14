# Core System
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](./LICENSE.txt) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/6e66409513d7451b949afbf0373ba71f)](https://www.codacy.com/manual/kevinveenbirkenbach/core-system?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=kevinveenbirkenbach/core-system&amp;utm_campaign=Badge_Grade) [![Travis CI](https://travis-ci.org/kevinveenbirkenbach/core-system.svg?branch=master)](https://travis-ci.org/kevinveenbirkenbach/core-system)

```
The
  _____                _____           _                 
 / ____|              / ____|         | |                
| |     ___  _ __ ___| (___  _   _ ___| |_ ___ _ __ ___  
| |    / _ \| '__/ _ \\___ \| | | / __| __/ _ \ '_ ` _ \
| |___| (_) | | |  __/____) | |_| \__ \ ||  __/ | | | | |
 \_____\___/|_|  \___|_____/ \__, |___/\__\___|_| |_| |_|
                              __/ |                      
                             |___/                       
is an administration tool designed from and for Kevin Veen-Birkenbach.
Licensed under GNU GENERAL PUBLIC LICENSE Version 3
```

## Description
This repository contains scripts to set up an working client system, maintain it and to save all important and configuration data on an USB stick. The data is stored encrypted with [EncFS](https://en.wikipedia.org/wiki/EncFS).
It's adapted to the needs of Kevin Veen-Birkenbach. Feel free to clone it and to adapt it to your needs. The goal is to never setup and configure a system manual again, or to care about loosing passwords and important data. Instead the whole process **SHOULD** be automatized.

## System
### Client
The client script is optimized for a [Manjaro Linux](https://manjaro.org). It's recommended to encrypt the hard drive with [LUKS](https://en.wikipedia.org/wiki/Linux_Unified_Key_Setup) if the computer isn't shared.

#### Folder
The following folder structures will be used:

| Path                        | Description |
|---|---|
$HOME/Documents/certificates/ | Contains certificates to authenticate via [certificate based authentication](https://blog.couchbase.com/x-509-certificate-based-authentication/). |
| $HOME/Documents/recovery_codes/ | Contains files with recovery_codes e.g. for [Two-factor authentication](https://en.wikipedia.org/wiki/Multi-factor_authentication). |
| $HOME/Documents/identity/ | Contains files to prove the identity of the *Core System Owner* in physical live like passports. |
| $HOME/Documents/passwords/ | Contains e.g the [KeePassXC](https://keepassxc.org/) database with all *Core System Owner* passwords. |
| $HOME/Repositories/ | Contains all git repository providers. |
| $HOME/Repositories/{{provider}} | Contains all git repositories of an provider. |
| $HOME/Backups | Contains all backups. The sub-folders follow the standards of [Backup Manager](https://github.com/kevinveenbirkenbach/backup-manager) |
| $HOME/Games/roms | Contains all roms |
| $HOME/Images/ | contains os images|

#### Desktop
The System allows to use a [GNOME desktop](https://www.gnome.org/?) or a [Xfce](https://www.xfce.org/) desktop.
Depending on the desktop environment you have different functionalities.

#### User Data
Right now the software expects that the *Core System Owner* has on all systems the same username. By executing the *import script* it automatic backups the application configuration data, ssh keys and other important data which is saved in well defined configuration files and folders.

### Images

This repository contains some shell scripts to configure and generate images and transfer them to a storage.

#### Setup
To install a Linux distribution execute:

```bash
  sudo bash ./scripts/image/setup.sh
```
#### Chroot
To chroot into a Linux distribution on a storage execute:

```bash
  sudo bash ./scripts/image/chroot.sh
```

#### Backup
To backup a image execute:

```bash
  sudo bash ./scripts/image/backup.sh
```

## Todo

- Implement ssh configuration
- Implement wifi automation
- Install client software depentend on hardware
- Use travis
- Move repository folder

## License
The ["GNU GENERAL PUBLIC LICENSE Version 3"](./LICENSE.txt) applies to this project.
