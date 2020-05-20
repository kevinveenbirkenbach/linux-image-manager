#!/bin/bash
# @author Kevin Veen-Birkenbach
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../../base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Searching for files which are in \"$HOME\" and bigger then 100MB..."
find ~ -type f -size +100M -exec ls -lh {} \;
