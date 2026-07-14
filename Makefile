.PHONY: install test

PREFIX ?= $(HOME)/.local

install:
	chmod +x main.py
	install -d $(PREFIX)/bin
	ln -sf $(CURDIR)/main.py $(PREFIX)/bin/lim
	@echo "Installed lim to $(PREFIX)/bin/lim"

test:
	python3 -m pytest
