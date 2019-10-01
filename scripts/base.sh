#!/bin/bash
# This script contains the global program variables and functions
# @author Kevin Veen-Birkenbach [aka. Frantz]
ENCRYPTED=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../.encrypted");
DECRYPTED=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../data");
