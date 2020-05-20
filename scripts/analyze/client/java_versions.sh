#!/bin/bash
# @author Kevin Veen-Birkenbach
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../../base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Showing the installed Java versions..." &&
archlinux-java status
