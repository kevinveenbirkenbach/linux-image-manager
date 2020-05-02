#!/bin/bash
#
# Unlocks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
#
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Unlocking directory $DECRYPTED_PATH..."
if [ ! -d "$DECRYPTED_PATH" ]
  then
    echo "Creating directory $DECRYPTED_PATH..."
    mkdir "$DECRYPTED_PATH"
fi
echo "Encrypting directory $DECRYPTED_PATH to $DECRYPTED_PATH..."
encfs "$ENCRYPTED_PATH" "$DECRYPTED_PATH" && echo "ATTENTION: DATA IS NOW DECRYPTED!"
