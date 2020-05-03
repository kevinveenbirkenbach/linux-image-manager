#!/bin/bash
#
# Locks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
#
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Locking directory $DECRYPTED_PATH..." &&
fusermount -u "$DECRYPTED_PATH" || error "Unmounting failed."
info "Data is now encrypted."

info "Removing directory $DECRYPTED_PATH..." &&
rmdir "$DECRYPTED_PATH" || error "Failed."
