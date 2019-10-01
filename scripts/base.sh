#!/bin/bash
#
# This script contains the global program variables and functions
# @author Kevin Veen-Birkenbach [aka. Frantz]
REPOSITORY_PATH="$(dirname "$(readlink -f "${0}")")"
ENCRYPTED=$(readlink -f "$REPOSITORY_PATH/../.encrypted");
DECRYPTED=$(readlink -f "$REPOSITORY_PATH/../data");
