# Changelog

## [2.3.0] - 2026-07-24

**✨ New**

- Guided setup wizard, now the default command: *lim* with no *--type* (or
  *lim --type guided*) asks everything up front — distribution, target device,
  hostname, login user + SSH key, password — then builds an encrypted,
  Tor-remote-unlockable image unattended.
- Debian / Raspberry Pi OS remote LUKS unlock. The initramfs unlock stack is
  now distro-agnostic behind an *InitramfsBackend* abstraction: *mkinitcpio*
  for Arch/Manjaro, *initramfs-tools* (cryptsetup-initramfs + dropbear-initramfs
  + a Tor onion) for Raspberry Pi OS / moode / RetroPie.
- Flash full disk images into LUKS. Distributions that ship a *.img* rather
  than a rootfs tarball (Raspberry Pi OS, moode, RetroPie, Manjaro ARM) are
  loop-mounted and their boot + root partitions copied into a fresh LUKS
  container. New Raspberry Pi OS catalog (*lite64* / *desktop64* / *lite32*).
- New *remote-unlock* command: reach a waiting initramfs over Tor (onion, via
  *torsocks*) or plain SSH (host/IP), running *cryptroot-unlock* or presenting
  the passphrase prompt. The wizard saves a target record under
  *~/.config/lim/unlocks* so *lim --type remote-unlock* offers it directly.
- Cross-architecture builds. Building a foreign-arch image (e.g. arm64
  Raspberry Pi OS on an x86 host) auto-installs *qemu-user-static* and registers
  binfmt, or aborts before the target is erased with per-distro instructions.
- RTC-less clock hardening. A clock floor (build epoch baked into the initramfs)
  plus a numeric *tor_ntp=* cmdline let the clock sync without DNS, so the Tor
  onion still publishes on boards without a real-time clock (which boot at 1970).
- Numbered selection menus for distribution and version prompts; typing the
  name still works.
- CI: a full Debian *build → boot → LUKS-unlock* QEMU end-to-end job runs on
  push (*make test-qemu-debian*).

**🐛 Fixes**

- Raspberry Pi OS Bookworm boots the encrypted image: the initramfs is placed on
  the *​/boot/firmware* FAT partition instead of the ext4 root, so cryptsetup is
  present at boot (no more *(initramfs)* emergency shell).
- Chroot package installs are robust cross-host: a Debian-safe *PATH* (so
  *update-initramfs* / *useradd* resolve) and *apt-get update* before install
  (stock images ship stale lists whose superseded *.deb* URLs 404).
- Stock-image *fstab* is normalized (the existing *​/* line is replaced, not
  duplicated) when copying a distro image into LUKS.
- Large copies show progress (*rsync --info=progress2*, *cp* fallback).

**💥 Breaking / behavior**

- *lim* with no *--type* now runs the guided wizard (previously *--type* was
  required).
- The long-deprecated *--extra* argument is removed.

## [2.2.0] - 2026-07-21

- Optional remote LUKS unlock via a Tor onion service in the initramfs.
  Encrypted image setups can bake *tor* into the initramfs (mkinitcpio hooks
  ordered *netconf tor dropbear encryptssh*), generate the v3 onion keys
  offline in the image chroot, and print the stable *.onion* address. Unlock
  with *torsocks ssh root@<onion-address>*. Useful behind NAT/CGNAT or a
  dynamic IP, where the direct *ssh root@<ip>* unlock cannot reach the host.
- End-to-end tests: a rootless one (*LIM_E2E_TOR=1*) that round-trips a
  passphrase through a real Tor onion service, and a full virtualized one
  (*LIM_E2E_QEMU=1*) that builds a LUKS image, boots it in QEMU, and unlocks
  the root over Tor. The offline onion keygen runs in CI; *make test-tor* /
  *make test-qemu* / *make test-all* run the opt-in stages.

## [2.1.0] - 2026-07-14

Initial PyPI release 🥳

## [2.0.0] - 2026-07-14

All bash scripts were ported to the *lim/* Python package with a unified CLI, a mocked test suite, and CI.

**💥 Breaking changes**

- *scripts/*.sh* removed. Use *lim --type <command>* instead.
- *--extra* is deprecated and ignored.
- Root commands re-execute themselves with sudo automatically.

**✨ New**

- New command types besides *image*, *single*, *raid1*, *backup* and
  *chroot*: *mount*, *umount*, *single-boot*, *raid1-boot*, *lock*,
  *unlock*, *import*, *export*.
- *distributions.yml* as single point of truth for the image catalog.
- 102 pytest tests with mocked system commands plus a max-250-lines
  architecture guard. Run with *make test*.
- Strict ruff linting, GitHub Actions CI, Dependabot, *Makefile* with
  *install* and *test* targets.

**🐛 Fixes over the bash version**

- Correct partition paths for *mmcblk* and *nvme* devices.
- *chown* targets the invoking user instead of root.
- sha512 checksums are verified; every pipeline stage is checked.
- fstab UUID seeding skips PARTUUID and LABEL based images.
- Pre-mounted images no longer get empty UUIDs in fstab and crypttab.
- Missing system tools abort with a clear message, not a traceback.

**📦 Dependencies**

- Python 3.10 or newer, PyYAML 6 or newer.
- System tools per command: *cryptsetup*, *fdisk*, *rsync*, *wget*,
  *gpg*, *encfs*, *pv*, *bsdtar*.

## [1.0.0] - 2026-07-14

Official Release 🥳

