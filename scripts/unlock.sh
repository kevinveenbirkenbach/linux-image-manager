#!/bin/bash
# Unlocks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
ENCRYPTED=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../.encrypted");
DECRYPTED=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../data");
echo "Unlocking directory: $DECRYPTED"
encfs $ENCRYPTED $DECRYPTED && echo "ATTENTION: DATA IS NOW DECRYPTED!"
