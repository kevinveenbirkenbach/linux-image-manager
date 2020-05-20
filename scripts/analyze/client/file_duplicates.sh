#!/bin/bash
# @author Kevin Veen-Birkenbach
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../../base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Checking relevant home folders for duplicated files..."
fdupes -r "$HOME/Documents/" "$HOME/Downloads/" "$HOME/Images/" "$HOME/Desktop/" "$HOME/Music/" "$HOME/Pictures/" "$HOME/Videos"
