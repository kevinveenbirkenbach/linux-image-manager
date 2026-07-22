# Virtualized end-to-end Tor unlock harness

This harness models the **entire** encrypted-image process in a virtual
machine: it builds a LUKS image carrying the real `lim` Tor-in-initramfs
artifacts, boots it in QEMU, lets the real `netconf → tor → dropbear →
encryptssh` chain run in early userspace, then unlocks the root over Tor and
proves the real system booted.

It complements the lightweight, always-rootless
[`test_tor_unlock_e2e.py`](../test_tor_unlock_e2e.py): that one round-trips a
passphrase through Tor against a dropbear *stand-in*; this one runs the real
dropbear, real cryptsetup, real mkinitcpio initramfs, and a real tor daemon in
a booted machine.

## Why a virtio machine and not an emulated Raspberry Pi

QEMU's `raspi3b`/`raspi4b` machines do not emulate the Pi's USB-gadget
Ethernet — exactly the network path the Pi images use in the initramfs
(`g_ether`/`smsc95xx`/`lan78xx`). Without early networking there is no Tor and
no unlock, so emulating the literal board is pointless here. Instead we
reproduce the same *software stack* (same HOOKS chain, same tor hook, same
torrc and onion keys) on a QEMU-friendly `virt`/`q35` machine with
`virtio-net`. The only deltas from a real Pi image are the NIC driver and the
CPU architecture.

## Stages

| Stage | File | Privilege |
|---|---|---|
| Build encrypted image (Arch) | `build_image.sh` | **root** (loop, cryptsetup, chroot) |
| Build encrypted image (Debian) | `build_image_debian.sh` | **root** (debootstrap, loop, cryptsetup, chroot) |
| Tor network | `tor_net.py` | rootless |
| Boot + unlock | `boot_unlock.py` | rootless (QEMU user-mode net) |
| Orchestration | `harness.py` | mixed (uses `sudo` for the build only) |
| Pure command builders | `config.py` | none — unit-tested offline |

## Keeping the host rootless

Only `build_image.sh` needs root (there is no rootless dm-crypt). To keep your
host unprivileged, run the whole harness **inside a throwaway VM** that has
`/dev/kvm`, and drive it from there. QEMU itself, the tor client and the unlock
are rootless: user-mode networking (`-netdev user`) needs no tap device, and a
Tor onion service needs no inbound port forward (its rendezvous is outbound
from both ends).

When run directly on the host, `harness.py` invokes the build via `sudo -E`
and then `chown`s the artifacts back so rootless QEMU can read them.

## Requirements

- `qemu-system-x86_64` (or `-aarch64` for `LIM_E2E_ARCH=aarch64`)
- `arch-install-scripts` (`pacstrap`, `arch-chroot`)
- `cryptsetup`, `mkinitcpio`, `tor`, `openssh`, `ncat` (SOCKS5 ProxyCommand)
- Network access to the public Tor network, **or** `chutney` for a private one
- `/dev/kvm` recommended (TCG works but is slow; aarch64-on-x86 is always TCG)

For the Debian build (`LIM_E2E_OS=debian`), additionally: `debootstrap` and
network access to a Debian mirror. The guest uses the initramfs-tools backend
(cryptsetup-initramfs + dropbear-initramfs), so the unlock SSH session runs
`cryptroot-unlock` instead of Arch's login-time encryptssh prompt.

## Unlock transport: direct vs Tor

`LIM_E2E_TRANSPORT` (default `direct`) selects how the passphrase reaches the
guest's dropbear:

- **direct** — QEMU forwards a host port to the guest's dropbear (`:22`) and the
  passphrase is delivered over a plain SSH. Deterministic; it verifies the whole
  LUKS-unlock stack (cryptsetup-initramfs + dropbear-initramfs + cryptroot-unlock
  + LUKS + boot). This is what CI/`make` runs.
- **tor** — the full onion path: the guest publishes its onion and the host
  reaches it through Tor. Representative of production but **flaky over public
  Tor inside QEMU** (fresh guest Tor + user-mode net make the onion rendezvous
  unreliable), so it is opt-in. The onion transport itself is covered
  deterministically by the rootless `test_tor_unlock_e2e.py`.

## Running

```bash
# Arch (mkinitcpio), direct transport (deterministic, default):
LIM_E2E_QEMU=1 pytest tests/e2e/test_qemu_unlock_e2e.py -v -s

# Debian (initramfs-tools) via debootstrap, direct transport:
LIM_E2E_QEMU=1 LIM_E2E_OS=debian pytest tests/e2e/test_qemu_unlock_e2e.py -v -s

# Full onion transport (opt-in, flaky over public Tor):
LIM_E2E_QEMU=1 LIM_E2E_TRANSPORT=tor pytest tests/e2e/test_qemu_unlock_e2e.py -v -s
```

`make test-qemu` / `make test-qemu-debian` wrap the direct-transport runs.

Environment knobs: `LIM_E2E_ARCH` (`x86_64` default, or `aarch64`),
`CHUTNEY_PATH` (enables the private network), `CHUTNEY_PATH` unset → public.

## Determinism note (chutney)

For a fully private loop the **guest image** must trust the same authorities as
the host client. `ChutneyNetwork.test_network_conf()` distils the
`TestingTorNetwork`/`DirAuthority` lines (rewriting `127.0.0.1` to the QEMU
user-net host alias `10.0.2.2`) into a file, which `build_image.sh` appends to
the baked-in torrc via `TOR_TEST_NETWORK_CONF`. The offline onion key
generation is unaffected — it never touches the network either way.

## What runs in CI without any of this

The pure logic (`config.py`, the env parser, the chutney torrc parsing) and the
drift guards that keep `build_image.sh` aligned with what the harness expects
are covered by [`test_qemu_harness_unit.py`](../test_qemu_harness_unit.py),
which runs in the normal `pytest` suite — no QEMU, root, or network.
