# Changelog

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

