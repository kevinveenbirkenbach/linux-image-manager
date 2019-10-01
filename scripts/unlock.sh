#!/bin/bash
#
# Unlocks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
#
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/base.sh"
echo "Unlocking directory $DECRYPTED_PATH..."
echo "Creating directory $DECRYPTED_PATH..."
mkdir "$DECRYPTED_PATH"
echo "Encrypting directory $DECRYPTED_PATH to $DECRYPTED_PATH..."
encfs "$ENCRYPTED_PATH" "$DECRYPTED_PATH" && echo "ATTENTION: DATA IS NOW DECRYPTED!"
