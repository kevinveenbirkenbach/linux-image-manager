#!/bin/bash
#
# Pushs all repositories
# @author Kevin Veen-Birkenbach [aka. Frantz]
source "$(dirname "$(readlink -f "${0}")")/base.sh"
bash "$SCRIPT_PATH/push-local-repositories.sh" push
