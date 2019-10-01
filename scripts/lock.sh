#!/bin/bash
#
# Locks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
#
# Deactivate SC1090
# shellcheck source=/dev/null
source "$(dirname "$(readlink -f "${0}")")/base.sh"
echo "Locking directory $DECRYPTED..."
fusermount -u "$DECRYPTED" && echo "Data is now encrypted." && echo "Removing directory $DECRYPTED..." && rmdir "$DECRYPTED"
