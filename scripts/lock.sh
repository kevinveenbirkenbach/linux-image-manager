#!/bin/bash
# Locks the data
# @author Kevin Veen-Birkenbach [aka. Frantz]
DECRYPTED=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../data");
echo "Locking directory: $DECRYPTED"
fusermount -u $DECRYPTED && echo "Data is now encrypted."
