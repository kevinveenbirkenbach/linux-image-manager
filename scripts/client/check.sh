#!/bin/bash
# @author Kevin Veen-Birkenbach
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "System check - Shows things which can be optimized:"
echo
info "Linux-Kernel: $(uname -r)"
info "Checking relevant home folders for duplicated files..."
fdupes -r "$HOME/Documents/" "$HOME/Downloads/" "$HOME/Images/" "$HOME/Desktop/" "$HOME/Music/" "$HOME/Pictures/" "$HOME/Videos"
info "Searching for files which are in \"$HOME\" but don't belong to user \"$USER\"..."
sudo find "$HOME" ! -user "$USER"
info "Searching for files which are in \"$HOME\" and bigger then 100MB..."
find ~ -type f -size +100M -exec ls -lh {} \;
info "Showing the installed Java versions..." &&
archlinux-java status
