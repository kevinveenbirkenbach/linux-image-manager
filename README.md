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
## Todo

- Implement ssh configuration
- Implement wifi automation
- Install client software depentend on hardware
- Use travis
- Move repository folder

## Description
This repository contains scripts to set up an working client system, maintain it and to save all important and configuration data on an USB stick. The data is stored encrypted with [EncFS](https://en.wikipedia.org/wiki/EncFS).
It's adapted to the needs of Kevin Veen-Birkenbach. Feel free to clone it and to adapt it to your needs. The goal is to never setup and configure a system manual again, or to care about loosing passwords and important data. Instead the whole process **SHOULD** be automatized.

## Functions

This repository contains the following scripts:

| Order | Description |
|---|---|
| ```bash ./scripts/system-setup.sh``` | Setup the customized software on the system on which you execute it. |
| ```bash ./scripts/image/backup.sh``` | Backup an device image |
| ```bash ./scripts/data/import-data-from-system.sh``` | Import data from the host system.|
| ```bash ./scripts/data/export-data-to-system.sh``` | Export data to the host system.|
| ```bash ./scripts/encryption/data/unlock.sh``` | Unlock the stored data.|
| ```bash ./scripts/encryption/data/lock.sh``` | Lock the stored data |
| ```bash ./scripts/pull-local-repositories.sh``` | Pulls all local repositories branches |
| ```bash ./scripts/pushs-local-repositories.sh``` | Pushs all local repositories branches |
| ```encfsctl passwd .encrypted``` | Change the password of the encrypted folder. |


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
| $HOME/Repositories/ | Contains all git repositories |
| $HOME/Games/roms | Contains all roms |
| $HOME/Images/ | contains os images|

#### Desktop
The System allows to use a [GNOME desktop](https://www.gnome.org/?) or a [Xfce](https://www.xfce.org/) desktop.
Depending on the desktop environment you have different functionalities.

#### User Data
Right now the software expects that the *Core System Owner* has on all systems the same username. By executing the *import script* it automatic backups the application configuration data, ssh keys and other important data which is saved in well defined configuration files and folders.

### Server

#### Raspberry Pi
This repository contains some shell scripts to install Arch Linux for the Raspberry Pi on a SD-Card and to backup a SD-Card.

##### Setup
###### Guided
To install a Linux distribution manually on a SD card type in:

```bash
  bash ./sd_setup.sh
```
###### Piped
To pase the configuration to the program use this syntax:
```bash
(
  echo "$USER"              # | The username
  echo "mmcblk1"                # | The device
  echo "arm"             # | The architecture type; arm or 64_bit
  echo "arch"            # | The operation system
  echo "3"          # | The version
  #echo "n"                 # ├── If arch: Should a encrypted setup be used? (y/n)
  echo "n"                  # | Should the image download be forced?(y/n)
  echo "n"                  # | Should the image be transfered to $device_path?(y/n)
  #echo "n"                 # ├── Overwrite device before copying? (y/n)
  echo "n"                  # | Should the password be changed?(y/N)
  #echo "test12345"         # ├── The user password_1
  #echo "test12345"         # ├── The user password_2
  echo "n"                 # | Should the ssh-key be copied to the image?(y/N)
  echo "n"                  # |Should the hostname be changed?(y/N)
  #echo "example-host"       # | The hostname
  echo "y"                  # Should the image system be updated?(y/N)
  #echo "y"                 # | Setup Wifi on target system - Not implemented yet
)| sudo bash ./scripts/image/setup.sh | tee log.txt
```

## License
The ["GNU GENERAL PUBLIC LICENSE Version 3"](./LICENSE.txt) applies to this project.
