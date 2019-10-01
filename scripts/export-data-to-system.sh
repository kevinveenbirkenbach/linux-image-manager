#!/bin/bash
# Executes the import script in reverse mode
# @author Kevin Veen-Birkenbach [aka. Frantz]
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/base.sh"
bash "$SCRIPT_PATH/import-data-from-system.sh" reverse
