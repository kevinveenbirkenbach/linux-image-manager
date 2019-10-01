#!/bin/bash
# Unlocks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
source "$(dirname "$(readlink -f "${0}")")/base.sh"
echo "Unlocking directory $DECRYPTED..."
echo "Creating directory $DECRYPTED..."
mkdir "$DECRYPTED"
echo "Encrypting directory $DECRYPTED to $DECRYPTED..."
encfs "$ENCRYPTED" "$DECRYPTED" && echo "ATTENTION: DATA IS NOW DECRYPTED!"
