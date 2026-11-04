.PHONY: install test test-tor test-qemu test-qemu-debian test-docker test-all

PREFIX ?= $(HOME)/.local
# Interpreter used for the tests. Override if your active venv lacks pytest,
# e.g.  make test PYTHON=/usr/bin/python3
PYTHON ?= python3

install:
	chmod +x main.py
	install -d $(PREFIX)/bin
	ln -sf $(CURDIR)/main.py $(PREFIX)/bin/lim
	@echo "Installed lim to $(PREFIX)/bin/lim"

# Default suite: fully mocked, no root/QEMU/network. The opt-in e2e tests skip.
test:
	$(PYTHON) -m pytest

# Rootless Tor onion unlock e2e (needs the `tor` binary and network access).
test-tor:
	LIM_E2E_TOR=1 $(PYTHON) -m pytest tests/e2e/test_tor_unlock_e2e.py -v

# Full virtualized build+boot+unlock e2e. Needs qemu, arch-install-scripts,
# cryptsetup and ssh; the build stage runs under sudo. The default "direct"
# transport delivers the passphrase deterministically via a QEMU port-forward;
# set LIM_E2E_TRANSPORT=tor for the full onion path (also needs tor + ncat, and
# is flaky over public Tor inside QEMU).
test-qemu:
	LIM_E2E_QEMU=1 $(PYTHON) -m pytest tests/e2e/test_qemu_unlock_e2e.py -v -s

# Same, but builds a Debian image with debootstrap (initramfs-tools backend)
# instead of Arch. Needs debootstrap + cryptsetup + ssh; runs under sudo.
test-qemu-debian:
	LIM_E2E_QEMU=1 LIM_E2E_OS=debian $(PYTHON) -m pytest tests/e2e/test_qemu_unlock_e2e.py -v -s

test-docker:
	LIM_E2E_DOCKER=1 $(PYTHON) -m pytest tests/e2e/test_distro_hostkeys_e2e.py -v

# Everything: mocked suite plus both opt-in e2e stages, in one run.
test-all:
	LIM_E2E_TOR=1 LIM_E2E_QEMU=1 LIM_E2E_DOCKER=1 $(PYTHON) -m pytest -v -s
