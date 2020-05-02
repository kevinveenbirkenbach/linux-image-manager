#!/bin/bash
#
# Locks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
#
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Locking directory $DECRYPTED_PATH..."
fusermount -u "$DECRYPTED_PATH" && echo "Data is now encrypted." && echo "Removing directory $DECRYPTED_PATH..." && rmdir "$DECRYPTED_PATH"
